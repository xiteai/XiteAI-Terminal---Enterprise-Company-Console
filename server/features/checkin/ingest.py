"""Store a verified check-in.

The hardware hash says WHICH machine; the key proves it's the install holding
that machine's key. A known machine arriving with a different key (reinstall,
or an impostor) is accepted but marked 'relinked', the old key goes to
key_history and the audit log says so. Nothing is silently overwritten.
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta, timezone

from ...core import audit, db
from .verify import CheckinError, fingerprint, verify

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code(conn) -> str:
    while True:
        raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        code = f"{raw[:4]}-{raw[4:]}"
        if not conn["installs"].find_one({"code": code}, {"_id": 1}):
            return code


def _s(value, limit: int) -> str:
    return str(value or "")[:limit]


def _count(value) -> int:
    try:
        return max(0, min(int(value or 0), 9999))
    except (TypeError, ValueError):
        return 0


def _fields(payload: dict, now: str) -> dict:
    consent = payload.get("consent") if isinstance(payload.get("consent"), dict) else {}
    c_profile, c_usage = bool(consent.get("profile")), bool(consent.get("usage"))
    profile = payload.get("profile") if c_profile and isinstance(payload.get("profile"), dict) else {}
    dob = _s(profile.get("dob"), 10)
    return {
        "last_seen": now,
        "app_version": _s(payload.get("app_version"), 20),
        "os_version": _s(payload.get("os_version"), 60),
        "device_type": _s(payload.get("device_type"), 20),
        "region": _s(payload.get("region"), 60),
        "timezone": _s(payload.get("timezone"), 60),
        "locale": _s(payload.get("locale"), 20),
        "consent_profile": c_profile,
        "consent_usage": c_usage,
        # consent withdrawn = what we held is cleared on this very check-in
        "user_name": _s(profile.get("name"), 80) or None,
        "user_dob": dob if re.match(r"^\d{4}-\d{2}-\d{2}$", dob) else None,
        "update_state": payload.get("update_state") if payload.get("update_state") in ("ok", "failed", "pending")
        else "ok",
        "crash_count_7d": _count(payload.get("crash_count_7d")),
    }


def ingest(conn, body: dict, ip: str = "") -> dict:
    payload, pk_b64 = verify(body)
    now = db.now_iso()
    product = conn["products"].find_one({"slug": str(payload.get("product") or "xos1")}, {"id": 1})
    if not product:
        raise CheckinError(400, "unknown product")
    pid = product["id"]
    with db.tx(conn) as tconn:
        tconn["checkin_nonces"].delete_many({"at": {"$lt": db.iso(datetime.now(timezone.utc) - timedelta(days=1))}})
        if tconn["checkin_nonces"].find_one({"_id": payload["nonce"]}, {"_id": 1}):
            raise CheckinError(409, "nonce already used")
        tconn["checkin_nonces"].insert_one({"_id": payload["nonce"], "nonce": payload["nonce"], "at": now})

        fields = _fields(payload, now)
        row = db.strip(tconn["installs"].find_one({"product_id": pid, "hardware_hash": payload["hardware_hash"]}))
        relinked = False
        if row is None:
            code = new_code(tconn)
            install_id = db.next_id(tconn, "installs")
            tconn["installs"].insert_one({
                "_id": install_id, "id": install_id, "product_id": pid, "code": code,
                "hardware_hash": payload["hardware_hash"], "public_key": pk_b64, "key_fingerprint": fingerprint(pk_b64),
                "status": "verified", "first_seen": now, "last_seen": now, "app_version": "", "os_version": "",
                "device_type": "", "region": "", "timezone": "", "locale": "", "consent_profile": False,
                "consent_usage": False, "user_name": None, "user_dob": None, "update_state": "ok",
                "crash_count_7d": 0, "checkin_count": 0, "is_demo": False,
            })
            audit.record(tconn, None, "install.registered", code, "first check-in", ip)
        else:
            install_id, code = row["id"], row["code"]
            if row["public_key"] != pk_b64:
                relinked = True
                khid = db.next_id(tconn, "key_history")
                tconn["key_history"].insert_one({"_id": khid, "id": khid, "install_id": install_id,
                                                 "public_key": row["public_key"], "fingerprint": row["key_fingerprint"],
                                                 "replaced_at": now})
                tconn["installs"].update_one({"_id": install_id}, {"$set": {"public_key": pk_b64,
                                                                            "key_fingerprint": fingerprint(pk_b64),
                                                                            "status": "relinked"}})
                audit.record(tconn, None, "install.relinked", code, "same machine, new key (reinstall or impostor)", ip)

        tconn["installs"].update_one({"_id": install_id}, {"$set": fields, "$inc": {"checkin_count": 1}})
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        tools = usage.get("tools") if fields["consent_usage"] else None
        ckid = db.next_id(tconn, "checkins")
        tconn["checkins"].insert_one({
            "_id": ckid, "id": ckid, "install_id": install_id, "at": now, "app_version": fields["app_version"],
            "update_state": fields["update_state"], "crash_count": fields["crash_count_7d"],
            "tools_json": json.dumps([_s(t, 40) for t in tools][:50]) if isinstance(tools, list) else None,
            "is_demo": False,
        })
    return {"ok": True, "code": code, "relinked": relinked}
