"""Replacing a provider's key: test it with the provider, send it to Cloudflare,
keep a record of who did it. The key itself is never written anywhere here:
not the database, not the audit trail, not a log line. The record keeps its
last four characters, which is enough to tell two keys apart."""
from __future__ import annotations

import urllib.error
import urllib.request

from fastapi import HTTPException

from ...core import db, vault
from . import cloudflare

# What XOS1 talks to. `secret` is the name the Worker reads; `models_url`
# answers 200 for a working key and 401/403 for a refused one (checked).
PROVIDERS = {
    "deepinfra": {"label": "DeepInfra", "secret": "DEEPINFRA_API_KEY", "role": "Main chat model and memory",
                  "models_url": "https://api.deepinfra.com/v1/openai/models",
                  "chat_url": "https://api.deepinfra.com/v1/openai/chat/completions"},
    "baseten": {"label": "Baseten", "secret": "BASETEN_API_KEY", "role": "Backup chat model",
                "models_url": "https://inference.baseten.co/v1/models",
                "chat_url": "https://inference.baseten.co/v1/chat/completions"},
    "openai": {"label": "OpenAI", "secret": "OPENAI_API_KEY", "role": "Memory, first fallback",
               "models_url": "https://api.openai.com/v1/models",
               "chat_url": "https://api.openai.com/v1/chat/completions"},
    "cerebras": {"label": "Cerebras", "secret": "CEREBRAS_API_KEY", "role": "Memory, second fallback",
                 "models_url": "https://api.cerebras.ai/v1/models",
                 "chat_url": "https://api.cerebras.ai/v1/chat/completions"},
}


def provider(key: str) -> dict:
    p = PROVIDERS.get(key)
    if not p:
        raise HTTPException(404, "No provider by that name.")
    return p


def clean_key(raw: str) -> str:
    key = (raw or "").strip()
    if len(key) < 16 or len(key) > 400 or any(c.isspace() for c in key):
        raise HTTPException(400, "That doesn't look like an API key. Paste the whole key, with no spaces.")
    return key


def test(p: dict, key: str) -> tuple[bool, str]:
    """(works, plain sentence). Never puts the key in the sentence."""
    req = urllib.request.Request(p["models_url"], headers={"Authorization": f"Bearer {key}",
                                                          "User-Agent": "xos1-terminal"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if 200 <= r.status < 300:
                return True, f"{p['label']} accepted the key."
            return False, f"{p['label']} answered {r.status}, so the key couldn't be confirmed."
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, f"{p['label']} refused this key."
        return False, f"{p['label']} answered {e.code}, so the key couldn't be confirmed. Try again shortly."
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, f"Couldn't reach {p['label']} to test the key. Try again shortly."


def record(conn, prov: str, key: str, actor: dict, outcome: str, detail: str) -> None:
    cid = db.next_id(conn, "ai_key_changes")
    conn["ai_key_changes"].insert_one({"_id": cid, "id": cid, "provider": prov, "last4": key[-4:],
                                       "changed_by": actor["id"], "changed_at": db.now_iso(), "outcome": outcome,
                                       "detail": detail[:300], "ip": actor["ip"]})


def listing(conn) -> list[dict]:
    out = []
    vaulted = stored_set(conn)
    for key, p in PROVIDERS.items():
        rows = [db.strip(r) for r in conn["ai_key_changes"].find({"provider": key}).sort("id", -1).limit(6)]
        names = {s["id"]: s["display_name"] for s in conn["staff"].find(
            {"id": {"$in": [r["changed_by"] for r in rows if r["changed_by"]]}}, {"id": 1, "display_name": 1})}
        for r in rows:
            r["display_name"] = names.get(r["changed_by"])
        live = next((r for r in rows if r["outcome"] == "live"), None)
        out.append({
            "key": key, "label": p["label"], "role": p["role"], "secret": p["secret"],
            "in_vault": key in vaulted,
            "current": live and {"last4": live["last4"], "by": live["display_name"] or "someone removed",
                                 "at": live["changed_at"]},
            "history": [{"last4": r["last4"], "by": r["display_name"] or "someone removed", "at": r["changed_at"],
                         "outcome": r["outcome"], "detail": r["detail"]} for r in rows],
        })
    return out


# ── The vault: the key lives here, so no device ever carries one ─────────────
# Cloudflare keeps its own copy for the Worker path; this copy is what the
# gateway uses when XOS1 asks this server to make a call on its behalf.

def store(conn, prov: str, key: str, actor: dict) -> None:
    conn["ai_secrets"].update_one({"_id": prov}, {"$set": {
        "_id": prov, "provider": prov, "secret": vault.seal(key), "last4": key[-4:],
        "updated_by": actor["id"], "updated_at": db.now_iso()}}, upsert=True)


def live_key(conn, prov: str) -> str:
    """The usable key, for the gateway only. Never returned to a device."""
    row = conn["ai_secrets"].find_one({"_id": prov})
    if not row:
        raise HTTPException(503, f"No {prov} key is set on the server yet.")
    return vault.open_(row["secret"])


def reveal(conn, prov: str, actor: dict) -> str:
    """The key in full, for a level allowed to see it. Every read is audited
    by the caller — this function only opens it."""
    row = conn["ai_secrets"].find_one({"_id": prov})
    if not row:
        raise HTTPException(404, "That key was set before the vault existed, or hasn't been set here yet. "
                                 "Replace it once and it becomes readable.")
    return vault.open_(row["secret"])


def stored_set(conn) -> set[str]:
    return {r["_id"] for r in conn["ai_secrets"].find({}, {"_id": 1})}


def push(p: dict, key: str, actor: dict) -> None:
    try:
        cloudflare.put_secret(p["secret"], key, f"Set by {actor["display_name"]} from XiteAI Terminal")
    except cloudflare.CloudflareError as e:
        raise HTTPException(502, f"The key works, but Cloudflare didn't take it: {e} Nothing changed for users.")
