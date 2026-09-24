"""MongoDB Atlas access: one shared pooled client, `connect()` hands back the
app's database (collections are `conn["staff"]`, `conn["sessions"]`, ...),
`tx()` for a real multi-document transaction, `next_id()` for integer ids that
behave exactly like SQLite's `INTEGER PRIMARY KEY` (so every place that
already treats an id as a plain int — URLs, foreign keys, comparisons — needs
no change), and the ISO-8601 UTC timestamp format every collection stores
(kept as plain strings, not BSON dates: sorts and compares identically to
before, and a document reads back exactly as it was written).

Inside `with db.tx(conn) as conn:`, every collection call `conn` gives out —
`conn["staff"].update_one(...)`, `.find(...)`, anything — automatically joins
that transaction. No call site anywhere ever passes `session=` itself: that
was tried and dropped, because it only takes one forgotten call, in one
helper, three layers down, to silently commit outside the transaction it was
supposed to be part of. `_TxDatabase`/`_TxCollection` below inject it instead,
so a transaction can't be joined incorrectly — the only way to be in one is
to be handed the proxy that `tx()` yields."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import quote_plus

from pymongo import MongoClient, ReturnDocument
from pymongo.client_session import ClientSession
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.database import Database

from . import config

CASE_INSENSITIVE = Collation(locale="en", strength=2)   # matches SQLite's COLLATE NOCASE; pass as collation=


def iso(dt: datetime) -> str:
    """UTC, second precision: the one format stored and compared everywhere."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def now_iso() -> str:
    return iso(datetime.now(timezone.utc))


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _client_uri() -> str:
    if config.MONGO_URI:                     # a full URI wins (tests point this at a local/throwaway server)
        return config.MONGO_URI
    if not (config.MONGO_CLUSTER and config.MONGO_DB_PASSWORD):
        raise RuntimeError("Set MONGO_CLUSTER and MONGO_DB_PASSWORD (or MONGO_URI) in .env before starting.")
    return f"mongodb+srv://xiteai-admin-db:{quote_plus(config.MONGO_DB_PASSWORD)}@{config.MONGO_CLUSTER}/?appName=Cluster0"


_client: MongoClient | None = None


def client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(_client_uri(), maxPoolSize=config.MONGO_POOL_SIZE, serverSelectionTimeoutMS=8000)
    return _client


@contextmanager
def connect():
    yield client()[config.MONGO_DB_NAME]


class _TxCollection:
    """A Collection that always hands its session along, on every call that
    accepts one — reads too, so a read inside a transaction sees that
    transaction's own not-yet-committed writes."""

    def __init__(self, coll: Collection, session: ClientSession):
        self._coll, self._session = coll, session

    def __getattr__(self, name):
        attr = getattr(self._coll, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            kwargs.setdefault("session", self._session)
            return attr(*args, **kwargs)
        return call


class _TxDatabase:
    """What `db.tx()` yields in place of the plain database: same `conn["x"]`
    interface, every collection it gives out is session-bound."""

    def __init__(self, database: Database, session: ClientSession):
        self._database, self._session = database, session

    def __getitem__(self, name: str) -> _TxCollection:
        return _TxCollection(self._database[name], self._session)

    def __getattr__(self, name):
        return getattr(self._database, name)


@contextmanager
def tx(conn: Database):
    """A real multi-document transaction (Atlas's replica set supports these,
    the shared free tier included).

        with db.tx(conn) as tconn:
            tconn["staff"].update_one(...)
            sessions.end_all(tconn, staff_id)   # sees the same transaction: pass `tconn`, not `conn`

    Always name it `tconn` (never `as conn`, shadowing the outer one): the
    session it holds is closed the moment the `with` block ends, so a `conn`
    rebound to it would look fine right up until the first call made with it
    AFTER the block — which raises, because that session has already ended.
    If a function needs to return something read after its writes, read it as
    the last line INSIDE the block, using `tconn`, and return that value —
    don't read again once the block (and its session) has closed."""
    with client().start_session() as session:
        with session.start_transaction():
            yield _TxDatabase(conn, session)


def next_id(conn, name: str) -> int:
    """The next integer id for `name` (a former table, now a collection),
    starting at 1: SQLite's `INTEGER PRIMARY KEY` behaviour."""
    doc = conn["counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return doc["seq"]


def next_ids(conn, name: str, count: int) -> range:
    """`count` fresh ids in one round trip, for a bulk insert — reserving them
    one at a time (`count` calls to `next_id`) is correct but needlessly slow
    against a remote database when seeding hundreds of documents."""
    if count <= 0:
        return range(0)
    doc = conn["counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": count}}, upsert=True, return_document=ReturnDocument.AFTER)
    return range(doc["seq"] - count + 1, doc["seq"] + 1)


def strip(doc: dict | None) -> dict | None:
    """Drop Mongo's own `_id` (every document keeps its real int `id` too)."""
    if doc is None:
        return None
    return {k: v for k, v in doc.items() if k != "_id"}
