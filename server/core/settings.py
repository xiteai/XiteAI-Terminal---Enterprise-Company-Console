"""Company-wide switches the founder flips in the console, kept in the settings collection."""
from __future__ import annotations

from . import db


def get(conn, key: str, default: str = "") -> str:
    doc = conn["settings"].find_one({"_id": key})
    return default if doc is None else doc["value"]


def put(conn, key: str, value: str, by: int | None = None) -> None:
    conn["settings"].update_one({"_id": key}, {"$set": {"key": key, "value": value, "set_by": by,
                                                        "set_at": db.now_iso()}}, upsert=True)


# ── Demo data: a switch, not a deletion ───────────────────────────────────────
# With demo off, every query adds a `is_demo: False` filter: the demo rows
# stay in the database, so switching it back on is instant.

def show_demo(conn) -> bool:
    return get(conn, "show_demo", "1") == "1"


def demo_filter(conn) -> dict:
    """{} when demo is shown; {'is_demo': False} when it's hidden — merge into any filter dict."""
    return {} if show_demo(conn) else {"is_demo": False}
