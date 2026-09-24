"""Is this check-in genuine? Ed25519 signature over the exact payload bytes,
a fresh timestamp, and a well-formed hardware hash. The contract is
contract/checkin.schema.json."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...core import config, db

MAX_PAYLOAD_BYTES = 8 * 1024
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CheckinError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def fingerprint(public_key_b64: str) -> str:
    h = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:16].upper()
    return " ".join(h[i:i + 4] for i in range(0, 16, 4))


def _b64(value, what: str) -> bytes:
    try:
        return base64.b64decode(str(value), validate=True)
    except (binascii.Error, ValueError):
        raise CheckinError(400, f"{what} is not valid base64")


def verify(body: dict) -> tuple[dict, str]:
    """Return (payload, public_key_b64) or raise CheckinError."""
    if not isinstance(body, dict):
        raise CheckinError(400, "body must be a JSON object")
    raw, sig, pk = (_b64(body.get("payload"), "payload"), _b64(body.get("signature"), "signature"),
                    _b64(body.get("public_key"), "public_key"))
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise CheckinError(413, "payload too large")
    if len(pk) != 32 or len(sig) != 64:
        raise CheckinError(400, "public_key must be 32 bytes and signature 64 bytes")
    try:
        Ed25519PublicKey.from_public_bytes(pk).verify(sig, raw)
    except InvalidSignature:
        raise CheckinError(401, "signature does not match payload")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise CheckinError(400, "payload is not JSON")
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise CheckinError(400, "unsupported payload version")
    if not _HEX64.match(str(payload.get("hardware_hash", ""))):
        raise CheckinError(400, "hardware_hash must be 64 lowercase hex characters")
    try:
        sent = db.parse_iso(str(payload.get("sent_at", "")))
    except ValueError:
        raise CheckinError(400, "sent_at must be an ISO-8601 timestamp")
    if abs(datetime.now(timezone.utc) - sent) > timedelta(minutes=config.CHECKIN_MAX_SKEW_MIN):
        raise CheckinError(400, "sent_at is too far from server time")
    if not 16 <= len(str(payload.get("nonce", ""))) <= 64:
        raise CheckinError(400, "nonce must be 16-64 characters")
    return payload, base64.b64encode(pk).decode()
