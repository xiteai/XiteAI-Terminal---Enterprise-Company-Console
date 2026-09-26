from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core import db
from ...web.deps import actor, require
from . import service

router = APIRouter(prefix="/api/feed", tags=["feed"])


class Post(BaseModel):
    kind: str
    title: str
    body: str = ""
    event_date: str = ""


class Result(BaseModel):
    result: str


@router.get("")
def home(a: dict = Depends(actor)):
    with db.connect() as conn:
        return {**service.timeline(conn), "birthdays": service.birthdays(conn),
                "can_post": "feed.post" in a["perms"] and not a["previewing"]}


@router.post("")
def post(body: Post, a: dict = Depends(require("feed.post"))):
    with db.connect() as conn:
        return service.post(conn, a, body.model_dump())


@router.post("/{post_id}/result")
def add_result(post_id: int, body: Result, a: dict = Depends(require("feed.post"))):
    with db.connect() as conn:
        return service.add_result(conn, a, post_id, body.result)


@router.delete("/{post_id}")
def remove(post_id: int, a: dict = Depends(require("feed.post"))):
    with db.connect() as conn:
        service.remove(conn, a, post_id)
        return {"ok": True}
