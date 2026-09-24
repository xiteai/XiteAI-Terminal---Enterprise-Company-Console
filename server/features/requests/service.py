"""Deciding a join request. The first person with the power decides it; the
'new request' notification everyone else got is replaced by a single line
saying who decided what, so nobody's bell fills up with stale requests."""
from __future__ import annotations

from fastapi import HTTPException

from ...access import levels, perms
from ...core import audit, db, notify, settings
from ..people import cards
from ..people.service import check_reports_to, founder_id


def visible(conn, a: dict) -> list[dict]:
    """Pending requests this viewer could decide."""
    if "people.approve" not in a["perms"]:
        return []
    rows = list(conn["staff"].find({"status": "pending", **settings.demo_filter(conn)}).sort("created_at", -1))
    full = "people.profiles" in a["perms"]
    return [(cards.full(db.strip(r)) if full else cards.card(db.strip(r))) | {"created_at": r["created_at"]}
            for r in rows if levels.outranks(a["eff_level"], r["level"])]


def decide(conn, a: dict, staff_id: int, approve: bool, changes: dict, note: str) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    with db.tx(conn) as tconn:
        row = db.strip(tconn["staff"].find_one({"_id": staff_id}))
        if not row:
            raise HTTPException(404, "No request with that id.")
        if row["status"] != "pending":
            by = tconn["staff"].find_one({"_id": row["decided_by"]}, {"display_name": 1})
            raise HTTPException(409, f"Already {row['status']} by {by['display_name'] if by else 'someone'}.")
        final = changes.get("level") or row["level"]
        for lv in {row["level"], final}:
            if not perms.over(a["eff_level"], a["perms"], "people.approve", lv):
                raise HTTPException(403, "Only someone above that level, with the power to approve, can decide.")
        now = db.now_iso()
        if approve:
            reports_to = changes.get("reports_to") or a["id"]
            check_reports_to(tconn, reports_to, final)
            tconn["staff"].update_one({"_id": staff_id}, {"$set": {
                "status": "active", "level": final, "title": (changes.get("title") or row["title"]).strip(),
                "department": changes.get("department") or row["department"], "reports_to": reports_to,
                "decided_by": a["id"], "decided_at": now, "decision_note": note.strip()}})
            verb, headline = "approved", f"approved {row['display_name']} as {levels.LABEL[final]}"
        else:
            tconn["staff"].update_one({"_id": staff_id}, {"$set": {
                "status": "declined", "decided_by": a["id"], "decided_at": now, "decision_note": note.strip()}})
            verb, headline = "declined", f"declined {row['display_name']}'s request"

        had = notify.clear(tconn, "join.request", staff_id)
        others = [i for i in had if i != a["id"]]
        fid = founder_id(tconn)
        if fid and fid != a["id"]:
            others.append(fid)
        notify.send(tconn, others, "join.decided", f"{a['display_name']} {headline}",
                    f"{row['title']} · {row['department']}", f"/console/people/{staff_id}", staff_id)
        audit.record(tconn, a, f"join.{verb}", row["email"],
                     f"{levels.LABEL[final]}{' · ' + note.strip() if note.strip() else ''}", a["ip"])
        result = cards.card(db.strip(tconn["staff"].find_one({"_id": staff_id})))
    return result


def recent_decisions(conn, limit: int = 6) -> list[dict]:
    rows = list(conn["staff"].find({
        "decided_at": {"$ne": None}, "source": "signup", "status": {"$in": ["active", "declined"]},
        **settings.demo_filter(conn)}).sort("decided_at", -1).limit(limit))
    deciders = {d["id"]: d["display_name"] for d in
               conn["staff"].find({"id": {"$in": [r["decided_by"] for r in rows if r["decided_by"]]}},
                                  {"id": 1, "display_name": 1})}
    return [cards.card(db.strip(r)) | {"decided_at": r["decided_at"], "decider": deciders.get(r["decided_by"])}
           for r in rows]
