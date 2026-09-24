from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from ...core import db
from ...web.deps import client_ip
from .ingest import ingest
from .verify import CheckinError

router = APIRouter(prefix="/api/v1", tags=["checkin"])


@router.post("/checkin")
async def checkin(request: Request):
    raw = await request.body()
    if len(raw) > 32 * 1024:
        raise HTTPException(413, "Too large.")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    try:
        with db.connect() as conn:
            return ingest(conn, body, client_ip(request))
    except CheckinError as e:
        raise HTTPException(e.status, e.message)
