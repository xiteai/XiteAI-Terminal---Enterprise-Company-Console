from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core import db, notify
from ...web.deps import actor

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class ReadBody(BaseModel):
    ids: list[int] | None = None      # None = everything


@router.get("")
def inbox(limit: int = 30, a: dict = Depends(actor)):
    limit = max(5, min(limit, 100))
    with db.connect() as conn:
        filt = notify.visible_filter(conn, a["id"])
        items = [{k: r[k] for k in ("id", "kind", "title", "body", "link", "created_at", "read_at")}
                for r in conn["notifications"].find(filt).sort([("created_at", -1), ("id", -1)]).limit(limit)]
        unread = conn["notifications"].count_documents({**filt, "read_at": None})
    return {"items": items, "unread": unread}


@router.post("/read")
def mark_read(body: ReadBody, a: dict = Depends(actor)):
    with db.connect() as conn:
        now = db.now_iso()
        if body.ids is None:
            conn["notifications"].update_many({"staff_id": a["id"], "read_at": None}, {"$set": {"read_at": now}})
        else:
            conn["notifications"].update_many(
                {"id": {"$in": body.ids[:200]}, "staff_id": a["id"], "read_at": None}, {"$set": {"read_at": now}})
    return {"ok": True}
