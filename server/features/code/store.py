"""The Codebase's own database: a local SQLite file, not MongoDB.

Everything else in the Terminal (people, sessions, the audit trail,
notifications) lives in MongoDB Atlas. The Codebase keeps its records here,
next to the repositories it describes, because:
  • one page of it asks dozens of small questions (which lines can this person
    see, who answers for this file); over the network each one is a round trip,
    locally it's a lookup;
  • a change request holds whole file texts, which have no business filling
    the Atlas quota;
  • grants, features, items and change requests are relational: deleting a
    feature must take its grants and items with it, and SQLite's foreign keys
    do that in one step (without them, a deleted feature's people kept access).

People are referred to by their id (staff_id, author_id, ...), a plain number
here; their names and levels are looked up in MongoDB when a page needs them.

Ids are AUTOINCREMENT: never handed out twice, even after a delete. Other
records point at them from outside this file (notifications link to change
#12, the audit trail names repository 6, "protected paths already set up" is
remembered per repository id), and a reused id would inherit all of that.

    store.rows(sql, args)  store.one(...)  store.scalar(...)  store.run(...)  store.many(...)
    with store.tx() as t:  t.run(...)  t.many(...)  # all or nothing
"""
from __future__ import annotations

from ...core import config, sqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS code_repos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    remote_url    TEXT NOT NULL,
    branch        TEXT NOT NULL DEFAULT 'main',
    status        TEXT NOT NULL DEFAULT 'cloning',   -- cloning | ready | failed
    status_detail TEXT NOT NULL DEFAULT '',
    head_sha      TEXT NOT NULL DEFAULT '',
    remote_sha    TEXT NOT NULL DEFAULT '',          -- GitHub's head at the last sync: the history guard's memory
    held_remote   TEXT NOT NULL DEFAULT '',          -- a rewritten GitHub head the guard refused to follow
    last_sync_at  TEXT,
    created_by    INTEGER,
    created_at    TEXT NOT NULL
);

-- A feature: a named bundle of code (folders, files, functions, lines) that
-- can be granted, and owned, as one.
CREATE TABLE IF NOT EXISTS code_features (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id     INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_by  INTEGER,
    created_at  TEXT NOT NULL,
    UNIQUE (repo_id, name)
);

