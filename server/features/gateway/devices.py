"""Is this a machine we know, and is it the same machine it was last time?

A check-in registers a hardware hash together with the public key that signed
it. The gateway will only work for a pair that already exists: a stranger
with a fresh keypair gets nothing, and a stolen hardware hash signed by a
different key gets nothing either.

Answers are cached briefly — a chat turn shouldn't wait on a lookup that
changes once a month."""
from __future__ import annotations

import threading
import time

from ..installs import store

_TTL_S = 60
_lock = threading.Lock()
_cache: dict[tuple[int, str], tuple[float, str | None]] = {}


def known(product_id: int, hardware_hash: str, public_key_b64: str) -> bool:
    now = time.monotonic()
    key = (product_id, hardware_hash)
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _TTL_S:
            return hit[1] == public_key_b64
    row = store.one("SELECT public_key FROM installs WHERE product_id = ? AND hardware_hash = ?",
                    (product_id, hardware_hash))
    found = row["public_key"] if row else None
    with _lock:
        _cache[key] = (now, found)
        if len(_cache) > 50_000:                  # a bound, not a policy: never grow without limit
            _cache.clear()
    return found == public_key_b64


def exists(product_id: int, hardware_hash: str) -> bool:
    """Is this machine still on the books? Used on the token path, where the
    signature has already been checked once and what matters now is that the
    install hasn't been removed since."""
    now = time.monotonic()
    key = (product_id, hardware_hash)
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _TTL_S:
            return hit[1] is not None
    row = store.one("SELECT public_key FROM installs WHERE product_id = ? AND hardware_hash = ?",
                    (product_id, hardware_hash))
    with _lock:
        _cache[key] = (now, row["public_key"] if row else None)
    return row is not None


def forget(product_id: int, hardware_hash: str) -> None:
    with _lock:
        _cache.pop((product_id, hardware_hash), None)
