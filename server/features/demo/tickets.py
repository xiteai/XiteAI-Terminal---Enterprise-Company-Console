"""Demo customer tickets."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ...core import db
from . import data as d


def seed(conn, rng: random.Random, now: datetime, product_id: int, codes: list[str], items=d.TICKETS) -> int:
    used: set[str] = set()
    for kind, status, priority, subject, message, days_ago in items:
        ref = f"XS-{rng.randint(100000, 999999)}"
        while ref in used or conn["tickets"].find_one({"ref": ref}, {"_id": 1}):
            ref = f"XS-{rng.randint(100000, 999999)}"
        used.add(ref)
        first, last = rng.choice(d.FIRST), rng.choice(d.LAST)
        created = now - timedelta(days=days_ago, hours=rng.randint(1, 20), minutes=rng.randint(0, 59))
        updated = min(created + timedelta(hours=rng.randint(0, 30)), now) if status != "open" else created
        tid = db.next_id(conn, "tickets")
        conn["tickets"].insert_one({
            "_id": tid, "id": tid, "product_id": product_id, "ref": ref, "kind": kind, "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower().replace(chr(39), '')}@example.com",
            "install_code": rng.choice(codes) if codes and rng.random() < 0.7 else "", "subject": subject,
            "message": message, "status": status, "priority": priority, "assignee_id": None,
            "created_at": created.isoformat(), "updated_at": updated.isoformat(), "ip": "", "is_demo": True,
        })
    return len(items)
