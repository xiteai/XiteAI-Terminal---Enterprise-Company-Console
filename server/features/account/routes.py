"""Your own account: password, where you're signed in."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core import audit, config, db
from ...security import mfa, passwords, sessions, totp, vault
from ...web.deps import actor, writable
from ..people import cards

router = APIRouter(prefix="/api/account", tags=["account"])


class PasswordBody(BaseModel):
    current: str = Field(max_length=200)
    new: str = Field(max_length=200)


class PhotoBody(BaseModel):
    photo: str = Field(default="", max_length=400_100)


@router.get("/profile")
def my_profile(a: dict = Depends(actor)):
    return cards.full(a)


@router.put("/photo")
def change_photo(body: PhotoBody, a: dict = Depends(actor)):
    """Your own photo, changed by you. Nobody needs a permission to change
    their own face, and nobody but you can change yours — the id comes from
    the session, never from the request."""
    writable(a)
    from ..join import validate as v

    photo = v.photo(body.photo)          # same size and type rules as sign-up
    with db.connect() as conn:
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"avatar_url": photo}})
        audit.record(conn, a, "account.photo_changed", a["email"], "", a["ip"])
    return {"ok": True, "avatar_url": photo}


@router.delete("/photo")
def remove_photo(a: dict = Depends(actor)):
    writable(a)
    with db.connect() as conn:
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"avatar_url": ""}})
        audit.record(conn, a, "account.photo_removed", a["email"], "", a["ip"])
    return {"ok": True, "avatar_url": ""}


@router.post("/password")
def change_password(body: PasswordBody, a: dict = Depends(actor)):
    writable(a)
    if a["source"] == "env":
        raise HTTPException(409, "Your password lives in .env. Change it there and restart the server.")
    if not passwords.verify_password(body.current, a["password_hash"]):
        raise HTTPException(400, "Your current password isn't right.")
    problem = passwords.problem(body.new)
    if problem:
        raise HTTPException(400, problem)
    if body.new == body.current:
        raise HTTPException(400, "Choose a password you haven't used here.")
    with db.connect() as conn:
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"password_hash": passwords.hash_password(body.new),
                                                             "must_change_pw": False}})
        sessions.end_all(conn, a["id"], keep_hash=a["session_hash"])
        audit.record(conn, a, "account.password_changed", a["email"], "", a["ip"])
    return {"ok": True}


@router.get("/sessions")
def my_sessions(a: dict = Depends(actor)):
    with db.connect() as conn:
        rows = list(conn["sessions"].find({"staff_id": a["id"]},
                                          {"token_hash": 1, "created_at": 1, "last_seen_at": 1, "user_agent": 1, "ip": 1})
                   .sort("last_seen_at", -1))
    return {"items": [{"current": r["token_hash"] == a["session_hash"], "created_at": r["created_at"],
                       "last_seen_at": r["last_seen_at"], "user_agent": r["user_agent"], "ip": r["ip"]} for r in rows]}


@router.post("/sessions/revoke-others")
def revoke_others(a: dict = Depends(actor)):
    with db.connect() as conn:
        n = sessions.end_all(conn, a["id"], keep_hash=a["session_hash"])
        audit.record(conn, a, "account.sessions_revoked", a["email"], f"{n} other sessions", a["ip"])
    return {"ok": True, "revoked": n}


# ── Your authenticator ────────────────────────────────────────────────────────

class CodeBody(BaseModel):
    code: str = Field(max_length=12)
    password: str = Field(default="", max_length=200)


@router.post("/authenticator/start")
def authenticator_start(a: dict = Depends(actor)):
    """A fresh seed, held as 'pending' until a code from it proves the app has it."""
    writable(a)
    if mfa.from_env(a):
        raise HTTPException(409, "Yours is set in .env (FOUNDER_TOTP_SECRET).")
    secret = totp.new_secret()
    with db.connect() as conn:
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"totp_pending": vault.seal(secret)}})
    return {"secret": secret, "uri": totp.setup_uri(secret, a["email"], config.APP_NAME)}


@router.post("/authenticator/confirm")
def authenticator_confirm(body: CodeBody, a: dict = Depends(actor)):
    writable(a)
    with db.connect() as conn:
        row = conn["staff"].find_one({"_id": a["id"]}, {"totp_pending": 1})
        pending = vault.unseal((row or {}).get("totp_pending") or "")
        if not pending:
            raise HTTPException(409, "Start the setup again.")
        if not totp.verify(pending, body.code):
            raise HTTPException(400, "That code didn't work. Check the app shows XiteAI Terminal, and try the newest code.")
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"totp_secret": vault.seal(pending), "totp_pending": ""}})
        sessions.mark_mfa(conn, a["session_hash"])
        audit.record(conn, a, "account.authenticator_on", a["email"], "", a["ip"])
    return {"ok": True}


@router.post("/authenticator/remove")
def authenticator_remove(body: CodeBody, a: dict = Depends(actor)):
    """Only with your password and a current code: a stolen session can't switch it off."""
    writable(a)
    if mfa.from_env(a):
        raise HTTPException(409, "Yours is set in .env. Remove FOUNDER_TOTP_SECRET there.")
    if not passwords.verify_password(body.password, a["password_hash"]) or not mfa.check(a, body.code):
        raise HTTPException(400, "Your password or code isn't right.")
    with db.connect() as conn:
        conn["staff"].update_one({"_id": a["id"]}, {"$set": {"totp_secret": "", "totp_pending": ""}})
        audit.record(conn, a, "account.authenticator_off", a["email"], "", a["ip"])
    return {"ok": True}
