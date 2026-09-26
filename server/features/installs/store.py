"""Installs and their check-ins: a local SQLite file on the server, not MongoDB.

Each install is one row, updated in place on every check-in. What grows is
the history: one row per check-in per machine, which the activity chart, the
heatmap and each install's version history are drawn from. At ten thousand
PCs checking in hourly that's ~50 MB a day: Atlas's free 512 MB would be full
in a week and a half, the server's own disk holds years of it. It's also
written by one batching writer (features/checkin/batcher.py), and SQLite
takes a thousand check-ins in one transaction in milliseconds.

Deleting an install takes its check-ins and key history with it (foreign
keys), so "erase this install" really does erase every record of it.

Products are referred to by id; their names live in MongoDB."""
from __future__ import annotations

from ...core import config, settings, sqlite
from ..releases.loader import version_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS installs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    code            TEXT NOT NULL UNIQUE,              -- what the user reads out to support: ABCD-EF23
    hardware_hash   TEXT NOT NULL,                     -- sha256 of the machine id; the raw id never leaves the PC
    public_key      TEXT NOT NULL,
    key_fingerprint TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'verified',  -- verified | relinked (same machine, new key)
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    app_version     TEXT NOT NULL DEFAULT '',
    version_sort    TEXT NOT NULL DEFAULT '',          -- 1.0.17 -> 000001.000000.000017, so SQL sorts versions right
    os_version      TEXT NOT NULL DEFAULT '',
    device_type     TEXT NOT NULL DEFAULT '',
    region          TEXT NOT NULL DEFAULT '',
    timezone        TEXT NOT NULL DEFAULT '',
    locale          TEXT NOT NULL DEFAULT '',
    consent_profile INTEGER NOT NULL DEFAULT 0,
    consent_usage   INTEGER NOT NULL DEFAULT 0,
    user_name       TEXT,                              -- only with consent_profile; cleared when it's withdrawn
    user_dob        TEXT,
    update_state    TEXT NOT NULL DEFAULT 'ok',
    crash_count_7d  INTEGER NOT NULL DEFAULT 0,
    checkin_count   INTEGER NOT NULL DEFAULT 0,
    is_demo         INTEGER NOT NULL DEFAULT 0,
    UNIQUE (product_id, hardware_hash)
);
CREATE INDEX IF NOT EXISTS ix_installs_seen ON installs(product_id, last_seen);
CREATE INDEX IF NOT EXISTS ix_installs_first ON installs(product_id, first_seen);

CREATE TABLE IF NOT EXISTS checkins (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    install_id   INTEGER NOT NULL REFERENCES installs(id) ON DELETE CASCADE,
    at           TEXT NOT NULL,
    app_version  TEXT NOT NULL DEFAULT '',
    update_state TEXT NOT NULL DEFAULT 'ok',
    crash_count  INTEGER NOT NULL DEFAULT 0,
    tools_json   TEXT,                                 -- only with consent_usage
    is_demo      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_checkins_install ON checkins(install_id, at);
CREATE INDEX IF NOT EXISTS ix_checkins_at ON checkins(at);

-- A machine that came back with a different key: the old one, kept.
CREATE TABLE IF NOT EXISTS key_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    install_id  INTEGER NOT NULL REFERENCES installs(id) ON DELETE CASCADE,
    public_key  TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    replaced_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_key_history ON key_history(install_id);

-- Every check-in's nonce for a day: the same signed check-in can't be sent twice.
CREATE TABLE IF NOT EXISTS checkin_nonces (
    nonce TEXT PRIMARY KEY,
    at    TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_nonces_at ON checkin_nonces(at);

CREATE TABLE IF NOT EXISTS downloads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    at         TEXT NOT NULL,
    ip_hash    TEXT NOT NULL DEFAULT '',   -- sha256(ip + secret): counts people, never identifies one
    country    TEXT NOT NULL DEFAULT '',   -- from Cloudflare's header when it's there
    referer    TEXT NOT NULL DEFAULT '',
    is_demo    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_downloads_at ON downloads(product_id, at);
"""

DB = sqlite.Store(lambda: config.INSTALLS_DB_PATH, SCHEMA)
rows, one, scalar, run, many, tx = DB.rows, DB.one, DB.scalar, DB.run, DB.many, DB.tx


def version_sort(v: str) -> str:
    return ".".join(f"{n:06d}" for n in version_key(v)[:4]) if v else ""


def demo_sql(conn, alias: str = "") -> str:
    """' AND is_demo = 0' while demo data is hidden (settings live in MongoDB), else ''."""
    return "" if settings.show_demo(conn) else f" AND {alias + '.' if alias else ''}is_demo = 0"


def local_offset() -> str:
    """The display clock's offset as an SQLite date modifier: '+330 minutes' for IST."""
    from ...core import clock
    return f"{int(clock.OFFSET.total_seconds() // 60):+d} minutes"
