from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core import db
from ...web.deps import actor, require
from ..products import service as products
from . import service

router = APIRouter(tags=["overview"])


@router.get("/api/overview")
def overview(period: int = Query(30, alias="range"), product: str = products.DEFAULT,
             a: dict = Depends(require("overview"))):
    with db.connect() as conn:
        return service.build(conn, a, period if period in (7, 30, 90) else 30, products.get(conn, product))


@router.get("/api/company")
def company(a: dict = Depends(require("people.directory"))):
    with db.connect() as conn:
        return service.company(conn, a)
