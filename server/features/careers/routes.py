from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...core import config, db
from ...security import lockout
from ...web.deps import client_ip, require
from ..join import options
from . import service

router = APIRouter(prefix="/api/careers", tags=["careers"])


class Application(BaseModel):
    name: str
    email: str
    phone: str = ""
    portfolio: str = ""
    note: str = ""
    website: str = ""          # honeypot


class RoleBody(BaseModel):
    title: str
    department: str
    employment_type: str
    location: str = "Remote"
    summary: str
    description: str = ""


class StatusBody(BaseModel):
    status: str


# ── Public: no sign-in ───────────────────────────────────────────────────────

@router.get("/board")
def board():
    with db.connect() as conn:
        return {"departments": service.public_board(conn)}


@router.get("/roles/{role_id}")
def role(role_id: int):
    with db.connect() as conn:
        return service.public_role(conn, role_id)


@router.post("/roles/{role_id}/apply")
def apply(role_id: int, body: Application, request: Request):
    ip = client_ip(request)
    with db.connect() as conn:
        key = "careers-apply:" + ip
        if lockout.locked(conn, key, ip, per_key=config.JOIN_REQUESTS_PER_HOUR):
            raise HTTPException(429, "A few applications came from here already. Please try again later.")
        lockout.record(conn, key, ip, False)
        service.apply(conn, role_id, body.model_dump(), ip)
    return {"ok": True}


# ── Managed from the console (careers.manage) ───────────────────────────────

@router.get("/admin/options")
def admin_options(a: dict = Depends(require("careers.manage"))):
    return {"departments": options.DEPARTMENTS, "employment_types": options.EMPLOYMENT_TYPES, "titles": options.TITLES}


@router.get("/admin/roles")
def admin_roles(a: dict = Depends(require("careers.manage"))):
    with db.connect() as conn:
        return {"items": service.admin_list(conn)}


@router.post("/admin/roles")
def admin_create(body: RoleBody, a: dict = Depends(require("careers.manage"))):
    with db.connect() as conn:
        return service.create_role(conn, a, body.model_dump())


@router.put("/admin/roles/{role_id}")
def admin_update(role_id: int, body: RoleBody, a: dict = Depends(require("careers.manage"))):
    with db.connect() as conn:
        return service.update_role(conn, a, role_id, body.model_dump())


@router.patch("/admin/roles/{role_id}")
def admin_set_status(role_id: int, body: StatusBody, a: dict = Depends(require("careers.manage"))):
    with db.connect() as conn:
        return service.set_status(conn, a, role_id, body.status)


@router.get("/admin/roles/{role_id}/applicants")
def admin_applicants(role_id: int, a: dict = Depends(require("careers.manage"))):
    with db.connect() as conn:
        return service.applicants(conn, a, role_id)
