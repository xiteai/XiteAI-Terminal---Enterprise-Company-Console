"""Store verified check-ins, a batch at a time, in the installs store (SQLite).

The hardware hash says WHICH machine; the key proves it's the install holding
that machine's key. A known machine arriving with a different key (reinstall,
or an impostor) is accepted but marked 'relinked', the old key goes to
key_history and the audit trail says so. Nothing is silently overwritten.

Only batcher.py calls write(): one writer, one transaction per batch, one
savepoint per check-in so a bad one fails alone."""
from __future__ import annotations

import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from ...core import config, db
from ..installs import store
from .verify import CheckinError, fingerprint

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _s(value, limit: int) -> str:
    return str(value or "")[:limit]


def _count(value) -> int:
    try:
        return max(0, min(int(value or 0), 9999))
    except (TypeError, ValueError):
        return 0


def fields(payload: dict, now: str) -> dict:
    consent = payload.get("consent") if isinstance(payload.get("consent"), dict) else {}
    c_profile, c_usage = bool(consent.get("profile")), bool(consent.get("usage"))
    profile = payload.get("profile") if c_profile and isinstance(payload.get("profile"), dict) else {}
    dob = _s(profile.get("dob"), 10)
    version = _s(payload.get("app_version"), 20)
    return {
        "last_seen": now,
        "app_version": version,
        "version_sort": store.version_sort(version),
        "os_version": _s(payload.get("os_version"), 60),
        "device_type": _s(payload.get("device_type"), 20),
        "region": _s(payload.get("region"), 60),
        "timezone": _s(payload.get("timezone"), 60),
        "locale": _s(payload.get("locale"), 20),
        "consent_profile": int(c_profile),
        "consent_usage": int(c_usage),
        # consent withdrawn = what we held is cleared on this very check-in
        "user_name": _s(profile.get("name"), 80) or None,
        "user_dob": dob if re.match(r"^\d{4}-\d{2}-\d{2}$", dob) else None,
        "update_state": payload.get("update_state") if payload.get("update_state") in ("ok", "failed", "pending")
        else "ok",
        "crash_count_7d": _count(payload.get("crash_count_7d")),
    }


def _new_code(t) -> str:
    while True:
        raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        code = f"{raw[:4]}-{raw[4:]}"
        if not t.scalar("SELECT 1 FROM installs WHERE code = ?", (code,)):
            return code


def _one(t, it: dict) -> tuple[dict, tuple | None]:
    """One check-in. Returns (answer, audit event or None)."""
    payload, pk, now = it["payload"], it["public_key"], it["at"]
    if not t.run("INSERT OR IGNORE INTO checkin_nonces (nonce, at) VALUES (?, ?)", (payload["nonce"], now)).rowcount:
        raise CheckinError(409, "nonce already used")
    f = fields(payload, now)
    row = t.one("SELECT id, code, public_key, key_fingerprint FROM installs WHERE product_id = ? AND hardware_hash = ?",
                (it["product_id"], payload["hardware_hash"]))
    event = None
    if row is None:
        code = _new_code(t)
        install_id = t.run("INSERT INTO installs (product_id, code, hardware_hash, public_key, key_fingerprint, "
                           "first_seen, last_seen) VALUES (?,?,?,?,?,?,?)",
                           (it["product_id"], code, payload["hardware_hash"], pk, fingerprint(pk), now, now)).lastrowid
        relinked = False
    else:
        install_id, code = row["id"], row["code"]
        relinked = row["public_key"] != pk
        if relinked:
            t.run("INSERT INTO key_history (install_id, public_key, fingerprint, replaced_at) VALUES (?,?,?,?)",
                  (install_id, row["public_key"], row["key_fingerprint"], now))
            t.run("UPDATE installs SET public_key = ?, key_fingerprint = ?, status = 'relinked' WHERE id = ?",
                  (pk, fingerprint(pk), install_id))
            event = ("install.relinked", code, "same machine, new key (reinstall or impostor)", it["ip"])
    t.run(f"UPDATE installs SET {', '.join(f'{k} = ?' for k in f)}, checkin_count = checkin_count + 1 WHERE id = ?",
          (*f.values(), install_id))
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    tools = usage.get("tools") if f["consent_usage"] else None
    t.run("INSERT INTO checkins (install_id, at, app_version, update_state, crash_count, tools_json) VALUES (?,?,?,?,?,?)",
          (install_id, now, f["app_version"], f["update_state"], f["crash_count_7d"],
           json.dumps([_s(x, 40) for x in tools][:50]) if isinstance(tools, list) else None))
    return {"ok": True, "code": code, "relinked": relinked, "next_after_s": _next_after(payload["hardware_hash"])}, event


def _next_after(hardware_hash: str) -> int:
    """When this machine should come back. The spread comes from its own hash,
    so every install sits in a fixed slot of the window instead of all of them
    waking together after an outage — and it survives a restart, because
    nothing about it is remembered here."""
    slot = int(hardware_hash[:8], 16) % max(1, config.CHECKIN_SPREAD_S)
    return config.CHECKIN_EVERY_S + slot


_nonces_swept = 0.0


def write(items: list[dict]) -> tuple[list, list[tuple]]:
    """[answer dict | CheckinError] in the same order as `items`, plus the audit
    events to record once the batch is safely stored."""
    global _nonces_swept
    answers, events = [], []
    with store.tx() as t:
        if time.monotonic() - _nonces_swept > 600:      # a day's nonces are enough to stop a replay
            t.run("DELETE FROM checkin_nonces WHERE at < ?", (db.iso(datetime.now(timezone.utc) - timedelta(days=1)),))
            _nonces_swept = time.monotonic()
        for it in items:
            t.run("SAVEPOINT one")
            try:
                answer, event = _one(t, it)
            except CheckinError as e:
                t.run("ROLLBACK TO one")
                answer, event = e, None
            except Exception as e:                            # noqa: BLE001 — one bad check-in fails alone
                t.run("ROLLBACK TO one")
                answer, event = e, None
            t.run("RELEASE one")
            answers.append(answer)
            if event:
                events.append(event)
    return answers, events
