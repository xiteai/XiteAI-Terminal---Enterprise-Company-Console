from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from ...access import levels
from ...core import config, db
from ...security import lockout
from ...web.deps import client_ip
from ..auth.routes import set_session_cookie
from . import options, service
from .schemas import EmailCheck, JoinBody

router = APIRouter(prefix="/api/join", tags=["join"])


@router.get("/options")
def join_options():
    joinable = [lv for lv in levels.as_list() if lv["key"] in levels.JOINABLE]
    return options.as_dict(joinable, config.EMAIL_DOMAIN)


@router.post("/check-email")
def check_email(body: EmailCheck, request: Request):
    ip = client_ip(request)
    with db.connect() as conn:
        key = "email-check:" + ip
        if lockout.locked(conn, key, ip, per_key=40):
            raise HTTPException(429, "Too many checks. Wait a few minutes.")
        lockout.record(conn, key, ip, False)       # every check counts toward the limit
        available = service.email_available(conn, body.local)
    return {"available": available, "email": f"{body.local.strip().lower()}@{config.EMAIL_DOMAIN}"}


@router.post("")
def join(body: JoinBody, request: Request, response: Response):
    with db.connect() as conn:
        _, token = service.submit(conn, body, client_ip(request), request.headers.get("user-agent", ""))
    set_session_cookie(response, token)
    return {"ok": True}
