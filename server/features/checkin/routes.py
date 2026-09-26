"""POST /api/v1/checkin: verify the signature here (cheap, pure CPU, no
database touched yet), then hand the check-in to the batcher and wait for its
turn to be written. Two guards run before anything is queued: a machine
checking in faster than TC_CHECKIN_MIN_INTERVAL_S is told to slow down, and if
the queue is already at TC_CHECKIN_QUEUE_MAX the request is turned away
outright — both without touching the database."""
from __future__ import annotations

import asyncio
import json
import threading
import time

from fastapi import APIRouter, HTTPException, Request

from ...core import config, db
from ...web.deps import client_ip
from . import batcher
from .verify import CheckinError, verify

router = APIRouter(prefix="/api/v1", tags=["checkin"])

BUSY = "Busy right now. Try again shortly."


def _busy() -> HTTPException:
    # Headers go on the exception itself: a Response object mutated before
    # raising is discarded once an exception replaces the normal return path.
    return HTTPException(503, BUSY, headers={"Retry-After": "5"})


# Which product id a slug means: refreshed from MongoDB at most every 30
# seconds, so a check-in never waits on a database round trip to find out.
_products_lock = threading.Lock()
_products: dict[str, int] = {}
_products_at = 0.0


def _product_id(slug: str) -> int | None:
    global _products, _products_at
    now = time.monotonic()
    if now - _products_at > 30:
        with _products_lock:
            if now - _products_at > 30:               # still true after taking the lock
                with db.connect() as conn:
                    _products = {r["slug"]: r["id"] for r in conn["products"].find({}, {"slug": 1, "id": 1})}
                _products_at = time.monotonic()
    return _products.get(slug)


# One machine checking in far more often than it should: a client stuck
# looping, or a nonce script. Kept in memory only — a restart just means it
# forgets who checked in recently, not a security gap (a replayed nonce is
# still refused, only the pacing hint resets).
_seen_lock = threading.Lock()
_seen: dict[tuple[int, str], float] = {}
_seen_swept = 0.0


def _too_soon(product_id: int, hardware_hash: str) -> bool:
    global _seen_swept
    now = time.monotonic()
    key = (product_id, hardware_hash)
    with _seen_lock:
        last = _seen.get(key)
        if last is not None and now - last < config.CHECKIN_MIN_INTERVAL_S:
            return True
        _seen[key] = now
        if now - _seen_swept > 300:
            cutoff = now - config.CHECKIN_MIN_INTERVAL_S
            for k, v in list(_seen.items()):
                if v < cutoff:
                    del _seen[k]
            _seen_swept = now
    return False


@router.post("/checkin")
async def checkin(request: Request):
    if batcher.queue_depth() >= config.CHECKIN_QUEUE_MAX:
        raise _busy()
    raw = await request.body()
    if len(raw) > 32 * 1024:
        raise HTTPException(413, "Too large.")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    try:
        payload, pk_b64 = verify(body)
    except CheckinError as e:
        raise HTTPException(e.status, e.message)
    product_id = _product_id(str(payload.get("product") or "xos1"))
    if product_id is None:
        raise HTTPException(400, "unknown product")
    if _too_soon(product_id, payload["hardware_hash"]):
        raise HTTPException(429, "Checking in too often.", headers={"Retry-After": str(config.CHECKIN_MIN_INTERVAL_S)})
    try:
        fut = batcher.submit(payload, pk_b64, product_id, client_ip(request))
    except batcher.QueueFull:
        raise _busy()
    try:
        return await asyncio.wait_for(asyncio.wrap_future(fut), timeout=15)
    except asyncio.TimeoutError:
        raise _busy()
    except CheckinError as e:
        raise HTTPException(e.status, e.message)
