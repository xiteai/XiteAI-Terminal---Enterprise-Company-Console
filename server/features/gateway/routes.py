"""POST /api/v1/ai/{provider}: XOS1 asks this server to make a model call.

The app signs the request with the same device key it checks in with, so the
envelope is the one already in contract/checkin.schema.json. What's different
is what's inside: a `request` object, passed to the provider as-is.

The key is read from the vault, used, and dropped. It is never in the
response, never in a log line, and never on the machine that asked.

Order of the guards, cheapest first, so a flood costs almost nothing:
  1. body size            — before reading it all
  2. signature            — pure CPU, no I/O
  3. replay               — in memory
  4. is the device known  — cached 60s
  5. per-device rate      — in memory
  6. only then, the provider call
"""
from __future__ import annotations

import json
import logging
import threading
import time

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ...core import config, db, vault
from ..ai_keys import service as keys
from ..checkin.routes import _product_id
from ..checkin.verify import CheckinError, verify
from . import devices, tokens

router = APIRouter(prefix="/api/v1/ai", tags=["gateway"])
log = logging.getLogger("terminal.gateway")


# ── One pooled HTTP client for every upstream call ───────────────────────────
# Async, because a blocking call inside an async handler stops the whole event
# loop: one slow model answer would freeze every other request on the server,
# including the console. Pooled, because opening a fresh TLS connection per
# request is most of the latency at any real volume.
_client: httpx.AsyncClient | None = None
_client_lock = threading.Lock()


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(config.GATEWAY_TIMEOUT_S, connect=10.0),
                    limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
                )
    return _client


# ── Replay: a signed request is good once ────────────────────────────────────
_seen_lock = threading.Lock()
_seen: dict[str, float] = {}
_swept = 0.0


def _replayed(nonce: str) -> bool:
    global _swept
    now = time.monotonic()
    with _seen_lock:
        if nonce in _seen:
            return True
        _seen[nonce] = now
        if now - _swept > 300:
            cutoff = now - config.CHECKIN_MAX_SKEW_MIN * 60 * 2
            for k, v in list(_seen.items()):
                if v < cutoff:
                    del _seen[k]
            _swept = now
    return False


# ── Rate: a fixed window per machine, in memory ──────────────────────────────
_rate_lock = threading.Lock()
_rate: dict[tuple[int, str], tuple[int, int]] = {}      # key -> (minute, count)