-- A grant gives one person a feature, or its own list of items.
CREATE TABLE IF NOT EXISTS code_grants (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id    INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    staff_id   INTEGER NOT NULL,
    feature_id INTEGER REFERENCES code_features(id) ON DELETE CASCADE,
    can_edit   INTEGER NOT NULL DEFAULT 0,
    note       TEXT NOT NULL DEFAULT '',
    granted_by INTEGER,
    granted_at TEXT NOT NULL,
    expires_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_code_grants_staff ON code_grants(repo_id, staff_id);

-- What a feature or a grant covers. A symbol item finds its function or class
-- by name every time, so it follows the code; a lines item is moved along
-- whenever the file changes. `missing` = its code is gone.
CREATE TABLE IF NOT EXISTS code_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id    INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    feature_id INTEGER REFERENCES code_features(id) ON DELETE CASCADE,
    grant_id   INTEGER REFERENCES code_grants(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('folder','file','lines','symbol')),
    path       TEXT NOT NULL,                     -- '' with kind folder = everything
    line_start INTEGER,
    line_end   INTEGER,
    symbol     TEXT NOT NULL DEFAULT '',
    missing    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_code_items_path ON code_items(repo_id, path);
CREATE INDEX IF NOT EXISTS ix_code_items_grant ON code_items(grant_id);
CREATE INDEX IF NOT EXISTS ix_code_items_feature ON code_items(feature_id);

-- Who answers for a folder, file or feature: owners approve and merge,
-- reviewers approve.
CREATE TABLE IF NOT EXISTS code_owners (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id    INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    staff_id   INTEGER NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('owner','reviewer')),
    path       TEXT,                              -- folder or file; NULL when feature_id is set
    feature_id INTEGER REFERENCES code_features(id) ON DELETE CASCADE,
    added_by   INTEGER,
    added_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_code_owners ON code_owners(repo_id, staff_id);

CREATE TABLE IF NOT EXISTS code_changes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id        INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    author_id      INTEGER,
    title          TEXT NOT NULL,
    body           TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft','review','changes','merged','rejected','withdrawn','conflict')),
    need_approvals INTEGER NOT NULL DEFAULT 1,
    checks_json    TEXT NOT NULL DEFAULT '[]',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    files_at       TEXT NOT NULL,                 -- last edit to its files: approvals before this don't count
    submitted_at   TEXT,
    merged_by      INTEGER,
    merged_at      TEXT,
    merged_sha     TEXT NOT NULL DEFAULT '',
    github         TEXT NOT NULL DEFAULT '',      -- pushed | failed | local
    github_detail  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_code_changes ON code_changes(repo_id, status, updated_at);

CREATE TABLE IF NOT EXISTS code_change_files (
    change_id   INTEGER NOT NULL REFERENCES code_changes(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    base_sha    TEXT NOT NULL,
    old_text    TEXT,                             -- the file at base_sha; NULL = new file
    new_text    TEXT,                             -- NULL = the file is deleted
    author_view TEXT NOT NULL DEFAULT '',         -- JSON {old:[..], new:[..]} lines the author may see; '' = all
    PRIMARY KEY (change_id, path)
);

CREATE TABLE IF NOT EXISTS code_reviews (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id INTEGER NOT NULL REFERENCES code_changes(id) ON DELETE CASCADE,
    staff_id  INTEGER,
    verdict   TEXT NOT NULL CHECK (verdict IN ('approve','changes','comment','reject')),
    body      TEXT NOT NULL DEFAULT '',
    at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_code_reviews ON code_reviews(change_id);

-- Paths only the founder reads, grants and merges: the updater, signing,
-- build and release scripts, dependency lists. Folder grants, owners and
-- `code.read_all` stop at their edge.
CREATE TABLE IF NOT EXISTS code_protected (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id  INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    path     TEXT NOT NULL,
    added_by INTEGER,
    added_at TEXT NOT NULL,
    UNIQUE (repo_id, path)
);

-- Named points in the history ("Before the memory rewrite"): a git tag, pushed to GitHub too.
CREATE TABLE IF NOT EXISTS code_checkpoints (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id    INTEGER NOT NULL REFERENCES code_repos(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    sha        TEXT NOT NULL,
    note       TEXT NOT NULL DEFAULT '',
    created_by INTEGER,
    created_at TEXT NOT NULL,
    on_github  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (repo_id, name)
);

-- Comments on exact lines of a change under review.
CREATE TABLE IF NOT EXISTS code_comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id   INTEGER NOT NULL REFERENCES code_changes(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('new','old')),   -- a line of the changed file, or a removed one
    line        INTEGER NOT NULL,
    body        TEXT NOT NULL,
    staff_id    INTEGER,
    at          TEXT NOT NULL,
    resolved_by INTEGER,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_code_comments ON code_comments(change_id);

-- Every file opened and every search, kept two days: the reading alarm counts them.
CREATE TABLE IF NOT EXISTS code_reads (
    staff_id INTEGER NOT NULL,
    kind     TEXT NOT NULL,                      -- open | search
    path     TEXT NOT NULL DEFAULT '',
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_code_reads ON code_reads(staff_id, at);
"""


_DB = sqlite.Store(lambda: config.CODE_DB_PATH, SCHEMA)
rows, one, scalar, run, many, tx = _DB.rows, _DB.one, _DB.scalar, _DB.run, _DB.many, _DB.tx


def forget_people(staff_ids: list[int]) -> None:
    """People deleted from MongoDB (only demo people ever are): their grants
    and roles here go too, the way a foreign key would have taken them."""
    if not staff_ids:
        return
    marks = ",".join("?" * len(staff_ids))
    with tx() as t:
        t.run(f"DELETE FROM code_grants WHERE staff_id IN ({marks})", staff_ids)
        t.run(f"DELETE FROM code_owners WHERE staff_id IN ({marks})", staff_ids)