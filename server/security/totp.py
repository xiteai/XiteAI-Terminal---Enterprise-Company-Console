"""Authenticator-app codes (RFC 6238: SHA-1, 6 digits, 30 s steps, ±1 step of drift)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse


def _code(secret_b32: str, counter: int) -> str:
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def verify(secret_b32: str, code: str) -> bool:
    code = (code or "").strip().replace(" ", "")
    if not (code.isdigit() and len(code) == 6):
        return False
    step = int(time.time()) // 30
    try:
        return any(hmac.compare_digest(_code(secret_b32, step + d), code) for d in (-1, 0, 1))
    except Exception:
        return False


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def setup_uri(secret: str, account: str, issuer: str) -> str:
    """The otpauth:// link an authenticator app reads from a QR code."""
    label = urllib.parse.quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?" + urllib.parse.urlencode({"secret": secret, "issuer": issuer, "digits": 6, "period": 30})
