"""Slow down guessing: too many failures for one account or one address inside
the window and further attempts are refused until the window passes. Also used
as a general per-key rate limit (email checks, ticket lookups)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..core import config, db


def _since() -> str:
    return db.iso(datetime.now(timezone.utc) - timedelta(minutes=config.LOCKOUT_WINDOW_MIN))


def locked(conn, key: str, ip: str, per_key: int | None = None) -> bool:
    since = _since()
    by_key = conn["login_attempts"].count_documents({"username": key, "ok": False, "at": {"$gt": since}},
                                                     collation=db.CASE_INSENSITIVE)
    by_ip = conn["login_attempts"].count_documents({"ip": ip, "ok": False, "at": {"$gt": since}})
    return by_key >= (per_key or config.LOCKOUT_FAILS_PER_USER) or by_ip >= config.LOCKOUT_FAILS_PER_IP


def record(conn, key: str, ip: str, ok: bool) -> None:
    aid = db.next_id(conn, "login_attempts")
    conn["login_attempts"].insert_one({"_id": aid, "id": aid, "username": key[:120], "ip": ip, "at": db.now_iso(),
                                       "ok": bool(ok)})
    if ok:
        conn["login_attempts"].delete_many({"username": key, "ok": False}, collation=db.CASE_INSENSITIVE)
