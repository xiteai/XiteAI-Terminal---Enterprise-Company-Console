"""Listing, filtering and opening installs. Search and sort only ever use
fields the viewer is allowed to see, or a filter would leak what's hidden.

Installs and their check-ins live in a local SQLite file (store.py), not
MongoDB: `conn` here is only for the audit trail and settings.demo_filter."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ...access import shaping
from ...core import audit, clock, db
from ..releases.loader import version_key
from . import store

STATES = ("active", "idle", "dormant", "relinked", "update_failed", "crashing")


def _escaped_like(q: str) -> str:
    """`q` as a LIKE pattern, with its own % and _ treated as literal characters."""
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def listing(conn, a: dict, product: dict, q: str, version: str, state: str, sort: str, direction: str, page: int,
            page_size: int) -> dict:
    p = a["perms"]
    now = datetime.now(timezone.utc)
    where, args = ["product_id = ?"], [product["id"]]
    q = q.strip()[:80]
    if q:
        pat = _escaped_like(q)
        ors = ["code LIKE ? ESCAPE '\\'", "app_version LIKE ? ESCAPE '\\'", "os_version LIKE ? ESCAPE '\\'",
               "device_type LIKE ? ESCAPE '\\'"]
        ors_args = [pat, pat, pat, pat]
        if "cust.name" in p:
            ors.append("(consent_profile = 1 AND user_name LIKE ? ESCAPE '\\')")
            ors_args.append(pat)
        if "cust.region" in p:
            ors.append("region LIKE ? ESCAPE '\\'")
            ors_args.append(pat)
        where.append("(" + " OR ".join(ors) + ")")
        args += ors_args
    if version:
        where.append("app_version = ?")
        args.append(version[:20])
    day, week = db.iso(now - timedelta(days=1)), db.iso(now - timedelta(days=7))
    if state in STATES:
        cond, cond_args = {
            "active": ("last_seen >= ?", [day]), "idle": ("last_seen < ? AND last_seen >= ?", [day, week]),
            "dormant": ("last_seen < ?", [week]), "relinked": ("status = 'relinked'", []),
            "update_failed": ("update_state = 'failed'", []), "crashing": ("crash_count_7d > 0", []),
        }[state]
        where.append(cond)
        args += cond_args
    rows = store.rows(f"SELECT * FROM installs WHERE {' AND '.join(where)}" + store.demo_sql(conn), args)
    versions = sorted({r["app_version"] for r in store.rows(
        "SELECT DISTINCT app_version FROM installs WHERE product_id = ?", (product["id"],)) if r["app_version"]},
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
    row = store.one("SELECT * FROM installs WHERE id = ? AND product_id = ?" + store.demo_sql(conn),
                    (install_id, product["id"]))
    if not row:
        raise HTTPException(404, "No install with that id.")
    cks = store.rows("SELECT at, app_version, update_state, crash_count, tools_json FROM checkins "
                     "WHERE install_id = ? ORDER BY at DESC", (install_id,))
    keys = store.rows("SELECT fingerprint, replaced_at FROM key_history WHERE install_id = ? ORDER BY replaced_at DESC",
                      (install_id,)) if "cust.fingerprints" in p else []
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
    row = store.one("SELECT code FROM installs WHERE id = ?", (install_id,))
    if not row:
        raise HTTPException(404, "No install with that id.")
    store.run("DELETE FROM installs WHERE id = ?", (install_id,))    # its check-ins and key history go with it
    audit.record(conn, a, "install.erased", row["code"], "every record for this install deleted", a["ip"])
