"""Who is asking: the signed-in person, their effective level (the founder can
preview a lower one, read-only), and that level's permissions right now."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from ..access import levels, perms
from ..core import db
from ..security import sessions

COOKIE = "tc_session"
PREVIEW_HEADER = "X-TC-Preview"
_OPEN_WHILE_WAITING = {"/api/auth/me", "/api/auth/logout"}
_OPEN_WHILE_RESETTING = _OPEN_WHILE_WAITING | {"/api/account/password"}


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def actor(request: Request) -> dict:
    with db.connect() as conn:
        staff = sessions.lookup(conn, request.cookies.get(COOKIE))
        if not staff:
            raise HTTPException(401, "Sign in to continue.")
        eff, previewing = staff["level"], False
        preview = request.headers.get(PREVIEW_HEADER, "")
        if preview and staff["level"] == "founder" and preview in levels.JOINABLE:
            if request.method != "GET":
                raise HTTPException(403, "Preview is read-only. Leave preview to make changes.")
            eff, previewing = preview, True
        staff["eff_level"], staff["previewing"] = eff, previewing
        staff["mfa"] = bool(staff.get("session_mfa"))
        staff["perms"] = perms.effective(conn, eff) if staff["status"] == "active" else set()
    path = request.url.path
    if staff["status"] != "active" and path not in _OPEN_WHILE_WAITING:
        raise HTTPException(403, "Your account is waiting for approval.")
    if staff["must_change_pw"] and path not in _OPEN_WHILE_RESETTING:
        raise HTTPException(403, "Set a new password first.")
    staff["ip"] = client_ip(request)
    return staff


def require(perm: str):
    def dependency(a: dict = Depends(actor)) -> dict:
        if perm not in a["perms"]:
            raise HTTPException(403, "Your level doesn't include this.")
        return a
    return dependency


def writable(a: dict) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only. Leave preview to make changes.")
