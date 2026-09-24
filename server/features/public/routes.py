"""The customer panel's API: no sign-in. Status, the changelog, sending a
request to the team, and looking one up by its reference + email."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...bootstrap import freshness
from ...core import audit, config, db
from ...security import lockout
from ...web.deps import client_ip
from ..releases import loader

router = APIRouter(prefix="/api/public", tags=["public"])
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
_SUBJECTS = {"support": "Help request", "feedback": "Feedback", "data_access": "What data do you hold about me?",
             "data_delete": "Please delete my data"}


class NewTicket(BaseModel):
    kind: str
    product: str = Field(default="xos1", max_length=32)
    name: str = Field(default="", max_length=80)
    email: str = Field(max_length=160)
    install_code: str = Field(default="", max_length=12)
    subject: str = Field(default="", max_length=140)
    message: str = Field(max_length=4000)
    website: str = Field(default="", max_length=200)   # honeypot


class Lookup(BaseModel):
    ref: str = Field(max_length=12)
    email: str = Field(max_length=160)


def _new_ref(conn) -> str:
    while True:
        ref = f"XS-{secrets.randbelow(900000) + 100000}"
        if not conn["tickets"].find_one({"ref": ref}, {"_id": 1}):
            return ref


@router.get("/status")
def status():
    try:
        with db.connect() as conn:
            conn.command("ping")
        state = "operational"
    except Exception:
        state = "degraded"
    return {"product": config.PRODUCT, "product_full": config.PRODUCT_FULL, "company": config.COMPANY,
            "state": state, "checked_at": db.now_iso(), "latest": loader.latest(),
            "download_url": config.DOWNLOAD_URL, "support_email": config.SUPPORT_EMAIL,
            "build": freshness.build(),    # launchers compare it, so an old server can't pose as the new one
            "live": freshness.LIVE}        # run by dev.py: it follows the code by itself


@router.get("/releases")
def releases():
    return {"releases": loader.load()[:6], "latest_version": config.LATEST_VERSION}


@router.post("/tickets")
def send(body: NewTicket, request: Request):
    if body.website:                                  # a bot filled the hidden field
        return {"ok": True, "ref": f"XS-{secrets.randbelow(900000) + 100000}"}
    if body.kind not in _SUBJECTS:
        raise HTTPException(400, "Pick what this is about.")
    if not _EMAIL.match(body.email.strip()):
        raise HTTPException(400, "That email address doesn't look right.")
    if len(body.message.strip()) < 10:
        raise HTTPException(400, "Tell us a little more (at least 10 characters).")
    ip = client_ip(request)
    with db.connect() as conn:
        since = db.iso(datetime.now(timezone.utc) - timedelta(hours=1))
        if conn["tickets"].count_documents({"ip": ip, "created_at": {"$gte": since}}) >= config.PUBLIC_TICKETS_PER_HOUR:
            raise HTTPException(429, "You've sent a few requests already. Please try again in an hour.")
        ref, now = _new_ref(conn), db.now_iso()
        product = (conn["products"].find_one({"slug": body.product, "is_demo": False}, {"id": 1})
                  or conn["products"].find_one({"slug": "xos1"}, {"id": 1}))
        tid = db.next_id(conn, "tickets")
        conn["tickets"].insert_one({
            "_id": tid, "id": tid, "product_id": product["id"], "ref": ref, "kind": body.kind,
            "name": body.name.strip(), "email": body.email.strip(),
            "install_code": body.install_code.strip().upper(), "subject": body.subject.strip() or _SUBJECTS[body.kind],
            "message": body.message.strip(), "status": "open",
            "priority": "high" if body.kind == "data_delete" else "normal", "assignee_id": None,
            "created_at": now, "updated_at": now, "ip": ip, "is_demo": False,
        })
        audit.record(conn, None, "ticket.received", ref, body.kind, ip)
    return {"ok": True, "ref": ref}


@router.post("/tickets/lookup")
def lookup(body: Lookup, request: Request):
    ip = client_ip(request)
    key = "lookup:" + ip
    with db.connect() as conn:
        if lockout.locked(conn, key, ip):
            raise HTTPException(429, "Too many lookups. Try again in a few minutes.")
        row = db.strip(conn["tickets"].find_one({
            "ref": body.ref.strip().upper(),
            "email": {"$regex": f"^{re.escape(body.email.strip())}$", "$options": "i"}}))
        if not row:
            lockout.record(conn, key, ip, False)
            raise HTTPException(404, "We couldn't find a request with that reference and email.")
    return {k: row[k] for k in ("ref", "kind", "subject", "status", "created_at", "updated_at")}
