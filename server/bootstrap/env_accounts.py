"""Accounts that come from .env: the founder, plus optional starting staff.

Runs on every start. The .env password is hashed into the database; if it
changed since last start the hash is replaced (that's how you rotate it).
People who joined through the sign-up page are never touched by this.
"""
from __future__ import annotations

import logging

from ..access import levels
from ..core import audit, config, db
from ..security import passwords, sessions

log = logging.getLogger("terminal.accounts")


def _upsert(conn, *, level: str, email: str, password: str, name: str, title: str, reports_to: int | None) -> int:
    row = db.strip(conn["staff"].find_one({"email": email}, collation=db.CASE_INSENSITIVE))
    if row and row["source"] != "env":
        log.warning("%s already joined through sign-up; its .env entry is ignored", email)
        return row["id"]
    if row:
        fields = {"level": level, "display_name": name, "title": title, "status": "active", "is_demo": False}
        if not passwords.verify_password(password, row["password_hash"]):
            fields["password_hash"] = passwords.hash_password(password)
            sessions.end_all(conn, row["id"])
            audit.record(conn, None, "account.password_rotated", email, "changed in .env")
        conn["staff"].update_one({"_id": row["id"]}, {"$set": fields})
        return row["id"]
    now = db.now_iso()
    sid = db.next_id(conn, "staff")
    conn["staff"].insert_one({
        **levels.new_staff_defaults(), "_id": sid, "id": sid, "email": email, "display_name": name, "level": level,
        "requested_level": level, "title": title, "department": "Leadership" if level == "founder" else "",
        "employment_type": "Full-time", "password_hash": passwords.hash_password(password), "reports_to": reports_to,
        "status": "active", "source": "env", "created_at": now, "decided_at": now,
    })
    audit.record(conn, None, "account.created", email, f"{levels.LABEL[level]} from .env")
    return sid


def sync(conn) -> None:
    if not config.FOUNDER_EMAIL or not config.FOUNDER_PASSWORD:
        log.error("FOUNDER_EMAIL / FOUNDER_PASSWORD missing from .env: nobody can sign in")
        return
    old = db.strip(conn["staff"].find_one({"level": "founder", "source": "env"}, {"id": 1, "email": 1}))
    if old and old["email"].lower() != config.FOUNDER_EMAIL:
        conn["staff"].update_one({"_id": old["id"]}, {"$set": {"email": config.FOUNDER_EMAIL}})
    founder = _upsert(conn, level="founder", email=config.FOUNDER_EMAIL, password=config.FOUNDER_PASSWORD,
                      name=config.FOUNDER_DISPLAY_NAME, title=config.FOUNDER_TITLE, reports_to=None)

    for entry in filter(None, (e.strip() for e in config.SEED_STAFF.split(";"))):
        parts = [p.strip() for p in entry.split(":")]
        if len(parts) < 4 or parts[0] not in levels.JOINABLE:
            log.warning("SEED_STAFF entry skipped (want level:email:password:Full Name[:Title])")
            continue
        level, email, password, name = parts[0], config.work_email(parts[1]), parts[2], parts[3]
        if passwords.problem(password):
            log.warning("SEED_STAFF password for %s is too weak; skipped", email)
            continue
        _upsert(conn, level=level, email=email, password=password, name=name,
                title=parts[4] if len(parts) > 4 else levels.LABEL[level], reports_to=founder)
