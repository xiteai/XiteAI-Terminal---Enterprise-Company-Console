"""Listing, filtering and opening installs. Search and sort only ever use
fields the viewer is allowed to see, or a filter would leak what's hidden."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ...access import shaping
from ...core import audit, clock, db, settings
from ..releases.loader import version_key

STATES = ("active", "idle", "dormant", "relinked", "update_failed", "crashing")


def listing(conn, a: dict, product: dict, q: str, version: str, state: str, sort: str, direction: str, page: int,
            page_size: int) -> dict:
    p = a["perms"]
    now = datetime.now(timezone.utc)
    filt: dict = {"product_id": product["id"], **settings.demo_filter(conn)}
    q = q.strip()[:80]
    if q:
        needle = re.escape(q)
        like = {"$regex": needle, "$options": "i"}
        cond = [{"code": like}, {"app_version": like}, {"os_version": like}, {"device_type": like}]
        if "cust.name" in p:
            cond.append({"consent_profile": True, "user_name": like})
        if "cust.region" in p:
            cond.append({"region": like})
        filt["$or"] = cond
    if version:
        filt["app_version"] = version[:20]
    day, week = db.iso(now - timedelta(days=1)), db.iso(now - timedelta(days=7))
    if state in STATES:
        filt.update({"active": {"last_seen": {"$gte": day}}, "idle": {"last_seen": {"$lt": day, "$gte": week}},
                    "dormant": {"last_seen": {"$lt": week}}, "relinked": {"status": "relinked"},
                    "update_failed": {"update_state": "failed"},
                    "crashing": {"crash_count_7d": {"$gt": 0}}}[state])
    rows = [db.strip(r) for r in conn["installs"].find(filt)]
    versions = sorted({v for v in conn["installs"].distinct("app_version", {"product_id": product["id"]}) if v},
                      key=version_key, reverse=True)
    keys = {
        "last_seen": lambda r: r["last_seen"],
        "first_seen": lambda r: r["first_seen"],
        "version": lambda r: version_key(r["app_version"]),
        "checkins": lambda r: r["checkin_count"],
        "code": lambda r: r["code"],
    }
    if "cust.name" in p:
        keys["name"] = lambda r: (r["user_name"] or "~").lower() if r["consent_profile"] else "~"
    if "cust.age" in p:
        keys["age"] = lambda r: (shaping.age_from_dob(r["user_dob"]) or 999) if r["consent_profile"] else 999
    rows.sort(key=keys.get(sort, keys["last_seen"]), reverse=(direction != "asc"))
    page_size = max(5, min(page_size, 100))
    pages = max(1, -(-len(rows) // page_size))
    page = max(1, min(page, pages))
    return {"total": len(rows), "page": page, "pages": pages, "page_size": page_size, "versions": versions,
            "sortable": sorted(keys), "customer_visibility": shaping.describe(p),
            "items": [shaping.install(r, p) for r in rows[(page - 1) * page_size: page * page_size]]}


def detail(conn, a: dict, install_id: int, product: dict) -> dict:
    p = a["perms"]
    row = db.strip(conn["installs"].find_one({"_id": install_id, "product_id": product["id"], **settings.demo_filter(conn)}))
    if not row:
        raise HTTPException(404, "No install with that id.")
    cks = list(conn["checkins"].find({"install_id": install_id},
                                     {"at": 1, "app_version": 1, "update_state": 1, "crash_count": 1, "tools_json": 1})
              .sort("at", -1))
    keys = list(conn["key_history"].find({"install_id": install_id}, {"fingerprint": 1, "replaced_at": 1})
               .sort("replaced_at", -1)) if "cust.fingerprints" in p else []
    if row["consent_profile"] and {"cust.name", "cust.dob", "cust.age"} & p and not a["previewing"]:
        audit.record(conn, a, "install.viewed", row["code"], "opened a customer profile", a["ip"])
    today = clock.today()
    per_day = Counter(clock.local(c["at"]).date() for c in cks)
    tools: Counter = Counter()
    for c in cks:
        if c.get("tools_json"):
            try:
                tools.update(json.loads(c["tools_json"]))
            except (ValueError, TypeError):
                pass
    history = []
    for c in reversed(cks):
        if not history or history[-1]["version"] != c["app_version"]:
            history.append({"version": c["app_version"], "since": c["at"]})
    return {
        "install": shaping.install(row, p),
        "daily": [{"date": (today - timedelta(days=i)).isoformat(), "value": per_day.get(today - timedelta(days=i), 0)}
                  for i in range(29, -1, -1)],
        "recent": [{"at": c["at"], "version": c["app_version"], "update_state": c["update_state"],
                    "crash_count": c["crash_count"]} for c in cks[:20]],
        "versions": list(reversed(history))[:8],
        "tools": [{"label": k, "value": v} for k, v in tools.most_common(6)],
        "key_history": [{"fingerprint": k["fingerprint"], "replaced_at": k["replaced_at"]} for k in keys],
        "can_erase": "installs.erase" in p and not a["previewing"],
    }


def erase(conn, a: dict, install_id: int) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = conn["installs"].find_one({"_id": install_id}, {"code": 1})
    if not row:
        raise HTTPException(404, "No install with that id.")
    conn["installs"].delete_one({"_id": install_id})
    audit.record(conn, a, "install.erased", row["code"], "every record for this install deleted", a["ip"])
