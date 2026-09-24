from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core import db
from ...web.deps import require
from ..products import service as products
from . import service

router = APIRouter(prefix="/api/installs", tags=["installs"])


@router.get("")
def list_installs(q: str = "", version: str = "", state: str = "", sort: str = "last_seen", dir: str = "desc",
                  page: int = 1, page_size: int = 25, product: str = products.DEFAULT,
                  a: dict = Depends(require("installs"))):
    with db.connect() as conn:
        return service.listing(conn, a, products.get(conn, product), q, version, state, sort, dir, page, page_size)


@router.get("/{install_id}")
def install(install_id: int, product: str = products.DEFAULT, a: dict = Depends(require("installs"))):
    with db.connect() as conn:
        return service.detail(conn, a, install_id, products.get(conn, product))


@router.delete("/{install_id}")
def erase(install_id: int, a: dict = Depends(require("installs.erase"))):
    with db.connect() as conn:
        service.erase(conn, a, install_id)
    return {"ok": True}
