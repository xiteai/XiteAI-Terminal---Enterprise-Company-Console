"""Every collection's indexes, created (or brought up to date) on start.

Each document keeps an explicit `id` field carrying whatever used to be the
SQL primary key (an integer from `db.next_id()`, or a natural key like an
email or a token hash) — `_id` is ALWAYS set to that same value too, so Mongo
enforces uniqueness on it for free, and `db.strip()` drops `_id` on the way
out so every document still looks exactly like the SQLite row it replaces.
A composite SQL primary key (e.g. `(change_id, path)`) becomes one string
`_id`, built the same way everywhere a lookup needs it — see each collection's
service module for its `_key()` helper.
"""
from __future__ import annotations

from pymongo import ASCENDING
from pymongo.errors import OperationFailure

from . import db


def _ensure(coll, keys, **kw) -> None:
    """create_index, but tolerant of an existing index under the same keys
    with different options (Atlas keeps the old one rather than erroring if we
    let it collide) — drop and recreate only when that actually happens."""
    try:
        coll.create_index(keys, **kw)
    except OperationFailure:
        name = kw.get("name")
        if name:
            coll.drop_index(name)
            coll.create_index(keys, **kw)
        else:
            raise


def init() -> None:
    with db.connect() as conn:
        # ── People ──────────────────────────────────────────────────────────
        _ensure(conn["staff"], [("email", ASCENDING)], unique=True, collation=db.CASE_INSENSITIVE, name="uq_email")
        _ensure(conn["staff"], [("status", ASCENDING), ("level", ASCENDING)], name="ix_status_level")

        _ensure(conn["login_attempts"], [("at", ASCENDING)], name="ix_at")

        _ensure(conn["notifications"], [("staff_id", ASCENDING), ("created_at", ASCENDING)], name="ix_staff_created")

        # ── Products ────────────────────────────────────────────────────────
        _ensure(conn["products"], [("slug", ASCENDING)], unique=True, name="uq_slug")

        # ── Installs ────────────────────────────────────────────────────────
        _ensure(conn["installs"], [("code", ASCENDING)], unique=True, name="uq_code")
        _ensure(conn["installs"], [("product_id", ASCENDING), ("hardware_hash", ASCENDING)], unique=True,
               name="uq_product_hw")
        _ensure(conn["installs"], [("last_seen", ASCENDING)], name="ix_last_seen")
        _ensure(conn["installs"], [("product_id", ASCENDING), ("last_seen", ASCENDING)], name="ix_product_last_seen")

        _ensure(conn["checkins"], [("at", ASCENDING)], name="ix_at")
        _ensure(conn["checkins"], [("install_id", ASCENDING), ("at", ASCENDING)], name="ix_install_at")

        # ── Customer requests ───────────────────────────────────────────────
        _ensure(conn["tickets"], [("ref", ASCENDING)], unique=True, name="uq_ref")
        _ensure(conn["tickets"], [("status", ASCENDING), ("updated_at", ASCENDING)], name="ix_status_updated")

        # ── AI keys ─────────────────────────────────────────────────────────
        _ensure(conn["ai_key_changes"], [("provider", ASCENDING), ("id", ASCENDING)], name="ix_provider_id")

        # ── Codebase ────────────────────────────────────────────────────────
        _ensure(conn["code_features"], [("repo_id", ASCENDING), ("name", ASCENDING)], unique=True, name="uq_repo_name")
        _ensure(conn["code_grants"], [("repo_id", ASCENDING), ("staff_id", ASCENDING)], name="ix_repo_staff")
        _ensure(conn["code_items"], [("repo_id", ASCENDING), ("path", ASCENDING)], name="ix_repo_path")
        _ensure(conn["code_changes"], [("repo_id", ASCENDING), ("status", ASCENDING), ("updated_at", ASCENDING)],
               name="ix_repo_status_updated")
        _ensure(conn["code_protected"], [("repo_id", ASCENDING), ("path", ASCENDING)], unique=True, name="uq_repo_path")
        _ensure(conn["code_checkpoints"], [("repo_id", ASCENDING), ("name", ASCENDING)], unique=True,
               name="uq_repo_name")
        _ensure(conn["code_comments"], [("change_id", ASCENDING)], name="ix_change")
        _ensure(conn["code_reads"], [("staff_id", ASCENDING), ("at", ASCENDING)], name="ix_staff_at")

        # ── The record ──────────────────────────────────────────────────────
        _ensure(conn["audit"], [("at", ASCENDING)], name="ix_at")