def _too_much(product_id: int, hardware_hash: str) -> bool:
    minute = int(time.time() // 60)
    key = (product_id, hardware_hash)
    with _rate_lock:
        window, count = _rate.get(key, (minute, 0))
        if window != minute:
            window, count = minute, 0
        count += 1
        _rate[key] = (window, count)
        if len(_rate) > 50_000:
            for k, (w, _) in list(_rate.items()):
                if w != minute:
                    del _rate[k]
    return count > config.GATEWAY_PER_MIN


@router.post("/token")
async def token(request: Request):
    """Trade a signed envelope for a short-lived bearer token.

    The envelope is the same one check-in uses, so the app needs no second
    identity. The token that comes back lasts minutes and is bound to this
    machine — it is meant to be held in memory and thrown away, never written
    to disk."""
    raw = await request.body()
    if len(raw) > 8 * 1024:
        raise HTTPException(413, "Too large.")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    try:
        payload, pk_b64 = verify(body)
    except CheckinError as e:
        raise HTTPException(e.status, e.message)
    if _replayed(str(payload["nonce"])):
        raise HTTPException(409, "That request was already used.")
    product_id = _product_id(str(payload.get("product") or "xos1"))
    if product_id is None:
        raise HTTPException(400, "unknown product")
    if not devices.known(product_id, payload["hardware_hash"], pk_b64):
        raise HTTPException(403, "This machine isn't registered. Check in first.")
    if _too_much(product_id, payload["hardware_hash"]):
        raise HTTPException(429, "Slow down.", headers={"Retry-After": "60"})
    value, ttl = tokens.issue(product_id, payload["hardware_hash"])
    return {"token": value, "expires_in": ttl}


def _from_bearer(authorization: str | None) -> tuple[int, str]:
    """The device behind a bearer token, re-checked against the install list
    so a deactivated machine stops working without waiting for expiry."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing token.")
    try:
        product_id, hardware_hash = tokens.read(authorization[7:].strip())
    except tokens.TokenError as e:
        raise HTTPException(401, str(e))
    if not devices.exists(product_id, hardware_hash):
        raise HTTPException(403, "This machine isn't registered.")
    if _too_much(product_id, hardware_hash):
        raise HTTPException(429, "Slow down.", headers={"Retry-After": "60"})
    return product_id, hardware_hash


@router.post("/{prov}/chat/completions")
async def chat_completions(prov: str, request: Request, authorization: str | None = Header(default=None)):
    """OpenAI-shaped, so XOS1 can point the `openai` SDK straight at it:

        OpenAI(base_url="https://xtec.xiteai.com/api/v1/ai/deepinfra",
               api_key=<device token>)

    Streaming is passed straight through, chunk for chunk, so time-to-first-
    token is the provider's and not ours."""
    p = keys.provider(prov)
    _from_bearer(authorization)
    raw = await request.body()
    if len(raw) > config.GATEWAY_MAX_BODY_KB * 1024:
        raise HTTPException(413, "Too large.")
    try:
        ask = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    if not isinstance(ask, dict) or not ask.get("messages"):
        raise HTTPException(400, "messages is required.")

    with db.connect() as conn:
        try:
            key = keys.live_key(conn, prov)
        except vault.VaultError as e:
            log.error("gateway: %s", e)
            raise HTTPException(503, "The server can't open its copy of that key.")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "User-Agent": "xiteai-terminal-gateway"}

    if not ask.get("stream"):
        try:
            r = await _http().post(p["chat_url"], json=ask, headers=headers)
        except httpx.TimeoutException:
            raise HTTPException(504, f"Couldn't reach {p['label']} in time.")
        except httpx.HTTPError:
            raise HTTPException(502, f"Couldn't reach {p['label']}.")
        if r.status_code >= 400:
            raise _provider_error(p, r.status_code, r.text)
        return JSONResponse(r.json())

    async def relay():
        # Straight through, chunk for chunk: the point of streaming is that the
        # first token arrives as early as it would have without us in the path.
        try:
            async with _http().stream("POST", p["chat_url"], json=ask, headers=headers) as upstream:
                if upstream.status_code >= 400:
                    body = (await upstream.aread())[:400].decode("utf-8", "replace")
                    log.warning("gateway: %s answered %s", p["label"], upstream.status_code)
                    yield b"data: " + json.dumps(
                        {"error": {"message": f"{p['label']} answered {upstream.status_code}. {body}"}}
                    ).encode() + b"\n\n"
                    return
                async for chunk in upstream.aiter_raw():
                    yield chunk
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            log.warning("gateway: stream from %s failed (%s)", p["label"], type(e).__name__)
            yield b"data: " + json.dumps(
                {"error": {"message": f"Lost the connection to {p['label']}."}}).encode() + b"\n\n"

    return StreamingResponse(relay(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


def _provider_error(p: dict, status: int, detail: str) -> HTTPException:
    log.warning("gateway: %s answered %s", p["label"], status)     # the key is never in this line
    if status >= 500:
        return HTTPException(502, f"{p['label']} is having trouble. Try again shortly.")
    return HTTPException(400, f"{p['label']} answered {status}. {(detail or '')[:400]}")


@router.post("/{prov}")
async def call(prov: str, request: Request):
    p = keys.provider(prov)
    raw = await request.body()
    if len(raw) > config.GATEWAY_MAX_BODY_KB * 1024:
        raise HTTPException(413, "Too large.")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    try:
        payload, pk_b64 = verify(body)
    except CheckinError as e:
        raise HTTPException(e.status, e.message)

    if _replayed(str(payload["nonce"])):
        raise HTTPException(409, "That request was already used.")
    product_id = _product_id(str(payload.get("product") or "xos1"))
    if product_id is None:
        raise HTTPException(400, "unknown product")
    if not devices.known(product_id, payload["hardware_hash"], pk_b64):
        raise HTTPException(403, "This machine isn't registered. Check in first.")
    if _too_much(product_id, payload["hardware_hash"]):
        raise HTTPException(429, "Slow down.", headers={"Retry-After": "60"})

    ask = payload.get("request")
    if not isinstance(ask, dict) or not ask.get("messages"):
        raise HTTPException(400, "request must be an object with messages.")
    if ask.get("stream"):
        raise HTTPException(400, "Streaming isn't supported through the gateway yet.")

    with db.connect() as conn:
        try:
            key = keys.live_key(conn, prov)
        except vault.VaultError as e:
            log.error("gateway: %s", e)
            raise HTTPException(503, "The server can't open its copy of that key.")

    try:
        r = await _http().post(p["chat_url"], json=ask,
                               headers={"Authorization": f"Bearer {key}",
                                        "Content-Type": "application/json",
                                        "User-Agent": "xiteai-terminal-gateway"})
    except httpx.TimeoutException:
        raise HTTPException(504, f"Couldn't reach {p['label']} in time.")
    except httpx.HTTPError:
        raise HTTPException(502, f"Couldn't reach {p['label']}.")
    if r.status_code >= 400:
        raise _provider_error(p, r.status_code, r.text)
    return JSONResponse(r.json())
