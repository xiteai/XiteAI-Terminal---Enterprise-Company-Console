"""Demo installs and their check-in history: a believable rollout of versions,
usage by hour and day, some churn, a few failed updates. A web product gets
browsers instead of Windows builds, and features instead of tools.

Built for one bulk `insert_many` of installs and one of checkins, not one
round trip per document: a demo seed is hundreds of installs and can be many
thousands of check-ins, and each round trip here goes over the network to
Atlas, not to a local file the way SQLite did."""
from __future__ import annotations

import base64
import hashlib
import json
import random
from datetime import datetime, timedelta

from ...core import db
from ..checkin.ingest import _CODE_ALPHABET
from ..checkin.verify import fingerprint
from . import data as d


DESKTOP = {"releases": d.RELEASES, "tools": (d.TOOLS, d.TOOL_WEIGHTS), "stuck": ["1.0.14", "1.0.15", "1.0.16"],
           "os": (["Windows 11 24H2", "Windows 11 23H2", "Windows 10 22H2"], [45, 30, 25]),
           "device": (["Laptop", "Desktop", "Tablet"], [68, 30, 2]), "crash": 0.12, "stuck_rate": 0.035}
WEB = {"releases": d.CHAT_RELEASES, "tools": (d.CHAT_FEATURES, d.CHAT_FEATURE_WEIGHTS), "stuck": [],
       "os": (["Chrome", "Edge", "Safari", "Firefox"], [58, 17, 18, 7]),
       "device": (["Laptop", "Desktop", "Phone", "Tablet"], [38, 16, 40, 6]), "crash": 0.04, "stuck_rate": 0}


def _version_at(releases, days_ago: float, first_seen_ago: float, lag: float, cap: str | None) -> str:
    v = releases[0][0]
    for ver, rel_ago in releases:
        if rel_ago >= first_seen_ago or rel_ago - lag >= days_ago:
            v = ver
        if cap and ver == cap:
            break
    return v


def _age(rng: random.Random) -> int:
    (lo, hi), = rng.choices([b for b, _ in d.AGE_BANDS], weights=[w for _, w in d.AGE_BANDS])
    return rng.randint(lo, hi)


def _times(rng, now: datetime, first_ago: float, profile: str, offset: float) -> list[datetime]:
    p_day, per_day, _ = d.PROFILES[profile]
    churn_ago = rng.uniform(8, max(9, first_ago)) if profile == "churned" else -1
    out = []
    for day in range(int(first_ago), -1, -1):
        weekend = (now - timedelta(days=day)).weekday() >= 5
        if day <= churn_ago or rng.random() >= p_day * (1.15 if weekend else 1):
            continue
        for _ in range(rng.randint(*per_day)):
            hour = rng.choices(range(24), weights=d.HOUR_WEIGHTS)[0]
            local = (now + timedelta(hours=offset) - timedelta(days=day)).replace(
                hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
            at = local - timedelta(hours=offset)
            if at <= now and (now - at).total_seconds() / 86400 <= first_ago:
                out.append(at)
    return sorted(out) or [now - timedelta(days=first_ago)]


def _codes(conn, rng: random.Random, count: int) -> list[str]:
    """`count` install codes, guaranteed unique against each other and against
    what's already stored — checked together, once, not once per code."""
    def draw() -> str:
        raw = "".join(rng.choice(_CODE_ALPHABET) for _ in range(8))
        return f"{raw[:4]}-{raw[4:]}"

    out: list[str] = []
    seen: set[str] = set()
    while len(out) < count:
        candidates = {c for c in (draw() for _ in range(count - len(out))) if c not in seen}
        taken = set(conn["installs"].distinct("code", {"code": {"$in": list(candidates)}})) if candidates else set()
        fresh = candidates - taken
        out.extend(fresh)
        seen |= fresh
    return out


def seed(conn, rng: random.Random, now: datetime, product_id: int, kind: str = "desktop",
         count: int = 186) -> tuple[list[str], int]:
    f = WEB if kind == "web" else DESKTOP
    rels = f["releases"]
    codes = _codes(conn, rng, count)
    install_ids = list(db.next_ids(conn, "installs", count))
    installs, per_install_times = [], []
    for i in range(count):
        if rng.random() < 0.22:
            region, tz, locale, offset = rng.choice(d.ABROAD)
            name = f"{rng.choice(d.FIRST_ABROAD)} {rng.choice(d.LAST_ABROAD)}"
        else:
            region, tz, locale, offset = rng.choice(d.REGIONS_IN), "Asia/Kolkata", "en-IN", 5.5
            name = f"{rng.choice(d.FIRST)} {rng.choice(d.LAST)}"
        age = _age(rng)
        dob = (now - timedelta(days=age * 365.25 + rng.randint(0, 364))).date().isoformat()
        first_ago = 1 + 139 * (rng.random() ** 1.7)
        profile = rng.choices(list(d.PROFILES), weights=[p[2] for p in d.PROFILES.values()])[0]
        stuck = rng.random() < f["stuck_rate"]
        cap = rng.choice(f["stuck"]) if stuck else None
        lag = rng.choice([0.1, 0.2, 0.4, 0.8, 1.5, 3.0])
        consent_profile, consent_usage = rng.random() < 0.8, rng.random() < 0.56
        times = _times(rng, now, first_ago, profile, offset)
        last = times[-1]
        crashes = rng.choice([1, 1, 2, 3]) if rng.random() < f["crash"] else 0
        pk = base64.b64encode(bytes(rng.getrandbits(8) for _ in range(32))).decode()
        install_id = install_ids[i]
        installs.append({
            "_id": install_id, "id": install_id, "product_id": product_id, "code": codes[i],
            "hardware_hash": hashlib.sha256(f"demo-{i}-{rng.random()}".encode()).hexdigest(), "public_key": pk,
            "key_fingerprint": fingerprint(pk), "status": "relinked" if rng.random() < 0.02 else "verified",
            "first_seen": (now - timedelta(days=first_ago)).isoformat(), "last_seen": last.isoformat(),
            "app_version": _version_at(rels, (now - last).total_seconds() / 86400, first_ago, lag, cap),
            "os_version": rng.choices(f["os"][0], weights=f["os"][1])[0],
            "device_type": rng.choices(f["device"][0], weights=f["device"][1])[0],
            "region": region, "timezone": tz, "locale": locale, "consent_profile": consent_profile,
            "consent_usage": consent_usage, "user_name": name if consent_profile else None,
            "user_dob": dob if consent_profile else None, "update_state": "failed" if stuck else "ok",
            "crash_count_7d": crashes, "checkin_count": len(times), "is_demo": True,
        })
        for at in times:
            ago = (now - at).total_seconds() / 86400
            tools = json.dumps(rng.choices(f["tools"][0], weights=f["tools"][1], k=rng.randint(1, 3))) \
                if consent_usage else None
            per_install_times.append({"install_id": install_id, "at": at.isoformat(),
                                      "app_version": _version_at(rels, ago, first_ago, lag, cap),
                                      "update_state": "failed" if stuck and ago < 6 else "ok",
                                      "crash_count": crashes if ago < 7 else 0, "tools_json": tools, "is_demo": True})
    if installs:
        conn["installs"].insert_many(installs)
    if per_install_times:
        ck_ids = db.next_ids(conn, "checkins", len(per_install_times))
        for ckid, doc in zip(ck_ids, per_install_times):
            doc["_id"] = doc["id"] = ckid
        conn["checkins"].insert_many(per_install_times)
    return codes, len(per_install_times)
