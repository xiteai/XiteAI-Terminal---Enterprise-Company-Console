"""Release notes, read straight from the XOS1 repo's NON-SHIPPINGS/release_notes/*.json
(XOS1_RELEASE_NOTES_DIR in .env), so the customer page shows the same changelog
as the in-app update notice. Read on every call: a new file shows up without a restart."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ...core import config

_FILE = re.compile(r"^\d+\.\d+\.\d+\.json$")


def version_key(v: str) -> tuple:
    try:
        return tuple(int(p) for p in (v or "0").split("."))
    except ValueError:
        return (0,)


def blank(version: str) -> dict:
    return {"version": version, "headline": "", "notes": "", "sections": [], "data_safety": ""}


def load() -> list[dict]:
    out = []
    folder = Path(config.RELEASE_NOTES_DIR) if config.RELEASE_NOTES_DIR else None
    if folder and folder.is_dir():
        for f in folder.iterdir():
            if not _FILE.match(f.name):
                continue
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ch = doc.get("changelog") or {}
            out.append({
                "version": f.name[:-5],
                "headline": ch.get("headline") or "",
                "notes": doc.get("notes") or "",
                "sections": [{"title": s.get("title", ""), "items": list(s.get("items") or [])}
                             for s in ch.get("sections") or [] if isinstance(s, dict)],
                "data_safety": ch.get("data_safety") or "",
            })
    if not any(r["version"] == config.LATEST_VERSION for r in out):
        out.append(blank(config.LATEST_VERSION))
    out.sort(key=lambda r: version_key(r["version"]), reverse=True)
    return out


def latest() -> dict:
    return next((r for r in load() if r["version"] == config.LATEST_VERSION), blank(config.LATEST_VERSION))
