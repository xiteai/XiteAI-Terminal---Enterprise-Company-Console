"""Secrets the server must be able to use again later — provider API keys.

AES-256-GCM, one random nonce per value, authenticated so a tampered
ciphertext fails to open rather than decrypting to garbage. The master key
comes from the environment and is never written to the database: whoever
holds the database alone holds nothing useful.

    blob = vault.seal("sk-live-…")        # -> {"n": …, "c": …}
    key  = vault.open_(blob)              # -> "sk-live-…"

Without TC_VAULT_KEY set, seal() refuses rather than storing anything
recoverable. Generate one with:  python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
"""
from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config


class VaultError(Exception):
    """No usable master key, or a value that won't open."""


def _master() -> bytes:
    raw = config.VAULT_KEY or os.environ.get("TC_VAULT_KEY", "")
    if not raw:
        raise VaultError("TC_VAULT_KEY isn't set, so there's nowhere safe to keep a key.")
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except (ValueError, TypeError):
        raise VaultError("TC_VAULT_KEY isn't valid base64.") from None
    if len(key) != 32:
        raise VaultError("TC_VAULT_KEY must decode to 32 bytes.")
    return key


def ready() -> bool:
    try:
        _master()
        return True
    except VaultError:
        return False


def seal(plaintext: str) -> dict:
    nonce = os.urandom(12)
    ct = AESGCM(_master()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return {"n": base64.b64encode(nonce).decode(), "c": base64.b64encode(ct).decode()}


def open_(blob: dict) -> str:
    if not isinstance(blob, dict) or "n" not in blob or "c" not in blob:
        raise VaultError("That secret isn't in a shape this can open.")
    try:
        nonce = base64.b64decode(blob["n"])
        ct = base64.b64decode(blob["c"])
        return AESGCM(_master()).decrypt(nonce, ct, None).decode("utf-8")
    except (InvalidTag, ValueError, TypeError):
        raise VaultError("That secret won't open — the master key changed, or it was tampered with.") from None
