"""The founder's grid: which level may see and do what. A switch that matches
the default removes its override document, so the collection only ever holds
real decisions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...access import catalog, levels, perms
from ...core import audit, db
from ...web.deps import require, writable

router = APIRouter(prefix="/api/access", tags=["access"])


class Switch(BaseModel):
    level: str
    perm: str
    allowed: bool


def _key(level: str, perm: str) -> str:
    return f"{level}|{perm}"


def _grid(conn) -> dict:
    editable = [lv for lv in levels.as_list() if lv["key"] != "founder"]
    return {
        "groups": catalog.as_groups(),
        "levels": editable,
        "matrix": {lv["key"]: sorted(perms.effective(conn, lv["key"])) for lv in editable},
        "defaults": {k: sorted(v) for k, v in catalog.DEFAULTS.items()},
        "overrides": conn["level_permissions"].count_documents({}),
    }


@router.get("")
def grid(a: dict = Depends(require("access.manage"))):
    with db.connect() as conn:
        return _grid(conn)


@router.put("")
def set_switch(body: Switch, a: dict = Depends(require("access.manage"))):
    writable(a)
    if body.level not in levels.JOINABLE or body.perm not in catalog.KEYS:
        raise HTTPException(400, "Unknown level or permission.")
    with db.connect() as conn:
        key = _key(body.level, body.perm)
        if (body.perm in catalog.DEFAULTS.get(body.level, set())) == body.allowed:
            conn["level_permissions"].delete_one({"_id": key})
        else:
            conn["level_permissions"].update_one(
                {"_id": key}, {"$set": {"level": body.level, "perm": body.perm, "allowed": body.allowed,
                                        "set_by": a["id"], "set_at": db.now_iso()}}, upsert=True)
        audit.record(conn, a, "access.changed", levels.LABEL[body.level],
                     f"{body.perm} {'on' if body.allowed else 'off'}", a["ip"])
        return _grid(conn)


@router.delete("/{level}")
def reset_level(level: str, a: dict = Depends(require("access.manage"))):
    writable(a)
    if level not in levels.JOINABLE:
        raise HTTPException(400, "Unknown level.")
    with db.connect() as conn:
        n = conn["level_permissions"].delete_many({"level": level}).deleted_count
        audit.record(conn, a, "access.reset", levels.LABEL[level], f"{n} switches back to default", a["ip"])
        return _grid(conn)
