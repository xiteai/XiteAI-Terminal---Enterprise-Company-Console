"""The Workplace's records, in their own SQLite file.

Leave, expenses and asset requests are one table on purpose: they are the same
object — someone files it, someone senior decides it — and differ only in the
few columns each kind fills in. One table means one approval path, one history
and one place to be sure nothing decides itself twice.

Helpdesk tickets are not that shape (a conversation, assigned rather than
approved), so they keep their own table and their own notes.

People live in MongoDB; only their ids are here, the way the rest of the
console does it."""
from __future__ import annotations

from ...core import config, settings, sqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS work_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL CHECK (kind IN ('leave','expense','asset')),
    staff_id      INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','approved','declined','withdrawn')),
    title         TEXT NOT NULL,
    note          TEXT NOT NULL DEFAULT '',
    leave_type    TEXT NOT NULL DEFAULT '',      -- leave: annual | sick | casual | unpaid | maternity | …
    start_date    TEXT NOT NULL DEFAULT '',      -- leave: earliest picked day, YYYY-MM-DD
    end_date      TEXT NOT NULL DEFAULT '',      -- leave: latest picked day
    dates_json    TEXT NOT NULL DEFAULT '[]',    -- leave: every day picked, not just the span between them
    days          REAL NOT NULL DEFAULT 0,       -- half days are real, hence not an INTEGER
    category      TEXT NOT NULL DEFAULT '',      -- expense: travel, meals … | asset: laptop, monitor …
    amount_paise  INTEGER NOT NULL DEFAULT 0,    -- expense: money is counted, never floated
    spent_on      TEXT NOT NULL DEFAULT '',
    quantity      INTEGER NOT NULL DEFAULT 0,    -- asset
    asset_action  TEXT NOT NULL DEFAULT 'new'    -- asset: new | replacement
                  CHECK (asset_action IN ('new','replacement')),
    fine_paise    INTEGER NOT NULL DEFAULT 0,    -- asset: charged on a replacement for loss or damage
    created_at    TEXT NOT NULL,
    decided_by    INTEGER,
    decided_at    TEXT,
    decision_note TEXT NOT NULL DEFAULT '',
    is_demo       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_work_requests_mine ON work_requests(staff_id, kind, created_at);
CREATE INDEX IF NOT EXISTS ix_work_requests_open ON work_requests(status, kind, created_at);

CREATE TABLE IF NOT EXISTS work_holidays (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL UNIQUE,             -- YYYY-MM-DD
    label      TEXT NOT NULL,
    created_by INTEGER,
    is_demo    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_work_holidays_date ON work_holidays(date);

CREATE TABLE IF NOT EXISTS work_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ref         TEXT NOT NULL UNIQUE,            -- WT-0001, what people quote at each other
    staff_id    INTEGER NOT NULL,
    category    TEXT NOT NULL,                   -- laptop | access | software | network | other
    subject     TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','in_progress','resolved','closed')),
    priority    TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low','normal','high','urgent')),
    assignee_id INTEGER,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    is_demo     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_work_tickets_mine ON work_tickets(staff_id, updated_at);
CREATE INDEX IF NOT EXISTS ix_work_tickets_queue ON work_tickets(status, priority, updated_at);

CREATE TABLE IF NOT EXISTS work_ticket_notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES work_tickets(id) ON DELETE CASCADE,
    staff_id  INTEGER NOT NULL,
    body      TEXT NOT NULL,
    at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_work_ticket_notes ON work_ticket_notes(ticket_id, at);

CREATE TABLE IF NOT EXISTS work_payslips (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id         INTEGER NOT NULL,
    period           TEXT NOT NULL,              -- YYYY-MM, the month it pays for
    gross_paise      INTEGER NOT NULL,
    deductions_paise INTEGER NOT NULL DEFAULT 0,
    net_paise        INTEGER NOT NULL,
    issued_at        TEXT NOT NULL,
    is_demo          INTEGER NOT NULL DEFAULT 0,
    UNIQUE (staff_id, period)
);
CREATE INDEX IF NOT EXISTS ix_work_payslips ON work_payslips(staff_id, period);
"""

DB = sqlite.Store(lambda: config.WORKPLACE_DB_PATH, SCHEMA)
rows, one, scalar, run, many, tx = DB.rows, DB.one, DB.scalar, DB.run, DB.many, DB.tx


def demo_sql(conn, alias: str = "") -> str:
    """' AND is_demo = 0' while demo data is hidden (the switch lives in MongoDB), else ''."""
    return "" if settings.show_demo(conn) else f" AND {alias + '.' if alias else ''}is_demo = 0"


def forget_people(staff_ids: list[int]) -> None:
    """People deleted from MongoDB (only demo people ever are): what they filed
    goes with them, the way a foreign key would have taken it."""
    if not staff_ids:
        return
    marks = ",".join("?" * len(staff_ids))
    with tx() as t:
        t.run(f"DELETE FROM work_ticket_notes WHERE staff_id IN ({marks})", staff_ids)
        t.run(f"DELETE FROM work_ticket_notes WHERE ticket_id IN "
              f"(SELECT id FROM work_tickets WHERE staff_id IN ({marks}))", staff_ids)
        t.run(f"DELETE FROM work_tickets WHERE staff_id IN ({marks})", staff_ids)
        t.run(f"DELETE FROM work_requests WHERE staff_id IN ({marks})", staff_ids)
        t.run(f"DELETE FROM work_payslips WHERE staff_id IN ({marks})", staff_ids)
