from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core import db
from ...web.deps import require
from ..products import service as products
from . import service

router = APIRouter(prefix="/api/finance", tags=["finance"])


class Entry(BaseModel):
    kind: str
    category: str
    amount: float
    occurred_on: str
    note: str = ""


@router.get("")
def list_entries(product: str = products.DEFAULT, kind: str = "", a: dict = Depends(require("finance.view"))):
    with db.connect() as conn:
        row = products.get(conn, product)
        return {"items": service.entries(conn, row["id"], kind or None),
                "can_manage": "finance.manage" in a["perms"] and not a["previewing"]}


@router.get("/summary")
def get_summary(product: str = products.DEFAULT, a: dict = Depends(require("finance.view"))):
    with db.connect() as conn:
        row = products.get(conn, product)
        return service.summary(conn, row["id"])


@router.get("/options")
def options(a: dict = Depends(require("finance.view"))):
    return {"revenue_categories": service.REVENUE_CATEGORIES, "cost_categories": service.COST_CATEGORIES}


@router.post("")
def add_entry(body: Entry, product: str = products.DEFAULT, a: dict = Depends(require("finance.manage"))):
    with db.connect() as conn:
        row = products.get(conn, product)
        return service.add_entry(conn, a, row["id"], body.model_dump())


@router.delete("/{entry_id}")
def remove_entry(entry_id: int, product: str = products.DEFAULT, a: dict = Depends(require("finance.manage"))):
    with db.connect() as conn:
        row = products.get(conn, product)
        service.remove_entry(conn, a, row["id"], entry_id)
        return {"ok": True}
