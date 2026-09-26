"""Short-lived device tokens, so the OpenAI SDK can talk to the gateway.

WHY A TOKEN AT ALL. The app already proves who it is with an Ed25519
signature, which is stronger than any token — but the `openai` SDK can only
send a bearer header, and rewriting streaming, retries and back-off inside
XOS1 to carry signatures instead would be a lot of new code in the one place
a bug is most expensive. So the signature stays as the root of trust: the app
signs once, gets a token that lasts minutes, and the SDK uses that.

WHY STATELESS. The token carries its own claims and an HMAC over them, keyed
by the vault master key. Nothing is stored, so there's no table to grow, no
lookup on the hot path, nothing to replicate between servers, and a restart
doesn't sign everyone out. It also means a leaked database contains no usable
tokens, because there are none in it.

WHAT MAKES IT SAFE ANYWAY:
  - minutes, not days: a copied token is worthless almost immediately
  - bound to one machine: the hardware hash is inside the signed claims, and
    the device is re-checked on every call, so deactivating an install kills
    its tokens within the device cache's 60 seconds
  - tamper-evident: changing a single byte of the claims breaks the HMAC
  - constant-time comparison, so the check can't be probed a byte at a time
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from ...core import config, vault

TTL_S = 15 * 60
_PREFIX = "xtg1"          # so a token is recognisable in a log without revealing it


class TokenError(Exception):
    """Expired, tampered with, or not a token at all."""


def _secret() -> bytes:
    """Derived from the vault master key, not the key itself: this signs
    tokens and nothing else, so it can never decrypt anything."""
    return hashlib.sha256(b"gateway-token|" + vault._master()).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(product_id: int, hardware_hash: str) -> tuple[str, int]:
    """(token, seconds until it expires)."""
    claims = {"p": product_id, "h": hardware_hash, "e": int(time.time()) + TTL_S}
    body = _b64(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{_PREFIX}.{body}.{sig}", TTL_S


def read(token: str) -> tuple[int, str]:
    """(product_id, hardware_hash) or raise TokenError."""
    try:
        prefix, body, sig = token.split(".", 2)
    except (ValueError, AttributeError):
        raise TokenError("not a token") from None
    if prefix != _PREFIX:
        raise TokenError("not a token")
    expected = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise TokenError("token doesn't check out")
    try:
        claims = json.loads(_unb64(body))
    except (ValueError, TypeError):
        raise TokenError("token doesn't check out") from None
    if int(claims.get("e", 0)) < time.time():
        raise TokenError("token expired")
    return int(claims["p"]), str(claims["h"])
