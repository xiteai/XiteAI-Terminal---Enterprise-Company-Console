"""Reference sender for XOS1 V17 — drop this in, or port it.

The server already refuses a flood politely (503/429 with Retry-After). This
is the other half of the bargain: a client that never causes one.

Three rules, and the whole design follows from them:

  1. Never lose a check-in. It goes to a local spool file first, and is only
     deleted once the server has acknowledged it.
  2. Never send the spool all at once. After a week offline you have a week
     of check-ins; sending them together is exactly the stampede we're
     avoiding. Send at most MAX_PER_DRAIN, then stop until next wake.
  3. Never decide your own schedule. The server answers `next_after_s` —
     that's when to come back. It already contains a per-machine spread, so
     two million PCs don't wake at the same instant.

On a 429 or 503, back off exponentially with jitter, honour Retry-After when
it's given, and give up for this wake rather than retrying in a tight loop.

    sender = Sender(spool_path, sign=my_signer, public_key_b64=pk)
    sender.record(payload)        # queue one, returns immediately
    sender.drain()                # call on wake / when the network returns
"""
from __future__ import annotations

import json
import random
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ENDPOINT = "https://xtec.xiteai.com/api/v1/checkin"
MAX_PER_DRAIN = 5            # a week offline drains over several wakes, not in one burst
MAX_ATTEMPTS = 6             # then leave it spooled and try again next wake
MAX_SPOOL = 500              # oldest are dropped past this; a year of backlog helps nobody
BASE_BACKOFF_S = 2
MAX_BACKOFF_S = 300
TIMEOUT_S = 20

SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    body     TEXT NOT NULL,      -- the signed envelope, ready to post
    queued_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0
);
"""


class Sender:
    def __init__(self, spool: Path, sign: Callable[[bytes], str], public_key_b64: str, endpoint: str = ENDPOINT):
        self.endpoint = endpoint
        self.sign = sign                       # bytes -> base64 Ed25519 signature
        self.public_key = public_key_b64
        self.db = sqlite3.connect(str(spool), isolation_level=None)
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.executescript(SCHEMA)

    # ── queue ────────────────────────────────────────────────────────────────

    def record(self, payload: dict) -> None:
        """Sign and spool one check-in. Never blocks on the network."""
        import base64
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        envelope = {"payload": base64.b64encode(raw).decode(),
                    "signature": self.sign(raw),
                    "public_key": self.public_key}
        self.db.execute("INSERT INTO outbox (body, queued_at) VALUES (?,?)",
                        (json.dumps(envelope), time.time()))
        self.db.execute("DELETE FROM outbox WHERE id NOT IN "
                        "(SELECT id FROM outbox ORDER BY id DESC LIMIT ?)", (MAX_SPOOL,))

    # ── drain ────────────────────────────────────────────────────────────────

    def drain(self) -> int:
        """Send what's waiting, politely. Returns how many the server took.
        Stops at the first sign the server wants a rest."""
        sent = 0
        for row in self.db.execute(
                "SELECT id, body, attempts FROM outbox ORDER BY id LIMIT ?", (MAX_PER_DRAIN,)).fetchall():
            rid, body, attempts = row
            ok, retry_after, permanent = self._post(body)
            if ok:
                self.db.execute("DELETE FROM outbox WHERE id = ?", (rid,))
                sent += 1
                continue
            if permanent:
                # The server will never accept this one (malformed, too old).
                # Keeping it would block everything behind it forever.
                self.db.execute("DELETE FROM outbox WHERE id = ?", (rid,))
                continue
            self.db.execute("UPDATE outbox SET attempts = attempts + 1 WHERE id = ?", (rid,))
            if attempts + 1 >= MAX_ATTEMPTS:
                break                                  # leave it; try again next wake
            time.sleep(retry_after if retry_after else self._backoff(attempts))
            break                                      # the server is busy: stop this drain
        return sent

    @staticmethod
    def _backoff(attempts: int) -> float:
        """Exponential, with full jitter. The jitter is the point: without it
        every client that failed at the same moment retries at the same
        moment, which is the stampede again with extra steps."""
        ceiling = min(MAX_BACKOFF_S, BASE_BACKOFF_S * (2 ** attempts))
        return random.uniform(0, ceiling)

    def _post(self, body: str) -> tuple[bool, float | None, bool]:
        """(accepted, retry_after_seconds, permanently_refused)."""
        req = urllib.request.Request(self.endpoint, data=body.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "xos1"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                answer = json.loads(r.read() or b"{}")
                self.on_accepted(answer)
                return True, None, False
        except urllib.error.HTTPError as e:
            retry_after = _retry_after(e)
            if e.code in (429, 503):
                return False, retry_after, False       # busy: come back later
            if e.code in (400, 401, 409, 413):
                return False, None, True               # this one will never be accepted
            return False, retry_after, False           # 5xx: transient
        except (urllib.error.URLError, TimeoutError, OSError):
            return False, None, False                  # no network; try next wake

    # ── the server sets the schedule ─────────────────────────────────────────

    def on_accepted(self, answer: dict) -> None:
        """Override, or read `next_wake_at` after a drain. The server's
        `next_after_s` already includes this machine's own spread — do not add
        your own interval on top, and do not round it to the hour."""
        after = int(answer.get("next_after_s") or 6 * 3600)
        self.next_wake_at = time.time() + after


def _retry_after(e: urllib.error.HTTPError) -> float | None:
    raw = e.headers.get("Retry-After") if e.headers else None
    try:
        return max(0.0, float(raw)) if raw else None
    except (TypeError, ValueError):
        return None
