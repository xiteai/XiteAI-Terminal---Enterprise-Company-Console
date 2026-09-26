"""Products: XOS1 today, whatever XiteAI builds next. Installs, tickets and
releases belong to a product; each product has its own team."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ...access import levels
from ...core import config, db, settings
from ..installs import store as installs_store
from ..people.cards import initials

DEFAULT = "xos1"
KINDS = ("desktop", "web")
STATUSES = ("live", "building", "paused")
ROLES = ("Owner", "Lead", "Member")
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")


def _member_key(product_id: int, staff_id: int) -> str:
    return f"{product_id}:{staff_id}"


def ensure_defaults(conn) -> None:
    """XOS1 always exists and always carries the version from .env; anything
    recorded before products existed belongs to it."""
    row = conn["products"].find_one({"slug": DEFAULT}, {"id": 1})
    if row:
        pid = row["id"]
        conn["products"].update_one({"_id": pid}, {"$set": {"latest_version": config.LATEST_VERSION}})
    else:
        pid = db.next_id(conn, "products")
        conn["products"].insert_one({
            "_id": pid, "id": pid, "slug": DEFAULT, "name": config.PRODUCT, "full_name": config.PRODUCT_FULL,
            "description": "The AI layer for your PC: remembers you, runs on your machine.", "kind": "desktop",
            "website": "https://xiteai.com", "logo": "xos1-mark.png", "logo_invert": True,
            "latest_version": config.LATEST_VERSION, "status": "live", "is_demo": False, "created_at": db.now_iso(),
        })
    installs_store.run("UPDATE installs SET product_id = ? WHERE product_id = 0", (pid,))
    conn["tickets"].update_many({"product_id": 0}, {"$set": {"product_id": pid}})
    founder = conn["staff"].find_one({"level": "founder", "status": "active"}, {"id": 1}, sort=[("id", 1)])
    if founder:
        key = _member_key(pid, founder["id"])
        conn["product_members"].update_one(
            {"_id": key}, {"$setOnInsert": {"_id": key, "product_id": pid, "staff_id": founder["id"],
                                            "role": "Owner", "added_by": None, "added_at": db.now_iso()}},
            upsert=True)


def get_id(conn, slug: str) -> int | None:
    """For the server's own use: ignores the demo switch."""
    row = conn["products"].find_one({"slug": slug}, {"id": 1})
    return row["id"] if row else None


def get(conn, slug: str) -> dict:
    row = db.strip(conn["products"].find_one({"slug": slug or DEFAULT, **settings.demo_filter(conn)}))
    if not row:
        raise HTTPException(404, "No product with that name.")
    return row


def card(row: dict) -> dict:
    return {k: row[k] for k in ("id", "slug", "name", "full_name", "description", "kind", "website", "logo",
                                "latest_version", "status")} | {
        "logo_invert": bool(row["logo_invert"]), "is_demo": bool(row["is_demo"]),
        "unit": "Users" if row["kind"] == "web" else "Installs"}


def stats(conn, pid: int) -> dict:
    now = datetime.now(timezone.utc)
    d = settings.demo_filter(conn)
    day, month = db.iso(now - timedelta(days=1)), db.iso(now - timedelta(days=30))
    active_staff_ids = conn["staff"].distinct("id", {"status": "active", **d})
    demo_sql = installs_store.demo_sql(conn)
    return {
        "installs": installs_store.scalar(f"SELECT COUNT(*) FROM installs WHERE product_id = ?{demo_sql}", (pid,)),
        "active_today": installs_store.scalar(
            f"SELECT COUNT(*) FROM installs WHERE product_id = ? AND last_seen >= ?{demo_sql}", (pid, day)),
        "active_month": installs_store.scalar(
            f"SELECT COUNT(*) FROM installs WHERE product_id = ? AND last_seen >= ?{demo_sql}", (pid, month)),
        "open_tickets": conn["tickets"].count_documents({"product_id": pid, "status": {"$in": ["open", "in_progress"]},
                                                         **d}),
        "team": conn["product_members"].count_documents({"product_id": pid, "staff_id": {"$in": active_staff_ids}}),
    }


def listing(conn) -> list[dict]:
    rows = list(conn["products"].find(settings.demo_filter(conn)).sort([("is_demo", 1), ("created_at", 1)]))
    return [card(db.strip(r)) | {"stats": stats(conn, r["id"])} for r in rows]


def clean(body: dict, creating: bool) -> dict:
    out = {}
    for k in ("name", "full_name", "description", "website", "latest_version"):
        if body.get(k) is not None:
            out[k] = str(body[k]).strip()[:200]
    if creating or "name" in out:
        if len(out.get("name", "")) < 2:
            raise HTTPException(400, "Give the product a name.")
    if body.get("kind") is not None:
        if body["kind"] not in KINDS:
            raise HTTPException(400, "Kind is desktop or web.")
        out["kind"] = body["kind"]
    if body.get("status") is not None:
        if body["status"] not in STATUSES:
            raise HTTPException(400, "Status is live, building or paused.")
        out["status"] = body["status"]
    if creating:
        slug = (body.get("slug") or re.sub(r"[^a-z0-9]+", "-", out["name"].lower())).strip("-")
        if not _SLUG.match(slug):
            raise HTTPException(400, "Short name: lowercase letters, numbers and dashes.")
        out["slug"] = slug
    return out


def team(conn, pid: int) -> list[dict]:
    members = {m["staff_id"]: m for m in conn["product_members"].find({"product_id": pid})}
    staff_rows = list(conn["staff"].find({"id": {"$in": list(members)}, "status": "active", **settings.demo_filter(conn)}))
    order = {"Owner": 0, "Lead": 1, "Member": 2}
    pairs = [(members[s["id"]], s) for s in staff_rows]
    pairs.sort(key=lambda pair: (order.get(pair[0]["role"], 3), -levels.RANK[pair[1]["level"]],
                                 pair[1]["display_name"].lower()))
    return [{"id": s["id"], "display_name": s["display_name"], "initials": initials(s["display_name"]),
             "email": s["email"], "title": s["title"], "department": s["department"], "level": s["level"],
             "level_label": levels.LABEL[s["level"]], "role": m["role"], "added_at": m["added_at"],
             "is_demo": bool(s["is_demo"])} for m, s in pairs]
