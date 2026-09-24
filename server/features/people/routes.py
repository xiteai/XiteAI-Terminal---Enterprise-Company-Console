from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...access import levels
from ...core import audit, db
from ...web.deps import require, writable
from . import cards, service
from .schemas import NoteBody, PersonPatch

router = APIRouter(prefix="/api/people", tags=["people"])


@router.get("")
def list_people(status: str = "active", q: str = "", a: dict = Depends(require("people.directory"))):
    with db.connect() as conn:
        return service.listing(conn, a, status, q)


@router.get("/org")
def org_chart(a: dict = Depends(require("people.directory"))):
    with db.connect() as conn:
        return {"items": service.org(conn)}


@router.get("/{staff_id}")
def person(staff_id: int, a: dict = Depends(require("people.directory"))):
    with db.connect() as conn:
        row = service.get(conn, staff_id)
        full = "people.profiles" in a["perms"] or row["id"] == a["id"]
        if row["status"] != "active" and not full and not service.powers(a, row)["approve"]:
            raise HTTPException(404, "No team member with that id.")
        manager = conn["staff"].find_one({"_id": row["reports_to"]}, {"id": 1, "display_name": 1, "title": 1}) \
            if row["reports_to"] else None
        reports = [db.strip(r) for r in conn["staff"].find({"reports_to": staff_id, "status": "active"})]
        decider = conn["staff"].find_one({"_id": row["decided_by"]}, {"display_name": 1, "level": 1}) \
            if row["decided_by"] else None
        if full and row["id"] != a["id"] and not a["previewing"]:
            audit.record(conn, a, "person.viewed", row["email"], "opened full profile", a["ip"])
    out = (cards.full(row) if full else cards.card(row)) | {
        "manager": manager,
        "reports": [cards.card(r) for r in reports],
        "can": service.powers(a, row),
        "full": full,
    }
    if full and decider:
        out["decided_by"] = f"{decider['display_name']} ({levels.LABEL[decider['level']]})"
    return out


@router.patch("/{staff_id}")
def change_person(staff_id: int, body: PersonPatch, a: dict = Depends(require("people.manage"))):
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    with db.connect() as conn:
        return cards.card(service.update(conn, a, staff_id, changes))


@router.post("/{staff_id}/deactivate")
def deactivate(staff_id: int, body: NoteBody, a: dict = Depends(require("people.fire"))):
    with db.connect() as conn:
        return cards.card(service.deactivate(conn, a, staff_id, body.note))


@router.post("/{staff_id}/reactivate")
def reactivate(staff_id: int, a: dict = Depends(require("people.fire"))):
    with db.connect() as conn:
        return cards.card(service.reactivate(conn, a, staff_id))


@router.post("/{staff_id}/reset-authenticator")
def reset_authenticator(staff_id: int, a: dict = Depends(require("people.reset"))):
    writable(a)
    with db.connect() as conn:
        service.reset_authenticator(conn, a, staff_id)
        return {"ok": True}


@router.post("/{staff_id}/reset-password")
def reset_password(staff_id: int, a: dict = Depends(require("people.reset"))):
    with db.connect() as conn:
        return {"temp_password": service.reset_password(conn, a, staff_id)}
