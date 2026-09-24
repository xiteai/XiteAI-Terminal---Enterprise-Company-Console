from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core import audit, db
from ...web.deps import actor, require, writable
from . import service

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductBody(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    slug: str | None = Field(default=None, max_length=32)
    full_name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    kind: str | None = None
    website: str | None = Field(default=None, max_length=200)
    status: str | None = None
    latest_version: str | None = Field(default=None, max_length=20)


class MemberBody(BaseModel):
    staff_id: int | None = None
    role: str = "Member"


def _active(a: dict = Depends(actor)) -> dict:
    if a["status"] != "active":
        raise HTTPException(403, "Your account is waiting for approval.")
    return a


@router.get("")
def products(a: dict = Depends(_active)):
    with db.connect() as conn:
        return {"items": service.listing(conn)}


@router.get("/{slug}")
def product(slug: str, a: dict = Depends(_active)):
    with db.connect() as conn:
        row = service.get(conn, slug)
        return service.card(row) | {"stats": service.stats(conn, row["id"])}


@router.post("")
def create(body: ProductBody, a: dict = Depends(require("products.manage"))):
    writable(a)
    fields = service.clean(body.model_dump(), creating=True)
    with db.connect() as conn:
        if conn["products"].find_one({"slug": fields["slug"]}, {"_id": 1}):
            raise HTTPException(409, "A product with that short name exists.")
        pid = db.next_id(conn, "products")
        defaults = {"full_name": "", "description": "", "kind": "desktop", "website": "", "logo": "",
                   "logo_invert": False, "latest_version": "", "status": "live", "is_demo": False}
        conn["products"].insert_one({"_id": pid, "id": pid, **defaults, **fields, "created_at": db.now_iso()})
        key = f"{pid}:{a['id']}"
        conn["product_members"].insert_one({"_id": key, "product_id": pid, "staff_id": a["id"], "role": "Owner",
                                            "added_by": a["id"], "added_at": db.now_iso()})
        audit.record(conn, a, "product.created", fields["name"], fields["slug"], a["ip"])
        return service.card(db.strip(conn["products"].find_one({"_id": pid})))


@router.patch("/{slug}")
def edit(slug: str, body: ProductBody, a: dict = Depends(require("products.manage"))):
    writable(a)
    fields = service.clean({k: v for k, v in body.model_dump().items() if k != "slug"}, creating=False)
    if not fields:
        raise HTTPException(400, "Nothing to change.")
    with db.connect() as conn:
        row = service.get(conn, slug)
        conn["products"].update_one({"_id": row["id"]}, {"$set": fields})
        audit.record(conn, a, "product.updated", row["name"], ", ".join(fields), a["ip"])
        return service.card(db.strip(conn["products"].find_one({"_id": row["id"]})))


@router.get("/{slug}/team")
def team(slug: str, a: dict = Depends(require("people.directory"))):
    with db.connect() as conn:
        row = service.get(conn, slug)
        return {"items": service.team(conn, row["id"]), "roles": service.ROLES,
                "can_manage": "people.manage" in a["perms"] and not a["previewing"]}


@router.post("/{slug}/team")
def add_member(slug: str, body: MemberBody, a: dict = Depends(require("people.manage"))):
    writable(a)
    if body.role not in service.ROLES or not body.staff_id:
        raise HTTPException(400, "Pick a person and a role.")
    with db.connect() as conn:
        row = service.get(conn, slug)
        person = conn["staff"].find_one({"_id": body.staff_id}, {"display_name": 1, "status": 1})
        if not person or person["status"] != "active":
            raise HTTPException(400, "They must be an active team member.")
        key = f"{row['id']}:{body.staff_id}"
        conn["product_members"].update_one(
            {"_id": key}, {"$set": {"_id": key, "product_id": row["id"], "staff_id": body.staff_id,
                                    "role": body.role, "added_by": a["id"], "added_at": db.now_iso()}}, upsert=True)
        audit.record(conn, a, "product.member_set", row["name"], f"{person['display_name']} as {body.role}", a["ip"])
        return {"items": service.team(conn, row["id"])}


@router.delete("/{slug}/team/{staff_id}")
def remove_member(slug: str, staff_id: int, a: dict = Depends(require("people.manage"))):
    writable(a)
    with db.connect() as conn:
        row = service.get(conn, slug)
        person = conn["staff"].find_one({"_id": staff_id}, {"display_name": 1})
        conn["product_members"].delete_one({"_id": f"{row['id']}:{staff_id}"})
        audit.record(conn, a, "product.member_removed", row["name"], person["display_name"] if person else str(staff_id), a["ip"])
        return {"items": service.team(conn, row["id"])}
