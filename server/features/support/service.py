"""Customer tickets: ordering, shaping, and the changes staff make to them."""
from __future__ import annotations

import re

from fastapi import HTTPException

from ...core import audit, db, notify, settings

KINDS = ("support", "feedback", "data_access", "data_delete")
PRIORITY = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
STATUS = {"open": 0, "in_progress": 1, "resolved": 2, "closed": 3}
_FIELDS = ("id", "ref", "kind", "name", "email", "install_code", "subject", "message", "status", "priority",
           "assignee_id", "created_at", "updated_at")


def shape(r: dict) -> dict:
    return {k: r[k] for k in _FIELDS} | {"assignee_name": r.get("assignee_name"), "is_demo": bool(r["is_demo"])}


def _with_assignee_names(conn, rows: list[dict]) -> list[dict]:
    names = {s["id"]: s["display_name"] for s in conn["staff"].find(
        {"id": {"$in": [r["assignee_id"] for r in rows if r["assignee_id"]]}}, {"id": 1, "display_name": 1})}
    return [{**r, "assignee_name": names.get(r["assignee_id"])} for r in rows]


def listing(conn, product: dict, status: str, kind: str, q: str) -> dict:
    filt: dict = {"product_id": product["id"], **settings.demo_filter(conn)}
    if status in STATUS:
        filt["status"] = status
    elif status == "active":
        filt["status"] = {"$in": ["open", "in_progress"]}
    if kind in KINDS:
        filt["kind"] = kind
    if q.strip():
        like = {"$regex": re.escape(q.strip()[:80]), "$options": "i"}
        filt["$or"] = [{"subject": like}, {"message": like}, {"ref": like}, {"name": like}, {"email": like}]
    rows = _with_assignee_names(conn, [db.strip(r) for r in conn["tickets"].find(filt)])
    rows.sort(key=lambda r: r["updated_at"], reverse=True)
    rows.sort(key=lambda r: (STATUS[r["status"]] > 1, PRIORITY[r["priority"]] if STATUS[r["status"]] <= 1 else 9))
    counts = {r["_id"]: r["n"] for r in conn["tickets"].aggregate([
        {"$match": {"product_id": product["id"], **settings.demo_filter(conn)}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    return {"items": [shape(r) for r in rows], "counts": counts}


def get(conn, ticket_id: int) -> dict:
    row = db.strip(conn["tickets"].find_one({"_id": ticket_id, **settings.demo_filter(conn)}))
    if not row:
        raise HTTPException(404, "No ticket with that id.")
    return _with_assignee_names(conn, [row])[0]


def update(conn, a: dict, ticket_id: int, changes: dict) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = get(conn, ticket_id)
    if "assignee_id" in changes and changes["assignee_id"] is not None and not conn["staff"].find_one(
            {"_id": changes["assignee_id"], "status": "active", "is_demo": False}, {"_id": 1}):
        raise HTTPException(400, "That person isn't an active team member.")
    conn["tickets"].update_one({"_id": ticket_id}, {"$set": {**changes, "updated_at": db.now_iso()}})
    audit.record(conn, a, "ticket.updated", row["ref"], ", ".join(f"{k}={v}" for k, v in changes.items()), a["ip"])
    assignee = changes.get("assignee_id")
    if assignee and assignee != a["id"]:
        product = conn["products"].find_one({"_id": row["product_id"]}, {"slug": 1})
        slug = product["slug"] if product else "xos1"
        notify.send(conn, [assignee], "ticket.assigned", f"{a['display_name']} assigned you {row['ref']}",
                    row["subject"], f"/console/p/{slug}/support/{ticket_id}", ticket_id)


def add_note(conn, a: dict, ticket_id: int, body: str) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = get(conn, ticket_id)
    now = db.now_iso()
    nid = db.next_id(conn, "ticket_notes")
    conn["ticket_notes"].insert_one({"_id": nid, "id": nid, "ticket_id": ticket_id, "staff_id": a["id"],
                                     "body": body.strip(), "at": now})
    conn["tickets"].update_one({"_id": ticket_id}, {"$set": {"updated_at": now}})
    audit.record(conn, a, "ticket.note", row["ref"], "", a["ip"])
