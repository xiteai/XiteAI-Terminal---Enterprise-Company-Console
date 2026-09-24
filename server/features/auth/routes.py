from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from ...core import audit, config, db
from ...security import sessions
from ...web.deps import COOKIE, actor, client_ip
from . import service
from .schemas import LoginBody

router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=config.COOKIE_SECURE,
                        max_age=config.SESSION_HOURS * 3600, path="/")


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    try:
        with db.connect() as conn:
            row, token = service.sign_in(conn, body.email, body.password, body.code, client_ip(request),
                                         request.headers.get("user-agent", ""))
    except service.NeedCode as need:
        return need.response()
    set_session_cookie(response, token)
    return {"ok": True, "status": row["status"], "must_change_pw": bool(row["must_change_pw"])}


@router.post("/logout")
def logout(request: Request, response: Response, a: dict = Depends(actor)):
    with db.connect() as conn:
        sessions.end(conn, request.cookies.get(COOKIE))
        audit.record(conn, a, "auth.logout", a["email"], "", a["ip"])
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(a: dict = Depends(actor)):
    with db.connect() as conn:
        return service.me(conn, a)
