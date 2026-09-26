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

import logging
import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import quote_plus

from pymongo import MongoClient, ReturnDocument, errors
from pymongo.client_session import ClientSession
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.database import Database

from . import config

log = logging.getLogger("terminal.db")

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


# ── finding the cluster, whatever the network's DNS is doing ─────────────────
#
# Reaching Atlas takes two kinds of lookup: the SRV record that lists the
# cluster's servers (dnspython), then each server's address (the operating
# system's getaddrinfo, i.e. the network's DNS). On this PC's Wi-Fi the ISP's
# DNS failed the second kind ("getaddrinfo failed") often enough to stop the
# server starting. So both go to config.MONGO_DNS first, fall back to the
# network's own DNS (for a network that blocks outside DNS), and every
# server's last good address is kept for when neither answers. Only the
# cluster's own host names are touched; TLS still checks the certificate
# against the real host name, so a wrong answer can't impersonate Atlas.

_system_getaddrinfo = socket.getaddrinfo
_resolver = None
_atlas_suffix = ""
_known: dict[str, tuple[float, list[str]]] = {}         # host -> (fresh until, addresses)
_known_lock = threading.Lock()


def _use_public_dns() -> None:
    global _resolver, _atlas_suffix
    if not config.MONGO_DNS:
        return
    import dns.exception
    import dns.resolver

    try:
        system = dns.resolver.Resolver()                 # the network's own DNS, as Windows has it
    except dns.exception.DNSException:
        system = None

    class Resolver(dns.resolver.Resolver):
        def resolve(self, *args, **kwargs):
            try:
                return super().resolve(*args, **kwargs)
            except (dns.exception.Timeout, dns.resolver.NoNameservers):
                if system is None:
                    raise
                return system.resolve(*args, **kwargs)

    r = Resolver(configure=False)
    r.nameservers = config.MONGO_DNS
    r.timeout, r.lifetime = 1.5, 4.0                     # measured ~130 ms when healthy
    dns.resolver.default_resolver = r                    # pymongo's SRV lookup asks this one
    _resolver = r
    if config.MONGO_CLUSTER and not config.MONGO_URI and "." in config.MONGO_CLUSTER:
        # cluster0.abcde.mongodb.net -> its servers are <name>.abcde.mongodb.net
        _atlas_suffix = "." + config.MONGO_CLUSTER.split(".", 1)[1].lower()
        socket.getaddrinfo = _getaddrinfo


def _atlas_addresses(host: str) -> list[str]:
    import dns.exception

    now = time.monotonic()
    with _known_lock:
        known = _known.get(host)
    if known and known[0] > now:
        return known[1]
    try:
        answer = _resolver.resolve(host, "A")
    except dns.exception.DNSException as e:
        if known:
            log.warning("couldn't look up %s (%s); using its last known address", host, type(e).__name__)
            return known[1]
        return []
    found = [r.address for r in answer]
    with _known_lock:
        _known[host] = (now + max(60, min(answer.rrset.ttl, 3600)), found)
    return found


def _getaddrinfo(host, port, *args, **kwargs):
    if isinstance(host, str) and _atlas_suffix and host.lower().endswith(_atlas_suffix):
        out = []
        for ip in _atlas_addresses(host):
            try:
                out += _system_getaddrinfo(ip, port, *args, **kwargs)   # an address already: no lookup
            except socket.gaierror:
                continue
        if out:
            return out
    return _system_getaddrinfo(host, port, *args, **kwargs)


_client_lock = threading.Lock()


def client() -> MongoClient:
    global _client
    if _client is None:
        with _client_lock:                            # two first requests at once must not build two pools
            if _client is None:
                _use_public_dns()
                # serverSelectionTimeoutMS 15 s: rides out an Atlas failover or
                # a slow lookup without hanging a request forever. minPoolSize
                # keeps a few connections open and ready, so a request doesn't
                # pay for a DNS lookup and a TLS handshake (seconds on a bad
                # network) before it can even ask its question.
                _client = MongoClient(_client_uri(), maxPoolSize=config.MONGO_POOL_SIZE,
                                      minPoolSize=min(4, config.MONGO_POOL_SIZE), serverSelectionTimeoutMS=15000,
                                      connectTimeoutMS=10000, retryReads=True, retryWrites=True)
    return _client


def wait_until_ready(max_wait_s: float = 600) -> None:
    """At start: keep asking until the database answers. A network that's
    still coming up (the laptop just woke, the Wi-Fi is reconnecting) or an
    Atlas failover is a reason to wait, not to crash. A wrong password isn't:
    that fails at once."""
    deadline = time.monotonic() + max_wait_s
    delay = 2.0
    while True:
        try:
            client().admin.command("ping")
            return
        except (errors.ConnectionFailure, errors.ConfigurationError) as e:
            if time.monotonic() + delay > deadline:
                raise
            log.warning("the database isn't reachable yet (%s); trying again in %.0f s", str(e)[:160], delay)
            time.sleep(delay)
            delay = min(delay * 2, 30)


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
