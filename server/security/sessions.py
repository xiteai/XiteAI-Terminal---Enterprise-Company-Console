"""Sign-in sessions. The browser holds a random token in an HttpOnly cookie;
the database holds only its SHA-256 (as the session's own `_id`), so a copied
database carries no usable session."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from ..core import config, db


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create(conn, staff_id: int, user_agent: str, ip: str, mfa: bool = False) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    th = _hash(token)
    conn["sessions"].insert_one({
        "_id": th, "token_hash": th, "staff_id": staff_id, "created_at": db.iso(now),
        "expires_at": db.iso(now + timedelta(hours=config.SESSION_HOURS)), "last_seen_at": db.iso(now),
        "user_agent": (user_agent or "")[:200], "ip": ip, "mfa": bool(mfa),
    })
    return token


def mark_mfa(conn, session_hash: str) -> None:
    conn["sessions"].update_one({"_id": session_hash}, {"$set": {"mfa": True}})


def lookup(conn, token: str | None) -> dict | None:
    """The staff row behind a live session (any status), or None. Touches last_seen."""
    if not token:
        return None
    th = _hash(token)
    session = conn["sessions"].find_one({"_id": th})
    if not session:
        return None
    staff = db.strip(conn["staff"].find_one({"_id": session["staff_id"]}))
    if not staff:                                          # the person behind it is gone
        conn["sessions"].delete_one({"_id": th})
        return None
    if db.parse_iso(session["expires_at"]) < datetime.now(timezone.utc) or staff["status"] == "deactivated":
        conn["sessions"].delete_one({"_id": th})
        return None
    conn["sessions"].update_one({"_id": th}, {"$set": {"last_seen_at": db.now_iso()}})
    row = {**staff, "expires_at": session["expires_at"], "session_mfa": session["mfa"], "session_hash": th}
    return row


def end(conn, token: str | None) -> None:
    if token:
        conn["sessions"].delete_one({"_id": _hash(token)})


def end_all(conn, staff_id: int, keep_hash: str | None = None) -> int:
    filt = {"staff_id": staff_id}
    if keep_hash:
        filt["_id"] = {"$ne": keep_hash}
    return conn["sessions"].delete_many(filt).deleted_count


def purge_expired(conn) -> None:
    conn["sessions"].delete_many({"expires_at": {"$lt": db.now_iso()}})
