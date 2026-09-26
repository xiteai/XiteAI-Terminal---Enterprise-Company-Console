"""Check-ins, end to end through the HTTP API.

    python tests/test_checkin.py

A throwaway MongoDB database and a throwaway SQLite installs file, both
dropped when the run ends. No real install ever touches this."""
import base64
import hashlib
import json
import os
import secrets as secrets_mod
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

TMP = Path(tempfile.mkdtemp(prefix="tc-checkin-"))
PW = "Test-Founder-Pw-2026"
MONGO_DB_NAME = "xiteai_terminal_test_" + secrets_mod.token_hex(4)
os.environ.update({
    # MONGO_CLUSTER / MONGO_DB_PASSWORD load from the real .env (one Atlas cluster);
    # only the DATABASE NAME is swapped, to a throwaway one dropped when this run ends.
    "TC_MONGO_DB_NAME": MONGO_DB_NAME, "TC_DEMO_DATA": "false",
    "TC_CODE_DB_PATH": str(TMP / "codebase.db"), "TC_CODE_DIR": str(TMP / "code"),
    "TC_CODE_BACKUP_DIR": str(TMP / "backups"), "TC_CODE_SYNC_MIN": "0",
    "TC_INSTALLS_DB_PATH": str(TMP / "installs.db"),
    "TC_CHECKIN_MIN_INTERVAL_S": "2", "TC_CHECKIN_BATCH_MS": "40", "TC_CHECKIN_BATCH": "25",
    "FOUNDER_EMAIL": "boss", "FOUNDER_PASSWORD": PW, "FOUNDER_TOTP_SECRET": "",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402
from server.core import config, db  # noqa: E402
from server.features.checkin import batcher  # noqa: E402
from server.features.checkin.verify import CheckinError, verify  # noqa: E402
from server.features.installs import store as installs_store  # noqa: E402

H = {"X-TC": "1"}


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def login() -> TestClient:
    c = TestClient(app)
    c.__enter__()
    r = c.post("/api/auth/login", json={"email": "boss", "password": PW, "code": ""}, headers=H)
    assert r.status_code == 200, r.text
    return c


def machine(seed: str = "") -> dict:
    """A fresh simulated install: its own Ed25519 key and hardware hash."""
    key = Ed25519PrivateKey.generate()
    return {"key": key, "hardware_hash": hashlib.sha256((seed or secrets_mod.token_hex(8)).encode()).hexdigest(),
            "public_key": base64.b64encode(_raw_public(key)).decode()}


def checkin_body(m: dict, *, nonce: str = "", sent_at: str = "", **fields) -> dict:
    payload = {"v": 1, "hardware_hash": m["hardware_hash"], "sent_at": sent_at or db.now_iso(),
               "nonce": nonce or secrets_mod.token_hex(12), **fields}
    raw = json.dumps(payload).encode()
    sig = m["key"].sign(raw)
    return {"payload": base64.b64encode(raw).decode(), "signature": base64.b64encode(sig).decode(),
            "public_key": m["public_key"]}


class Checkin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = login()

    def post(self, m: dict, **kw):
        return self.c.post("/api/v1/checkin", json=checkin_body(m, **kw), headers=H)

    def ok(self, r, code=200):
        self.assertEqual(r.status_code, code, r.text)
        return r.json()

    def test_01_new_install_registers(self):
        m = machine("m1")
        out = self.ok(self.post(m, app_version="1.0.17", os_version="Windows 11 24H2"))
        self.assertTrue(out["ok"])
        self.assertRegex(out["code"], r"^[A-Z2-9]{4}-[A-Z2-9]{4}$")
        self.assertFalse(out["relinked"])
        row = installs_store.one("SELECT * FROM installs WHERE hardware_hash = ?", (m["hardware_hash"],))
        self.assertEqual(row["code"], out["code"])
        self.assertEqual(row["app_version"], "1.0.17")
        self.assertEqual(row["checkin_count"], 1)
        self.assertEqual(installs_store.scalar("SELECT COUNT(*) FROM checkins WHERE install_id = ?", (row["id"],)), 1)

    def test_02_second_checkin_same_key_updates_in_place(self):
        m = machine("m2")
        first = self.ok(self.post(m, app_version="1.0.16"))
        time.sleep(2.1)                                          # past TC_CHECKIN_MIN_INTERVAL_S
        second = self.ok(self.post(m, app_version="1.0.17"))
        self.assertEqual(first["code"], second["code"])
        self.assertFalse(second["relinked"])
        row = installs_store.one("SELECT * FROM installs WHERE hardware_hash = ?", (m["hardware_hash"],))
        self.assertEqual(row["app_version"], "1.0.17")
        self.assertEqual(row["checkin_count"], 2)

    def test_03_relink_on_a_new_key_is_recorded(self):
        m1 = machine("m3")
        first = self.ok(self.post(m1))
        m2 = dict(m1, key=Ed25519PrivateKey.generate())          # same machine, reinstalled: new key
        m2["public_key"] = base64.b64encode(_raw_public(m2["key"])).decode()
        time.sleep(2.1)
        second = self.ok(self.post(m2))
        self.assertEqual(first["code"], second["code"])
        self.assertTrue(second["relinked"])
        row = installs_store.one("SELECT * FROM installs WHERE hardware_hash = ?", (m1["hardware_hash"],))
        self.assertEqual(row["status"], "relinked")
        self.assertEqual(row["public_key"], m2["public_key"])
        hist = installs_store.rows("SELECT * FROM key_history WHERE install_id = ?", (row["id"],))
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["public_key"], m1["public_key"])
        # The audit write happens after the response is already on its way
        # back (the check-in itself never waits on it): give it a moment.
        for _ in range(50):
            with db.connect() as conn:
                if conn["audit"].find_one({"action": "install.relinked", "target": row["code"]}):
                    break
            time.sleep(0.1)
        else:
            self.fail("install.relinked was never recorded in the audit trail")

    def test_04_nonce_reuse_is_refused(self):
        m = machine("m4")
        nonce = secrets_mod.token_hex(12)
        self.ok(self.post(m, nonce=nonce))
        time.sleep(2.1)                                           # past TC_CHECKIN_MIN_INTERVAL_S: the rate
        self.ok(self.post(m, nonce=nonce), 409)                   # limiter must not be what refuses this one

    def test_05_bad_signature_is_refused(self):
        m = machine("m5")
        body = checkin_body(m)
        raw = bytearray(base64.b64decode(body["payload"]))
        raw[0] ^= 0xFF                                            # flip a bit: signature no longer matches
        body["payload"] = base64.b64encode(bytes(raw)).decode()
        r = self.c.post("/api/v1/checkin", json=body, headers=H)
        self.assertEqual(r.status_code, 401, r.text)

    def test_06_stale_timestamp_is_refused(self):
        m = machine("m6")
        old = (datetime.now(timezone.utc) - timedelta(minutes=config.CHECKIN_MAX_SKEW_MIN + 5)).isoformat()
        self.ok(self.post(m, sent_at=old), 400)

    def test_07_unknown_product_is_refused(self):
        m = machine("m7")
        self.ok(self.post(m, product="not-a-real-product"), 400)

    def test_08_malformed_hardware_hash_is_refused(self):
        m = machine("m8")
        m["hardware_hash"] = "not-64-hex-characters"
        self.ok(self.post(m), 400)

    def test_09_oversized_body_is_refused(self):
        r = self.c.post("/api/v1/checkin", content=b"x" * (33 * 1024),
                        headers={**H, "content-type": "application/json"})
        self.assertEqual(r.status_code, 413, r.text)

    def test_10_checking_in_too_often_is_rate_limited(self):
        m = machine("m10")
        self.ok(self.post(m))
        r = self.post(m)                                          # a fresh nonce, same machine, right away
        self.assertEqual(r.status_code, 429, r.text)
        self.assertIn("Retry-After", r.headers)

    def test_11_consent_withdrawn_clears_what_was_held(self):
        m = machine("m11")
        self.ok(self.post(m, consent={"profile": True, "usage": True},
                          profile={"name": "Priya Sharma", "dob": "1998-04-02"}, usage={"tools": ["chat"]}))
        row = installs_store.one("SELECT * FROM installs WHERE hardware_hash = ?", (m["hardware_hash"],))
        self.assertEqual(row["user_name"], "Priya Sharma")
        time.sleep(2.1)
        self.ok(self.post(m, consent={"profile": False, "usage": False}))
        row = installs_store.one("SELECT * FROM installs WHERE hardware_hash = ?", (m["hardware_hash"],))
        self.assertIsNone(row["user_name"])
        self.assertIsNone(row["user_dob"])
        self.assertEqual(row["consent_profile"], 0)

    def test_13_many_machines_at_once_all_land(self):
        """The batcher's whole reason to exist: a burst of installs checking in
        together becomes one (or a few) SQLite writes, not one per machine, and
        every one of them still gets back its own right answer."""
        machines = [machine(f"burst-{i}") for i in range(40)]
        before = installs_store.scalar("SELECT COUNT(*) FROM installs") or 0

        def send(m):
            return self.c.post("/api/v1/checkin", json=checkin_body(m), headers=H)

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(send, machines))
        for r in results:
            self.assertEqual(r.status_code, 200, r.text)
        codes = {r.json()["code"] for r in results}
        self.assertEqual(len(codes), len(machines))                # every machine got its own code
        after = installs_store.scalar("SELECT COUNT(*) FROM installs")
        self.assertEqual(after, before + len(machines))

    def test_14_queue_full_is_refused_before_touching_anything(self):
        old = config.CHECKIN_QUEUE_MAX
        config.CHECKIN_QUEUE_MAX = 0
        try:
            m = machine("m14")
            r = self.post(m)
            self.assertEqual(r.status_code, 503, r.text)
            self.assertIn("Retry-After", r.headers)
            self.assertIsNone(installs_store.one("SELECT 1 FROM installs WHERE hardware_hash = ?",
                                                 (m["hardware_hash"],)))
        finally:
            config.CHECKIN_QUEUE_MAX = old

    def test_15_a_bad_check_in_inside_a_batch_fails_alone(self):
        """One savepoint per check-in: a bad one in the middle of a batch
        doesn't take the good ones with it. Submitted straight to the batcher,
        below the HTTP layer's per-machine pacing guard — that guard is a
        separate concern from savepoint isolation inside one flush, and three
        requests from one machine in the same instant would trip it first."""
        with db.connect() as conn:
            pid = conn["products"].find_one({"slug": "xos1"}, {"id": 1})["id"]
        good_a, good_b = machine("m15a"), machine("m15b")
        shared_nonce = secrets_mod.token_hex(12)
        wire = [checkin_body(good_a), checkin_body(good_a, nonce=shared_nonce),
               checkin_body(good_a, nonce=shared_nonce), checkin_body(good_b)]
        futures = [batcher.submit(*verify(body), pid, "127.0.0.1") for body in wire]
        outcomes = []
        for f in futures:
            try:
                f.result(timeout=5)
                outcomes.append(200)
            except CheckinError as e:
                outcomes.append(e.status)
        self.assertEqual(sorted(outcomes), [200, 200, 200, 409])   # exactly one of the two same-nonce sends lost
        for hh in (good_a["hardware_hash"], good_b["hardware_hash"]):
            self.assertIsNotNone(installs_store.one("SELECT 1 FROM installs WHERE hardware_hash = ?", (hh,)))

    def test_16_erase_takes_checkins_and_key_history_with_it(self):
        m = machine("m16")
        code = self.ok(self.post(m))["code"]
        row = installs_store.one("SELECT id FROM installs WHERE code = ?", (code,))
        r = self.c.delete(f"/api/installs/{row['id']}", headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(installs_store.one("SELECT 1 FROM installs WHERE id = ?", (row["id"],)))
        self.assertEqual(installs_store.scalar("SELECT COUNT(*) FROM checkins WHERE install_id = ?", (row["id"],)), 0)

    def test_17_listing_and_detail_see_it(self):
        m = machine("m17")
        code = self.ok(self.post(m, app_version="1.0.17"))["code"]
        found = self.c.get("/api/installs", params={"q": code}, headers=H).json()
        self.assertEqual(found["total"], 1)
        self.assertEqual(found["items"][0]["code"], code)
        iid = installs_store.one("SELECT id FROM installs WHERE code = ?", (code,))["id"]
        detail = self.c.get(f"/api/installs/{iid}", headers=H).json()
        self.assertEqual(detail["install"]["code"], code)
        self.assertEqual(len(detail["recent"]), 1)

    def test_18_overview_counts_it(self):
        before = self.c.get("/api/overview", params={"product": "xos1", "range": 7}, headers=H).json()
        m = machine("m18")
        self.ok(self.post(m))
        after = self.c.get("/api/overview", params={"product": "xos1", "range": 7}, headers=H).json()
        self.assertEqual(after["kpis"]["total_installs"], before["kpis"]["total_installs"] + 1)


if __name__ == "__main__":
    assert config.MONGO_DB_NAME == MONGO_DB_NAME and MONGO_DB_NAME != "xiteai_terminal" and \
        config.INSTALLS_DB_PATH.is_relative_to(TMP) and config.CODE_DB_PATH.is_relative_to(TMP), \
        "refusing to run outside the sandbox"
    try:
        result = unittest.main(verbosity=2, exit=False).result
    finally:
        db.client().drop_database(MONGO_DB_NAME)
    sys.exit(0 if result.wasSuccessful() else 1)
