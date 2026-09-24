"""Password hashing (scrypt, standard library), strength rules, and readable
temporary passwords."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# N=2^15, r=8, p=1: 32 MiB and ~60 ms per check. Slow for a guesser, fine for a person.
_N, _R, _P = 2 ** 15, 8, 1
_MAXMEM = 64 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, maxmem=_MAXMEM, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, key_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        key = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_b64),
                             n=int(n), r=int(r), p=int(p), maxmem=_MAXMEM, dklen=32)
        return hmac.compare_digest(key, base64.b64decode(key_b64))
    except Exception:
        return False


# Verified against when an email doesn't exist, so a wrong email takes as long
# as a wrong password and the two can't be told apart by timing.
_DUMMY = hash_password(secrets.token_urlsafe(16))


def burn_time(password: str) -> None:
    verify_password(password, _DUMMY)


def unusable_hash() -> str:
    """For accounts that must never sign in (demo people)."""
    return "disabled$" + secrets.token_hex(16)


def problem(password: str) -> str | None:
    """Why a new password is too weak, or None."""
    if len(password) < 12:
        return "Use at least 12 characters."
    if password.lower() == password or password.upper() == password:
        return "Mix upper and lower case letters."
    if not any(c.isdigit() for c in password):
        return "Include at least one number."
    return None


def generate() -> str:
    """Four groups of four, no look-alike characters: Hk7m-2QpR-x9Tn-Vb4c."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    while True:
        pw = "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))
        if problem(pw) is None:
            return pw
