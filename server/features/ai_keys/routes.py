from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core import audit, config, db, notify
from ...security import lockout, mfa, passwords
from ...web.deps import require, writable
from . import cloudflare, service

router = APIRouter(prefix="/api/ai-keys", tags=["ai-keys"])


class KeyBody(BaseModel):
    key: str = Field(max_length=500)
    password: str = Field(default="", max_length=200)
    code: str = Field(default="", max_length=12)


def _needs_code(a: dict) -> bool:
    return mfa.enrolled(a)


@router.get("")
def keys(a: dict = Depends(require("keys.view"))):
    with db.connect() as conn:
        return {"providers": service.listing(conn), "cloudflare": cloudflare.connected(),
                "can_replace": "keys.replace" in a["perms"] and not a["previewing"],
                "needs_code": _needs_code(a)}


@router.post("/{prov}/test")
def test_key(prov: str, body: KeyBody, a: dict = Depends(require("keys.replace"))):
    writable(a)
    p = service.provider(prov)
    ok, sentence = service.test(p, service.clean_key(body.key))
    return {"ok": ok, "message": sentence}


@router.post("/{prov}")
def replace(prov: str, body: KeyBody, a: dict = Depends(require("keys.replace"))):
    """Password (and the founder's authenticator code) again, then the provider
    must accept the key, then Cloudflare must take it. Any step failing means
    nothing changed for users."""
    writable(a)
    p = service.provider(prov)
    key = service.clean_key(body.key)
    gate = f"keys:{a['email']}"
    with db.connect() as conn:
        if lockout.locked(conn, gate, a["ip"]):
            raise HTTPException(429, f"Too many wrong passwords. Try again in {config.LOCKOUT_WINDOW_MIN} minutes.")
        if not passwords.verify_password(body.password, a["password_hash"]):
            lockout.record(conn, gate, a["ip"], False)
            audit.record(conn, a, "ai_key.denied", p["label"], "wrong password", a["ip"])
            raise HTTPException(400, "Your password isn't right.")
        if _needs_code(a) and not mfa.check(a, body.code):
            lockout.record(conn, gate, a["ip"], False)
            raise HTTPException(400, "That code didn't work. Codes change every 30 seconds.")
        lockout.record(conn, gate, a["ip"], True)
    if not cloudflare.connected():
        raise HTTPException(409, "Cloudflare isn't connected yet, so there's nowhere safe to put the key. "
                                 "You can still test it.")
    ok, sentence = service.test(p, key)
    if not ok:
        with db.connect() as conn:
            service.record(conn, prov, key, a, "refused", sentence)
            audit.record(conn, a, "ai_key.refused", p["label"], f"…{key[-4:]}: {sentence}", a["ip"])
        raise HTTPException(400, sentence + " Nothing changed for users.")
    service.push(p, key, a)
    with db.connect() as conn:
        service.record(conn, prov, key, a, "live", sentence)
        audit.record(conn, a, "ai_key.replaced", p["label"], f"now …{key[-4:]}", a["ip"])
        if a["level"] != "founder":
            founders = conn["staff"].distinct("id", {"level": "founder", "status": "active", "is_demo": False})
            notify.send(conn, founders, "ai_key", f"{a['display_name']} replaced the {p['label']} key",
                        f"Now ending …{key[-4:]}. Every XOS1 install uses it from now on.", "/console/keys")
        return {"ok": True, "message": f"Live. Every XOS1 install now uses the {p['label']} key ending …{key[-4:]}.",
                "providers": service.listing(conn)}
