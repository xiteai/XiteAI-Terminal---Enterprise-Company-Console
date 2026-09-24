"""Cloudflare Secrets Store, write side only.

The dashboard's token holds one permission, Secrets Store Write: it can put a
secret in and nothing else. It can't read a secret back and can't change the
Worker's code, so even a stolen dashboard can't redirect anyone's chats.
The Worker picks up a replaced value on its own; nothing is redeployed.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from ...core import config

API = "https://api.cloudflare.com/client/v4"


class CloudflareError(Exception):
    pass


def connected() -> bool:
    return bool(config.CF_ACCOUNT_ID and config.CF_API_TOKEN and config.CF_SECRETS_STORE_ID)


def _call(method: str, path: str, body=None) -> dict:
    url = f"{API}/accounts/{config.CF_ACCOUNT_ID}/secrets_store/stores/{config.CF_SECRETS_STORE_ID}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read() or b"{}")
        except ValueError:
            raise CloudflareError(f"Cloudflare answered {e.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise CloudflareError("Couldn't reach Cloudflare.") from None
    if not out.get("success"):
        errs = out.get("errors") or [{}]
        raise CloudflareError(errs[0].get("message") or "Cloudflare refused the change.")
    return out


def _find(name: str) -> str | None:
    out = _call("GET", "/secrets?" + urllib.parse.urlencode({"search": name, "per_page": 100}))
    for s in out.get("result") or []:
        if s.get("name") == name and s.get("status") != "deleted":
            return s["id"]
    return None


def put_secret(name: str, value: str, comment: str) -> None:
    """Create the secret, or replace its value if it exists."""
    sid = _find(name)
    if sid:
        _call("PATCH", f"/secrets/{sid}", {"value": value, "comment": comment, "scopes": ["workers"]})
    else:
        _call("POST", "/secrets", [{"name": name, "value": value, "comment": comment, "scopes": ["workers"]}])
