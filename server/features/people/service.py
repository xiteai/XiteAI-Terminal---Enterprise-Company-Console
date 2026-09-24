"""People powers: change, deactivate, reactivate, reset. Every one needs the
permission AND a higher level than the person it's used on."""
from __future__ import annotations

import re

from fastapi import HTTPException

from ...access import levels, perms
from ...core import audit, db, notify, settings
from ...security import passwords, sessions
from ..join import options
from . import cards


def get(conn, staff_id: int) -> dict:
    row = db.strip(conn["staff"].find_one({"_id": staff_id}))
    if not row:
        raise HTTPException(404, "No team member with that id.")
    return row


def founder_id(conn) -> int | None:
    row = conn["staff"].find_one({"level": "founder", "status": "active"}, {"id": 1}, sort=[("id", 1)])
    return row["id"] if row else None


def powers(a: dict, row: dict) -> dict:
    """What the viewer may do to this person, for the buttons the console shows."""
    if a["previewing"] or row["id"] == a["id"] or row["source"] == "env":
        return {"approve": False, "manage": False, "fire": False, "reset": False}
    lv, p = a["eff_level"], a["perms"]
    return {
        "approve": row["status"] == "pending" and perms.over(lv, p, "people.approve", row["level"]),
        "manage": row["status"] == "active" and perms.over(lv, p, "people.manage", row["level"]),
        "fire": row["status"] in ("active", "deactivated") and perms.over(lv, p, "people.fire", row["level"]),
        "reset": row["status"] == "active" and perms.over(lv, p, "people.reset", row["level"]) and not row["is_demo"],
    }


def _guard(a: dict, row: dict, perm: str) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if row["id"] == a["id"]:
        raise HTTPException(403, "You can't do this to your own account.")
    if row["source"] == "env":
        raise HTTPException(403, "This account is managed in .env.")
    if not perms.over(a["eff_level"], a["perms"], perm, row["level"]):
        raise HTTPException(403, "Only someone above their level, with that power, can do this.")


def check_reports_to(conn, reports_to: int, level: str) -> None:
    boss = conn["staff"].find_one({"_id": reports_to}, {"level": 1, "status": 1})
    if not boss or boss["status"] != "active":
        raise HTTPException(400, "They must report to an active team member.")
    if not levels.outranks(boss["level"], level):
        raise HTTPException(400, "They must report to someone at a higher level.")


def update(conn, a: dict, staff_id: int, changes: dict) -> dict:
    row = get(conn, staff_id)
    _guard(a, row, "people.manage")
    if row["status"] != "active":
        raise HTTPException(409, "Only active team members can be changed.")
    if "level" in changes and not perms.over(a["eff_level"], a["perms"], "people.manage", changes["level"]):
        raise HTTPException(403, "You can only give a level below your own.")
    if "department" in changes and changes["department"] not in options.DEPARTMENTS:
        raise HTTPException(400, "Pick a department from the list.")
    if "employment_type" in changes and changes["employment_type"] not in options.EMPLOYMENT_TYPES:
        raise HTTPException(400, "Pick an employment type from the list.")
    new_level = changes.get("level", row["level"])
    if "reports_to" in changes or "level" in changes:
        check_reports_to(conn, changes.get("reports_to") or row["reports_to"] or a["id"], new_level)
    if "title" in changes:
        changes["title"] = changes["title"].strip()
    if not changes:
        raise HTTPException(400, "Nothing to change.")
    conn["staff"].update_one({"_id": staff_id}, {"$set": changes})
    audit.record(conn, a, "person.updated", row["email"], ", ".join(f"{k}={v}" for k, v in changes.items()), a["ip"])
    if "level" in changes and changes["level"] != row["level"]:
        notify.send(conn, [staff_id], "person.level",
                    f"Your level is now {levels.LABEL[changes['level']]}", f"Changed by {a['display_name']}",
                    "/console/account", staff_id)
    return get(conn, staff_id)


