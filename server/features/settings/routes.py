"""Company switches. Today: whether demo data shows."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core import audit, db, settings
from ...web.deps import actor, require, writable
from ..demo.seed import present as _has_demo

router = APIRouter(prefix="/api/settings", tags=["settings"])


class DemoSwitch(BaseModel):
    show: bool


@router.get("")
def read(a: dict = Depends(actor)):
    with db.connect() as conn:
        return {"show_demo": settings.show_demo(conn), "has_demo": _has_demo(conn)}


@router.put("/demo")
def demo(body: DemoSwitch, a: dict = Depends(require("demo.manage"))):
    writable(a)
    with db.connect() as conn:
        settings.put(conn, "show_demo", "1" if body.show else "0", a["id"])
        audit.record(conn, a, "demo.shown" if body.show else "demo.hidden", "", "", a["ip"])
        return {"show_demo": body.show, "has_demo": _has_demo(conn)}
