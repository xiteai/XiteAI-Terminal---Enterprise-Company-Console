"""Small secrets the database has to hold (authenticator seeds), sealed with a
key that lives outside the database.

The key is TC_SECRET_KEY from .env if set (recommended on a server: then a
copied database file is useless on its own), otherwise data/secret.key,
created on first use and readable only by this user."""
from __future__ import annotations

import os
import stat

from cryptography.fernet import Fernet, InvalidToken

from ..core import config

_fernet: Fernet | None = None


def _key() -> bytes:
    env = os.getenv("TC_SECRET_KEY", "").strip()
    if env:
        return env.encode()
    path = config.DATA_DIR / "secret.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Fernet.generate_key())
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    return path.read_bytes().strip()


def _f() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_key())
    return _fernet


def seal(text: str) -> str:
    return _f().encrypt(text.encode("utf-8")).decode("ascii") if text else ""


def unseal(token: str) -> str:
    if not token:
        return ""
    try:
        return _f().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""