def deactivate(conn, a: dict, staff_id: int, note: str) -> dict:
    row = get(conn, staff_id)
    _guard(a, row, "people.fire")
    if row["status"] != "active":
        raise HTTPException(409, "Only active team members can be deactivated.")
    with db.tx(conn) as tconn:
        tconn["staff"].update_one({"_id": staff_id}, {"$set": {"status": "deactivated", "decided_by": a["id"],
                                                               "decided_at": db.now_iso(), "decision_note": note.strip()}})
        tconn["staff"].update_many({"reports_to": staff_id}, {"$set": {"reports_to": row["reports_to"] or a["id"]}})
        sessions.end_all(tconn, staff_id)
        audit.record(tconn, a, "person.deactivated", row["email"], note.strip(), a["ip"])
        fid = founder_id(tconn)
        if fid and fid != a["id"]:
            notify.send(tconn, [fid], "person.deactivated",
                        f"{a['display_name']} deactivated {row['display_name']}",
                        f"{levels.LABEL[row['level']]} · {row['title']}", f"/console/people/{staff_id}", staff_id)
        result = get(tconn, staff_id)
    return result


def reactivate(conn, a: dict, staff_id: int) -> dict:
    row = get(conn, staff_id)
    _guard(a, row, "people.fire")
    if row["status"] != "deactivated":
        raise HTTPException(409, "Only deactivated team members can be brought back.")
    conn["staff"].update_one({"_id": staff_id}, {"$set": {"status": "active", "decided_by": a["id"],
                                                          "decided_at": db.now_iso(), "decision_note": ""}})
    audit.record(conn, a, "person.reactivated", row["email"], "", a["ip"])
    return get(conn, staff_id)


def reset_password(conn, a: dict, staff_id: int) -> str:
    row = get(conn, staff_id)
    _guard(a, row, "people.reset")
    if row["is_demo"]:
        raise HTTPException(409, "Demo people can't sign in.")
    temp = passwords.generate()
    conn["staff"].update_one({"_id": staff_id}, {"$set": {"password_hash": passwords.hash_password(temp),
                                                          "must_change_pw": True}})
    sessions.end_all(conn, staff_id)
    audit.record(conn, a, "person.password_reset", row["email"], "", a["ip"])
    return temp


def reset_authenticator(conn, a: dict, staff_id: int) -> None:
    """For someone who lost their phone: their authenticator is cleared and they
    are signed out everywhere; they set a new one up after signing in."""
    row = get(conn, staff_id)
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if row["id"] == a["id"]:
        raise HTTPException(403, "You can't do this to your own account.")
    # Not _guard: an .env-managed account keeps its password in .env, but its
    # authenticator lives here like everyone else's.
    if not perms.over(a["eff_level"], a["perms"], "people.reset", row["level"]):
        raise HTTPException(403, "Only someone above their level, with that power, can do this.")
    conn["staff"].update_one({"_id": staff_id}, {"$set": {"totp_secret": "", "totp_pending": ""}})
    sessions.end_all(conn, staff_id)
    audit.record(conn, a, "person.authenticator_reset", row["email"], "", a["ip"])
    notify.send(conn, [staff_id], "account.authenticator_reset", "Your authenticator was reset",
                f"By {a['display_name']}. Set up a new one from Account before opening code.", "/console/account")


def listing(conn, a: dict, status: str, q: str) -> dict:
    can_see_all = bool({"people.approve", "people.manage", "people.fire", "people.profiles"} & a["perms"])
    filt: dict = {}
    if status in ("pending", "declined", "deactivated") and can_see_all:
        filt["status"] = status
    elif status == "all" and can_see_all:
        pass
    else:
        filt["status"] = "active"
    filt.update(settings.demo_filter(conn))
    if q.strip():
        needle = re.escape(q.strip()[:80])
        rx = {"$regex": needle, "$options": "i"}
        filt["$or"] = [{"display_name": rx}, {"preferred_name": rx}, {"email": rx}, {"title": rx}, {"department": rx}]
    rows = [db.strip(r) for r in conn["staff"].find(filt)]
    rows.sort(key=lambda r: (-levels.RANK[r["level"]], r["display_name"].lower()))
    counts = {r["_id"]: r["n"] for r in conn["staff"].aggregate([
        {"$match": settings.demo_filter(conn)}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    if not can_see_all:
        counts = {"active": counts.get("active", 0)}
    return {"items": [cards.card(r) | {"can": powers(a, r)} for r in rows], "counts": counts,
            "departments": options.DEPARTMENTS, "can_see_all": can_see_all}


def org(conn) -> list[dict]:
    rows = [db.strip(r) for r in conn["staff"].find({"status": "active", **settings.demo_filter(conn)})]
    rows.sort(key=lambda r: (-levels.RANK[r["level"]], r["display_name"].lower()))
    return [cards.card(r) for r in rows]
