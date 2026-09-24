"""Load or remove all demo data in one go. Deterministic (fixed seed).

Demo data is XOS1 installs plus a second, demo-only product, a team and
tickets for both. Removing it is remembered, so a restart doesn't bring it
back; hiding it is a separate switch (core.settings.show_demo)."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from ...core import audit, db, settings
from ..products import service as products
from . import data as d
from . import installs, team, tickets


def present(conn) -> bool:
    return bool(conn["installs"].find_one({"is_demo": True}, {"_id": 1})
               or conn["staff"].find_one({"is_demo": True}, {"_id": 1}))


def _chat_product(conn, now: datetime) -> int:
    row = conn["products"].find_one({"slug": d.CHAT["slug"]}, {"id": 1})
    if row:
        return row["id"]
    pid = db.next_id(conn, "products")
    conn["products"].insert_one({
        "_id": pid, "id": pid, **{k: d.CHAT[k] for k in
            ("slug", "name", "full_name", "description", "kind", "website", "logo", "latest_version", "status")},
        "logo_invert": False, "is_demo": True, "created_at": now.isoformat(),
    })
    return pid


def load(conn) -> dict:
    """Not wrapped in db.tx(): this writes thousands of documents (every
    install's whole check-in history), and a MongoDB transaction is sized for
    a handful of related writes, not a bulk seed — one nearly took the server
    down here (Atlas aborted it mid-way: 'Transaction ... has been aborted').
    None of it is real data anyway; if this is ever interrupted partway,
    Purge demo data followed by Add demo data starts clean."""
    rng = random.Random(20051120)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    founder_row = conn["staff"].find_one({"level": "founder", "status": "active"}, {"id": 1}, sort=[("id", 1)])
    founder = founder_row["id"] if founder_row else None
    xos1 = products.get_id(conn, products.DEFAULT)
    chat = _chat_product(conn, now)
    codes, n_checkins = installs.seed(conn, rng, now, xos1)
    chat_codes, n_chat = installs.seed(conn, rng, now, chat, "web", count=240)
    n_tickets = (tickets.seed(conn, rng, now, xos1, codes)
                 + tickets.seed(conn, rng, now, chat, chat_codes, d.CHAT_TICKETS))
    ids = team.seed(conn, rng, now, founder)
    team.assign(conn, now, founder, {products.DEFAULT: xos1, d.CHAT["slug"]: chat}, ids)
    settings.put(conn, "demo_deleted", "0")
    settings.put(conn, "show_demo", "1")
    out = {"installs": len(codes) + len(chat_codes), "checkins": n_checkins + n_chat,
           "tickets": n_tickets, "people": len(ids)}
    audit.record(conn, None, "demo.loaded", "", ", ".join(f"{v} {k}" for k, v in out.items()))
    return out


def purge(conn) -> dict:
    """Not wrapped in db.tx() either, for the same reason: potentially
    thousands of deletes, and none of it real data."""
    demo_people = conn["staff"].distinct("id", {"is_demo": True})
    if demo_people:
        conn["notifications"].delete_many({"kind": {"$regex": "^join\\."}, "ref_id": {"$in": demo_people}})
        conn["staff"].update_many({"reports_to": {"$in": demo_people}, "is_demo": False},
                                  {"$set": {"reports_to": None}})
        conn["tickets"].update_many({"assignee_id": {"$in": demo_people}}, {"$set": {"assignee_id": None}})
    out = {
        "installs": conn["installs"].delete_many({"is_demo": True}).deleted_count,
        "tickets": conn["tickets"].delete_many({"is_demo": True}).deleted_count,
        "people": conn["staff"].delete_many({"is_demo": True}).deleted_count,
    }
    # A demo product only goes if nothing real has landed in it.
    used = set(conn["installs"].distinct("product_id")) | set(conn["tickets"].distinct("product_id"))
    out["products"] = conn["products"].delete_many({"is_demo": True, "id": {"$nin": list(used)}}).deleted_count
    settings.put(conn, "demo_deleted", "1")
    return out
