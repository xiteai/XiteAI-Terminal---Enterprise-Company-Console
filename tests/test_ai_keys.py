"""AI keys page, end to end through the HTTP API, on a throwaway database.

    python tests/test_ai_keys.py

Accounts come from the environment set below, never from .env, and the
provider and Cloudflare calls are replaced with fakes: nothing leaves the PC.
"""
import os
import secrets
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = tempfile.mkdtemp(prefix="tc-keys-")
PW = "Test-Founder-Pw-2026"
MONGO_DB_NAME = "xiteai_terminal_test_" + secrets.token_hex(4)
os.environ.update({
    # MONGO_CLUSTER / MONGO_DB_PASSWORD are NOT set here: they load from the real
    # .env (config.py's own load_dotenv), because there's one Atlas cluster —
    # only the DATABASE NAME is swapped, to a throwaway one dropped when this run ends.
    "TC_MONGO_DB_NAME": MONGO_DB_NAME, "TC_DEMO_DATA": "false",
    "TC_CODE_DIR": str(Path(TMP) / "code"), "TC_CODE_BACKUP_DIR": str(Path(TMP) / "backups"), "TC_CODE_SYNC_MIN": "0",
    "FOUNDER_EMAIL": "boss", "FOUNDER_PASSWORD": PW, "FOUNDER_TOTP_SECRET": "",
    "SEED_STAFF": "vp:vee:Test-Vp-Pw-2026A:Vee Pee;employee:emma:Test-Emp-Pw-2026A:Em Ploy",
    "CF_ACCOUNT_ID": "", "CF_API_TOKEN": "", "CF_SECRETS_STORE_ID": "",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402
from server.core import config, db  # noqa: E402
from server.features.ai_keys import cloudflare, service  # noqa: E402

KEY = "sk-test-" + "Q" * 30 + "wxyz"
H = {"X-TC": "1"}


def client(email, pw):
    c = TestClient(app)
    c.__enter__()
    r = c.post("/api/auth/login", json={"email": email, "password": pw, "code": ""}, headers=H)
    assert r.status_code == 200, r.text
    return c


class AiKeys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boss = client("boss", PW)
        cls.vp = client("vee", "Test-Vp-Pw-2026A")
        cls.emp = client("emma", "Test-Emp-Pw-2026A")

    def test_1_listing_and_access(self):
        r = self.boss.get("/api/ai-keys")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual([p["key"] for p in d["providers"]], ["deepinfra", "baseten", "openai", "cerebras"])
        self.assertFalse(d["cloudflare"])
        self.assertTrue(d["can_replace"])
        self.assertTrue(self.vp.get("/api/ai-keys").json()["can_replace"] is False)   # view by default, no replace
        self.assertEqual(self.emp.get("/api/ai-keys").status_code, 403)

    def test_2_vp_cannot_replace(self):
        r = self.vp.post("/api/ai-keys/deepinfra", json={"key": KEY, "password": "Test-Vp-Pw-2026A"}, headers=H)
        self.assertEqual(r.status_code, 403)

    def test_3_bad_input(self):
        r = self.boss.post("/api/ai-keys/deepinfra/test", json={"key": "short"}, headers=H)
        self.assertEqual(r.status_code, 400)
        r = self.boss.post("/api/ai-keys/nope", json={"key": KEY, "password": PW}, headers=H)
        self.assertEqual(r.status_code, 404)

    def test_4_wrong_password_then_no_cloudflare(self):
        r = self.boss.post("/api/ai-keys/deepinfra", json={"key": KEY, "password": "wrong"}, headers=H)
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.json()["detail"])
        r = self.boss.post("/api/ai-keys/deepinfra", json={"key": KEY, "password": PW}, headers=H)
        self.assertEqual(r.status_code, 409)

    def test_5_refused_key_changes_nothing(self):
        with mock.patch.object(cloudflare, "connected", return_value=True), \
             mock.patch.object(service, "test", return_value=(False, "DeepInfra refused this key.")), \
             mock.patch.object(cloudflare, "put_secret") as put:
            r = self.boss.post("/api/ai-keys/deepinfra", json={"key": KEY, "password": PW}, headers=H)
        self.assertEqual(r.status_code, 400)
        put.assert_not_called()

    def test_6_replace_goes_live_and_stores_no_key(self):
        with mock.patch.object(cloudflare, "connected", return_value=True), \
             mock.patch.object(service, "test", return_value=(True, "DeepInfra accepted the key.")), \
             mock.patch.object(cloudflare, "put_secret") as put:
            r = self.boss.post("/api/ai-keys/deepinfra", json={"key": KEY, "password": PW}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        put.assert_called_once()
        self.assertEqual(put.call_args.args[:2], ("DEEPINFRA_API_KEY", KEY))
        cur = next(p for p in r.json()["providers"] if p["key"] == "deepinfra")["current"]
        self.assertEqual(cur["last4"], "wxyz")
        # The key must not be anywhere on disk: database, WAL, anything in the folder.
        for f in Path(TMP).iterdir():
            self.assertNotIn(KEY.encode(), f.read_bytes(), f.name)

    def test_7_cloudflare_failure_is_plain(self):
        with mock.patch.object(cloudflare, "connected", return_value=True), \
             mock.patch.object(service, "test", return_value=(True, "ok")), \
             mock.patch.object(cloudflare, "put_secret", side_effect=cloudflare.CloudflareError("Token expired.")):
            r = self.boss.post("/api/ai-keys/openai", json={"key": KEY, "password": PW}, headers=H)
        self.assertEqual(r.status_code, 502)
        self.assertIn("Nothing changed for users", r.json()["detail"])

    def test_8_real_provider_refuses_fake_key(self):
        ok, sentence = service.test(service.PROVIDERS["deepinfra"], KEY)
        self.assertFalse(ok)
        self.assertNotIn(KEY, sentence)

    def test_9_needs_console_header(self):
        r = self.boss.post("/api/ai-keys/deepinfra/test", json={"key": KEY})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    assert config.MONGO_DB_NAME == MONGO_DB_NAME and MONGO_DB_NAME != "xiteai_terminal", \
        "refusing to run against a real database"
    try:
        result = unittest.main(verbosity=2, exit=False).result
    finally:
        db.client().drop_database(MONGO_DB_NAME)
    sys.exit(0 if result.wasSuccessful() else 1)
