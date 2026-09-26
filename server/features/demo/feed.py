"""Demo posts for the Home feed: a couple of upcoming events, one with a
result already in, and news worth telling everyone."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ...core import db

POSTS = [
    ("funding", "We closed our Series A", "$4.2M led by Lightspeed, with participation from our seed investors. Onward.", None, None, 40),
    ("achievement", "XOS1 crossed 10,000 installs", "A milestone four years in the making. Thank you to everyone who shipped a piece of it.", None, None, 12),
    ("event", "Company offsite — Goa", "Three days, the whole team, and a lot of sand.", 21, None, 5),
    ("event", "Q3 hack day", "Twenty-four hours, any idea, no roadmap. Prizes for the best three.", -9, "Fourteen teams. The winning build shipped to production the following Monday.", 8),
    ("news", "New office, same address", "We've taken the third floor too. More desks, a proper standing-meeting corner, and yes, a second coffee machine.", None, None, 25),
]


def seed(conn, rng: random.Random, now: datetime, founder_id: int | None) -> int:
    if not founder_id:
        return 0
    for kind, title, body, day_offset, result, days_ago in POSTS:
        posted_at = (now - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        event_date = (now.date() + timedelta(days=day_offset)).isoformat() if day_offset is not None else ""
        aid = db.next_id(conn, "announcements")
        conn["announcements"].insert_one({"_id": aid, "id": aid, "kind": kind, "title": title, "body": body,
                                          "event_date": event_date, "result": result or "", "posted_by": founder_id,
                                          "posted_at": posted_at, "is_demo": True})
    return len(POSTS)


def purge(conn) -> int:
    return conn["announcements"].delete_many({"is_demo": True}).deleted_count
