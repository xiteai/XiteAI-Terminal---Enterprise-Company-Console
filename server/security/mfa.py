"""Authenticator codes for everyone, not only the founder.

The founder's seed can live in .env (FOUNDER_TOTP_SECRET, as before); anyone
else sets one up from Account, and it's stored sealed (security/vault.py).
A session remembers whether it was opened with a code: the codebase asks."""
from __future__ import annotations

from ..core import config
from . import totp, vault


def secret_for(row: dict) -> str:
    if row["level"] == "founder" and config.FOUNDER_TOTP_SECRET:
        return config.FOUNDER_TOTP_SECRET
    return vault.unseal(row.get("totp_secret") or "")


def enrolled(row: dict) -> bool:
    return bool(secret_for(row))


def from_env(row: dict) -> bool:
    return row["level"] == "founder" and bool(config.FOUNDER_TOTP_SECRET)


def check(row: dict, code: str) -> bool:
    secret = secret_for(row)
    return bool(secret) and totp.verify(secret, code)
