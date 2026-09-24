"""In-console notifications (the bell). Unlike the audit trail these are for
people, not for the record: one line each, and a resolved item replaces the
ones it made obsolete instead of piling up next to them."""
from __future__ import annotations

from . import db, settings


def send(conn, staff_ids, kind: str, title: str, body: str = "", link: str = "",
         ref_id: int | None = None) -> None:
    ids = sorted({i for i in staff_ids if i})
    if not ids:
        return
    now = db.now_iso()
    docs = []
    for sid in ids:
        nid = db.next_id(conn, "notifications")
        docs.append({"_id": nid, "id": nid, "staff_id": sid, "kind": kind, "title": title, "body": body,
                    "link": link, "ref_id": ref_id, "created_at": now, "read_at": None})
    conn["notifications"].insert_many(docs)


def clear(conn, kind: str, ref_id: int) -> list[int]:
    """Remove every notification of `kind` about `ref_id`; return who had one."""
    had = sorted(conn["notifications"].distinct("staff_id", {"kind": kind, "ref_id": ref_id}))
    conn["notifications"].delete_many({"kind": kind, "ref_id": ref_id})
    return had


def visible_filter(conn, staff_id: int) -> dict:
    """A staff member's own notifications; with demo hidden, a join request
    about a demo person goes quiet too, the same way everything else does."""
    filt = {"staff_id": staff_id}
    if not settings.show_demo(conn):
        demo_ids = conn["staff"].distinct("id", {"is_demo": True})
        filt["$nor"] = [{"kind": {"$regex": "^join\\."}, "ref_id": {"$in": demo_ids}}]
    return filt
