"""Demo installs and their check-in history: a believable rollout of versions,
usage by hour and day, some churn, a few failed updates. A web product gets
browsers instead of Windows builds, and features instead of tools.

Installs and check-ins live in the local SQLite store now (features/installs/
store.py), so this is one transaction of a few thousand rows — no round trip
per document the way Atlas would have needed."""
from __future__ import annotations

import base64
import hashlib
import json
import random
from datetime import datetime, timedelta

from ..checkin.ingest import _CODE_ALPHABET
from ..checkin.verify import fingerprint
from ..installs import store as installs_store
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


def _codes(rng: random.Random, count: int) -> list[str]:
    """`count` install codes, guaranteed unique against each other and against
    what's already stored — checked together, once, not once per code."""
    def draw() -> str:
        raw = "".join(rng.choice(_CODE_ALPHABET) for _ in range(8))
        return f"{raw[:4]}-{raw[4:]}"

    out: list[str] = []
    seen: set[str] = set()
    while len(out) < count:
        candidates = {c for c in (draw() for _ in range(count - len(out))) if c not in seen}
        if candidates:
            marks = ",".join("?" * len(candidates))
            taken = {r["code"] for r in installs_store.rows(
                f"SELECT code FROM installs WHERE code IN ({marks})", list(candidates))}
        else:
            taken = set()
        fresh = candidates - taken
        out.extend(fresh)
        seen |= fresh
    return out


def seed(conn, rng: random.Random, now: datetime, product_id: int, kind: str = "desktop",
         count: int = 186) -> tuple[list[str], int]:
    f = WEB if kind == "web" else DESKTOP
    rels = f["releases"]
    codes = _codes(rng, count)
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
        version = _version_at(rels, (now - last).total_seconds() / 86400, first_ago, lag, cap)
        installs.append((
            product_id, codes[i], hashlib.sha256(f"demo-{i}-{rng.random()}".encode()).hexdigest(), pk,
            fingerprint(pk), "relinked" if rng.random() < 0.02 else "verified",
            (now - timedelta(days=first_ago)).isoformat(), last.isoformat(), version,
            installs_store.version_sort(version),
            rng.choices(f["os"][0], weights=f["os"][1])[0], rng.choices(f["device"][0], weights=f["device"][1])[0],
            region, tz, locale, int(consent_profile), int(consent_usage), name if consent_profile else None,
            dob if consent_profile else None, "failed" if stuck else "ok", crashes, len(times), 1,
        ))
        for at in times:
            ago = (now - at).total_seconds() / 86400
            tools = json.dumps(rng.choices(f["tools"][0], weights=f["tools"][1], k=rng.randint(1, 3))) \
                if consent_usage else None
            per_install_times.append((i, at.isoformat(),
                                      _version_at(rels, ago, first_ago, lag, cap), "failed" if stuck and ago < 6 else "ok",
                                      crashes if ago < 7 else 0, tools))
    with installs_store.tx() as t:
        install_ids = []
        for row in installs:
            install_ids.append(t.run(
                "INSERT INTO installs (product_id, code, hardware_hash, public_key, key_fingerprint, status, "
                "first_seen, last_seen, app_version, version_sort, os_version, device_type, region, timezone, "
                "locale, consent_profile, consent_usage, user_name, user_dob, update_state, crash_count_7d, "
                "checkin_count, is_demo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row).lastrowid)
        if per_install_times:
            t.many("INSERT INTO checkins (install_id, at, app_version, update_state, crash_count, tools_json, "
                  "is_demo) VALUES (?,?,?,?,?,?,1)",
                  [(install_ids[i], at, v, us, cc, tj) for i, at, v, us, cc, tj in per_install_times])
    return codes, len(per_install_times)
