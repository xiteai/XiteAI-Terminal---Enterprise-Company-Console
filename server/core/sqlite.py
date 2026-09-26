"""The server's own local databases: SQLite files next to the app, for the
data that's big, busy or relational and has no reason to cross the network
(the Codebase's records, installs and their check-ins). Everything else is in
MongoDB Atlas (core/db.py).

    DB = sqlite.Store(lambda: config.SOME_PATH, SCHEMA)
    DB.rows(sql, args)  DB.one(...)  DB.scalar(...)  DB.run(...)  DB.many(...)
    with DB.tx() as t:  t.run(...)  t.many(...)      # all or nothing

A connection per call (cheap for a local file), WAL so readers never wait on a
writer, foreign keys on, rows as plain dicts. The schema is created the first
time a path is used."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable


def statements(schema: str) -> list[str]:
    """A schema split into whole statements (a comment may hold a ';')."""
    out, stmt = [], ""
    for line in schema.splitlines(keepends=True):
        stmt += line
        if sqlite3.complete_statement(stmt):
            out.append(stmt)
            stmt = ""
    return out


class Q:
    """One connection's worth of the helpers; `Store.tx()` hands out one of these."""

    def __init__(self, c: sqlite3.Connection):
        self.c = c

    def rows(self, sql: str, args=()) -> list[dict]:
        return [dict(r) for r in self.c.execute(sql, args)]

    def one(self, sql: str, args=()) -> dict | None:
        r = self.c.execute(sql, args).fetchone()
        return dict(r) if r else None

    def scalar(self, sql: str, args=()):
        r = self.c.execute(sql, args).fetchone()
        return r[0] if r else None

    def run(self, sql: str, args=()) -> sqlite3.Cursor:
        return self.c.execute(sql, args)

    def many(self, sql: str, seq) -> sqlite3.Cursor:
        return self.c.executemany(sql, seq)


class Store:
    def __init__(self, path: Callable[[], Path], schema: str):
        self._path, self._schema = path, schema
        self._ready: set[str] = set()
        self._lock = threading.Lock()

    def _open(self) -> sqlite3.Connection:
        path = self._path()
        key = str(path)
        if key not in self._ready:
            with self._lock:
                if key not in self._ready:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    c = sqlite3.connect(path, timeout=10, isolation_level=None)
                    try:
                        c.execute("PRAGMA journal_mode = WAL")    # background writers while pages read
                        c.executescript(self._schema)
                    finally:
                        c.close()
                    self._ready.add(key)
        c = sqlite3.connect(path, timeout=10, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA busy_timeout = 5000")
        c.execute("PRAGMA synchronous = NORMAL")     # safe with WAL: a power cut loses at most the last moment
        return c

    @contextmanager
    def _q(self):
        c = self._open()
        try:
            yield Q(c)
        finally:
            c.close()

    def rows(self, sql: str, args=()) -> list[dict]:
        with self._q() as q:
            return q.rows(sql, args)

    def one(self, sql: str, args=()) -> dict | None:
        with self._q() as q:
            return q.one(sql, args)

    def scalar(self, sql: str, args=()):
        with self._q() as q:
            return q.scalar(sql, args)

    def run(self, sql: str, args=()) -> sqlite3.Cursor:
        """A write. The cursor comes back already finished: read .lastrowid / .rowcount from it."""
        with self._q() as q:
            return q.run(sql, args)

    def many(self, sql: str, seq) -> sqlite3.Cursor:
        with self._q() as q:
            return q.many(sql, seq)

    @contextmanager
    def tx(self):
        """All or nothing: `with DB.tx() as t: t.run(...); t.many(...)`."""
        with self._q() as q:
            q.c.execute("BEGIN IMMEDIATE")
            try:
                yield q
                q.c.execute("COMMIT")
            except BaseException:
                q.c.execute("ROLLBACK")
                raise
