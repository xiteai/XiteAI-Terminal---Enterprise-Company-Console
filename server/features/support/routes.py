from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core import db
from ...web.deps import require
from ..installs import store as installs_store
from ..products import service as products
from . import service

router = APIRouter(prefix="/api/tickets", tags=["support"])


class TicketPatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee_id: int | None = None
    unassign: bool = False


class NoteBody(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.get("")
def tickets(status: str = "", kind: str = "", q: str = "", product: str = products.DEFAULT,
            a: dict = Depends(require("support"))):
    with db.connect() as conn:
        return service.listing(conn, products.get(conn, product), status, kind, q)


@router.get("/{ticket_id}")
def ticket(ticket_id: int, a: dict = Depends(require("support"))):
    with db.connect() as conn:
        row = service.get(conn, ticket_id)
        authors = {s["id"]: (s["display_name"], s["level"]) for s in conn["staff"].find(
            {"id": {"$in": conn["ticket_notes"].distinct("staff_id", {"ticket_id": ticket_id})}},
            {"id": 1, "display_name": 1, "level": 1})}
        notes = [{"id": n["id"], "body": n["body"], "at": n["at"],
                 "author": authors.get(n["staff_id"], (None, None))[0],
                 "author_level": authors.get(n["staff_id"], (None, None))[1]}
                for n in conn["ticket_notes"].find({"ticket_id": ticket_id}).sort("at", 1)]
        install = None
        if row["install_code"]:
            install = installs_store.one("SELECT id, code, app_version, last_seen FROM installs WHERE code = ?",
                                         (row["install_code"],))
        team = []
        if "support.assign" in a["perms"]:
            team = [{"id": s["id"], "name": s["display_name"], "level": s["level"]}
                   for s in conn["staff"].find({"status": "active", "is_demo": False},
                                               {"id": 1, "display_name": 1, "level": 1}).sort("display_name", 1)]
    return {"ticket": service.shape(row), "notes": notes, "install": install, "assignable": team,
            "can": {"reply": "support.reply" in a["perms"] and not a["previewing"],
                    "assign": "support.assign" in a["perms"] and not a["previewing"],
                    "erase": "installs.erase" in a["perms"] and not a["previewing"]}}


@router.patch("/{ticket_id}")
def change(ticket_id: int, body: TicketPatch, a: dict = Depends(require("support.reply"))):
    changes = {}
    if body.status is not None:
        if body.status not in service.STATUS:
            raise HTTPException(400, "Unknown status.")
        changes["status"] = body.status
    if body.priority is not None:
        if body.priority not in service.PRIORITY:
            raise HTTPException(400, "Unknown priority.")
        changes["priority"] = body.priority
    if body.assignee_id is not None or body.unassign:
        if "support.assign" not in a["perms"]:
            raise HTTPException(403, "Your level can't assign tickets.")
        changes["assignee_id"] = None if body.unassign else body.assignee_id
    if not changes:
        raise HTTPException(400, "Nothing to change.")
    with db.connect() as conn:
        service.update(conn, a, ticket_id, changes)
    return {"ok": True}


@router.post("/{ticket_id}/notes")
def note(ticket_id: int, body: NoteBody, a: dict = Depends(require("support.reply"))):
    with db.connect() as conn:
        service.add_note(conn, a, ticket_id, body.body)
    return {"ok": True}
