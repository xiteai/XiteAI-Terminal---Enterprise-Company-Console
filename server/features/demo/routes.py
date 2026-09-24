from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...core import audit, db
from ...web.deps import require, writable
from . import seed

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("")
def load(a: dict = Depends(require("demo.manage"))):
    writable(a)
    with db.connect() as conn:
        if seed.present(conn):
            raise HTTPException(409, "Demo data is already loaded.")
        out = seed.load(conn)
        audit.record(conn, a, "demo.loaded", "", "", a["ip"])
    return out


@router.delete("")
def purge(a: dict = Depends(require("demo.manage"))):
    writable(a)
    with db.connect() as conn:
        out = seed.purge(conn)
        audit.record(conn, a, "demo.purged", "", ", ".join(f"{v} {k}" for k, v in out.items()), a["ip"])
    return out
