"""The audit trail: one document per thing that happened, who did it, and to what."""
from __future__ import annotations

from . import db


def record(conn, actor: dict | None, action: str, target: str = "", detail: str = "", ip: str = "") -> None:
    aid = db.next_id(conn, "audit")
    conn["audit"].insert_one({
        "_id": aid, "id": aid, "at": db.now_iso(), "actor_id": actor["id"] if actor else None,
        "actor_name": actor["display_name"] if actor else "system",
        "actor_level": actor["level"] if actor else "system", "action": action, "target": target,
        "detail": (detail or "")[:500], "ip": ip,
    })
