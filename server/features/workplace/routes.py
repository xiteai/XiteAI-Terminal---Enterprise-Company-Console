from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...core import db
from ...web.deps import require
from . import service

router = APIRouter(prefix="/api/workplace", tags=["workplace"])

# Everyone in the Workplace holds `workplace`; the powers inside it are checked
# where they're used, because most of them depend on whose request it is.
member = require("workplace")


class Filing(BaseModel):
    note: str = ""
    leave_type: str = ""
    dates: list[str] = []
    category: str = ""
    amount: float | None = None
    spent_on: str = ""
    quantity: int | None = None
    asset_action: str = "new"


class Decision(BaseModel):
    approve: bool
    note: str = ""
    fine: float | None = None


class Holiday(BaseModel):
    date: str
    label: str


class NewTicket(BaseModel):
    category: str
    subject: str
    body: str
    priority: str = "normal"


class Note(BaseModel):
    body: str


class TicketPatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee_id: int | None = None
    unassign: bool = False


@router.get("/summary")
def summary(a: dict = Depends(member)):
    with db.connect() as conn:
        return service.summary(conn, a)


@router.get("/requests")
def requests(kind: str = "", scope: str = "mine", a: dict = Depends(member)):
    if kind and kind not in service.KINDS:
        raise HTTPException(404, "There's nothing of that kind.")
    with db.connect() as conn:
        items = service.awaiting(conn, a, kind or None) if scope == "approvals" else service.mine(conn, a, kind or None)
        return {"items": items, "can": service.can_do(a)}


@router.post("/requests/{kind}")
def file_request(kind: str, body: Filing, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.file_request(conn, a, kind, body.model_dump())


@router.post("/requests/{req_id}/decide")
def decide(req_id: int, body: Decision, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.decide(conn, a, req_id, body.approve, body.note, body.fine)


@router.post("/requests/{req_id}/withdraw")
def withdraw(req_id: int, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.withdraw(conn, a, req_id)


@router.get("/leave/balance")
def balance(a: dict = Depends(member)):
    with db.connect() as conn:
        return service.balance(conn, a)


@router.get("/leave/holidays")
def list_holidays(year: int | None = None, a: dict = Depends(member)):
    with db.connect() as conn:
        return {"items": service.holidays(conn, year), "can_manage": "leave.approve" in a["perms"] and not a["previewing"]}


@router.post("/leave/holidays")
def add_holiday(body: Holiday, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.add_holiday(conn, a, body.date, body.label)


@router.delete("/leave/holidays/{holiday_id}")
def remove_holiday(holiday_id: int, a: dict = Depends(member)):
    with db.connect() as conn:
        service.remove_holiday(conn, a, holiday_id)
        return {"ok": True}


@router.get("/tickets")
def tickets(scope: str = "mine", status: str = "", a: dict = Depends(member)):
    with db.connect() as conn:
        return {"items": service.tickets(conn, a, scope, status), "can": service.can_do(a)}


@router.post("/tickets")
def raise_ticket(body: NewTicket, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.raise_ticket(conn, a, body.model_dump())


@router.get("/tickets/{ticket_id}")
def ticket(ticket_id: int, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.ticket(conn, a, ticket_id)


@router.post("/tickets/{ticket_id}/notes")
def add_note(ticket_id: int, body: Note, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.add_note(conn, a, ticket_id, body.body)


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, body: TicketPatch, a: dict = Depends(member)):
    changes: dict = {}
    if body.status is not None:
        if body.status not in service.TICKET_STATUS:
            raise HTTPException(400, "Unknown status.")
        changes["status"] = body.status
    if body.priority is not None:
        if body.priority not in service.TICKET_PRIORITY:
            raise HTTPException(400, "Unknown priority.")
        changes["priority"] = body.priority
    if body.assignee_id is not None or body.unassign:
        changes["assignee_id"] = None if body.unassign else body.assignee_id
    if not changes:
        raise HTTPException(400, "Nothing to change.")
    with db.connect() as conn:
        return service.update_ticket(conn, a, ticket_id, changes)


@router.get("/payslips")
def payslips(staff_id: int | None = None, a: dict = Depends(member)):
    with db.connect() as conn:
        return service.payslips(conn, a, staff_id)


@router.get("/options")
def options(a: dict = Depends(member)):
    """The lists every form on the client builds itself from."""
    return {"leave_types": service.LEAVE_TYPES, "expense_categories": service.EXPENSE_CATEGORIES,
            "asset_items": service.ASSET_ITEMS, "asset_actions": service.ASSET_ACTIONS,
            "ticket_categories": service.TICKET_CATEGORIES,
            "priorities": list(service.TICKET_PRIORITY), "statuses": list(service.TICKET_STATUS)}
