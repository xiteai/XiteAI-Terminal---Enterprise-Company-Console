"""A product's overview (headline numbers, activity, how it's used) and the
company snapshot for the home screen. Everything personal is shaped by the
viewer's permissions; everything respects the demo switch."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from ...access import levels, shaping
from ...core import clock, db, settings
from ..installs import store as installs_store
from ..releases.loader import version_key
from ..requests import service as requests


def _share(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def build(conn, a: dict, days: int, product: dict) -> dict:
    p = a["perms"]
    pid = product["id"]
    d = settings.demo_filter(conn)
    now = datetime.now(timezone.utc)
    start, prev = now - timedelta(days=days), now - timedelta(days=2 * days)
    today = clock.today()
    start_iso = db.iso(start)
    demo_sql = installs_store.demo_sql(conn)

    # Every install this product has, matching the demo switch: the universe
    # everything below (counts, the checkins join, "recent") draws from.
    eligible = {r["id"]: r for r in installs_store.rows(f"SELECT * FROM installs WHERE product_id = ?{demo_sql}", (pid,))}
    total = len(eligible)
    active_24h = installs_store.scalar(
        f"SELECT COUNT(*) FROM installs WHERE product_id = ? AND last_seen >= ?{demo_sql}",
        (pid, db.iso(now - timedelta(days=1))))
    ids = list(eligible)
    marks = ",".join("?" * len(ids)) if ids else "NULL"
    cks = installs_store.rows(f"SELECT * FROM checkins WHERE install_id IN ({marks}) AND at >= ?", (*ids, db.iso(prev)))
    firsts = [r["first_seen"] for r in eligible.values() if r["first_seen"] >= db.iso(prev)]
    act = [r for r in eligible.values() if r["last_seen"] >= start_iso]
    recent_cks = installs_store.rows(
        f"SELECT * FROM checkins WHERE install_id IN ({marks}) ORDER BY at DESC LIMIT 8", ids) if ids else []
    recent = [{"c_at": c["at"], "c_version": c["app_version"], **eligible[c["install_id"]]} for c in recent_cks]

    day_sets: dict = {}
    heat = [[0] * 24 for _ in range(7)]
    tools: Counter = Counter()
    now_ids, prev_ids = set(), set()
    for r in cks:
        local = clock.local(r["at"])
        day_sets.setdefault(local.date(), set()).add(r["install_id"])
        if r["at"] >= start_iso:
            now_ids.add(r["install_id"])
            heat[local.weekday()][local.hour] += 1
            if r.get("tools_json"):
                try:
                    tools.update(json.loads(r["tools_json"]))
                except (ValueError, TypeError):
                    pass
        else:
            prev_ids.add(r["install_id"])

    new_by_day = Counter(clock.local(f).date() for f in firsts)
    series = [{"date": (today - timedelta(days=i)).isoformat(), "value": len(day_sets.get(today - timedelta(days=i), ()))}
              for i in range(days - 1, -1, -1)]
    n = len(act)
    versions = Counter(r["app_version"] or "unknown" for r in act)
    latest = product["latest_version"]
    out = {
        "range": days,
        "generated_at": db.now_iso(),
        "tz_label": clock.LABEL,
        "latest_version": latest,
        "kpis": {
            "total_installs": total,
            "active_24h": active_24h,
            "active_period": len(now_ids),
            "active_prev_period": len(prev_ids),
            "new_installs": sum(new_by_day.get(today - timedelta(days=i), 0) for i in range(days)),
            "new_installs_prev": sum(new_by_day.get(today - timedelta(days=days + i), 0) for i in range(days)),
            "on_latest": _share(versions.get(latest, 0), n),
            "update_ok": _share(sum(1 for r in act if r["update_state"] != "failed"), n),
            "crash_free": _share(sum(1 for r in act if not r["crash_count_7d"]), n),
            "downloads_period": store.scalar(
                f"SELECT COUNT(*) FROM downloads WHERE product_id = ? AND at >= ?{store.demo_sql(conn)}",
                (pid, (today - timedelta(days=days)).isoformat())) or 0,
            "downloads_total": store.scalar(
                f"SELECT COUNT(*) FROM downloads WHERE product_id = ?{store.demo_sql(conn)}", (pid,)) or 0,
            "open_tickets": conn["tickets"].count_documents(
                {"product_id": pid, "status": {"$in": ["open", "in_progress"]}, **d}),
            "urgent_tickets": conn["tickets"].count_documents({
                "product_id": pid, "status": {"$in": ["open", "in_progress"]}, "priority": {"$in": ["high", "urgent"]}, **d}),
        },
        "active_series": series,
        "versions": [{"label": v, "value": c} for v, c in sorted(versions.items(), key=lambda kv: version_key(kv[0]),
                                                                  reverse=True)],
        "os": [{"label": k, "value": v} for k, v in Counter(r["os_version"] or "Unknown" for r in act).most_common(6)],
        "heatmap": {"rows": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "values": heat},
        "tools": [{"label": k, "value": v} for k, v in tools.most_common(8)],
        "usage_optin": _share(sum(1 for r in act if r["consent_usage"]), n),
        "profile_optin": _share(sum(1 for r in act if r["consent_profile"]), n),
        "recent": [{"at": r["c_at"], "version": r["c_version"], "id": r["id"], "code": r["code"],
                    "device_type": r["device_type"], "is_demo": bool(r["is_demo"]),
                    "person": shaping.person(r, p), **({"region": r["region"]} if "cust.region" in p else {})}
                   for r in recent],
    }
    if "overview.demographics" in p:
        bands = Counter(shaping.age_band(shaping.age_from_dob(r["user_dob"]))
                        for r in act if r["consent_profile"] and r["user_dob"])
        out["age_bands"] = [{"label": b, "value": bands.get(b, 0)} for b in shaping.BANDS]
        if "cust.region" in p:
            out["regions"] = [{"label": k, "value": v} for k, v in
                              Counter(r["region"] for r in act if r["region"]).most_common(8)]
    return out


def company(conn, a: dict) -> dict:
    """Home screen: the team at a glance, and what's waiting for you."""
    active = list(conn["staff"].find({"status": "active", **settings.demo_filter(conn)}, {"level": 1, "department": 1}))
    out = {
        "headcount": len(active),
        "by_department": [{"label": k, "value": v} for k, v in
                          Counter(r["department"] or "Unassigned" for r in active).most_common(8)],
        "by_level": [{"label": levels.LABEL[k], "value": sum(1 for r in active if r["level"] == k)}
                     for k in levels.KEYS if any(r["level"] == k for r in active)],
    }
    if "people.approve" in a["perms"]:
        out["pending"] = requests.visible(conn, a)[:6]
        out["recent_decisions"] = requests.recent_decisions(conn, 5)
    return out
