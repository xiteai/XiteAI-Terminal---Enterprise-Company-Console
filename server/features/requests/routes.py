from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core import db
from ...web.deps import require
from . import service

router = APIRouter(prefix="/api/requests", tags=["requests"])


class Decision(BaseModel):
    level: str | None = None
    title: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=60)
    reports_to: int | None = None
    note: str = Field(default="", max_length=500)


@router.get("")
def pending(a: dict = Depends(require("people.approve"))):
    with db.connect() as conn:
        return {"items": service.visible(conn, a)}


@router.post("/{staff_id}/approve")
def approve(staff_id: int, body: Decision, a: dict = Depends(require("people.approve"))):
    changes = {k: v for k, v in body.model_dump(exclude={"note"}).items() if v}
    with db.connect() as conn:
        return service.decide(conn, a, staff_id, True, changes, body.note)


@router.post("/{staff_id}/decline")
def decline(staff_id: int, body: Decision, a: dict = Depends(require("people.approve"))):
    with db.connect() as conn:
        return service.decide(conn, a, staff_id, False, {}, body.note)
