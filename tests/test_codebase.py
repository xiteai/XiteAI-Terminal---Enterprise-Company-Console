"""Codebase, end to end through the HTTP API.

    python tests/test_codebase.py

A throwaway database and a local bare git repository standing in for GitHub.
Accounts come from the environment set below, never from .env."""
import json
import os
import secrets as secrets_mod
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="tc-code-"))
PW = {"boss": "Test-Founder-Pw-2026", "vee": "Test-Vp-Pw-2026A", "dee": "Test-Dir-Pw-2026A", "max": "Test-Mgr-Pw-2026A",
      "emma": "Test-Emp-Pw-2026A", "ian": "Test-Int-Pw-2026A", "helen": "Test-Hr-Pw-2026A",
      "vic": "Test-Vp2-Pw-2026A", "nora": "Test-Emp2-Pw-2026A"}
NO_AUTHENTICATOR = {"nora"}                 # never sets one up: the codebase must stay shut to her
MONGO_DB_NAME = "xiteai_terminal_test_" + secrets_mod.token_hex(4)
os.environ.update({
    # MONGO_CLUSTER / MONGO_DB_PASSWORD load from the real .env (one Atlas cluster);
    # only the DATABASE NAME is swapped, to a throwaway one dropped when this run ends.
    "TC_MONGO_DB_NAME": MONGO_DB_NAME, "TC_DEMO_DATA": "false", "TC_CODE_DIR": str(TMP / "code"),
    "TC_CODE_BACKUP_DIR": str(TMP / "backups"),         # never the real data/backups
    "TC_CODE_DB_PATH": str(TMP / "codebase.db"),        # never the real data/codebase.db
    "TC_CODE_ALLOW_LOCAL": "true", "TC_CODE_SYNC_MIN": "0", "GITHUB_TOKEN": "",
    "TC_CODE_ALERT_FILES_HOUR": "6", "TC_CODE_PAUSE_FILES_HOUR": "9",
    "FOUNDER_EMAIL": "boss", "FOUNDER_PASSWORD": PW["boss"], "FOUNDER_TOTP_SECRET": "",
    "SEED_STAFF": ";".join(f"{lv}:{n}:{PW[n]}:{n.title()} Test" for lv, n in
                           [("vp", "vee"), ("director", "dee"), ("manager", "max"), ("employee", "emma"),
                            ("intern", "ian"), ("hr", "helen"), ("vp", "vic"), ("employee", "nora")]),
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402
from server.core import config, db  # noqa: E402
from server.security import totp  # noqa: E402

H = {"X-TC": "1"}
REMOTE = TMP / "remote.git"
WORK = TMP / "work"

ENGINE = """import os


def helper(x):
    return x + 1


class Engine:
    def __init__(self):
        self.secret_sauce = 42

    def run(self, x):
        y = helper(x)
        return y * 2

    def stop(self):
        return "stopped"
"""
PROMPT = "PROMPT = 'You are helpful.'\n"
APP = """import { useState } from "react";

export default function App() {
  const [n, setN] = useState(0);
  return <button onClick={() => setN(n + 1)}>{n}</button>;
}
"""
PROMPT_TXT = """You are the assistant.

THE RULES. Be kind.
Never lie.

THE TEST. Could this be said to a stranger?
Then leave it out.
"""
UPDATER = "def apply(update):\n    return verify(update)\n"


def git(*args, cwd=WORK):
    subprocess.run(["git", "-c", "user.name=Suraj", "-c", "user.email=s@x.com", "-c", "core.autocrlf=false", *args],
                   cwd=cwd, check=True, capture_output=True)


def write(rel, content, binary=False):
    p = WORK / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    (p.write_bytes if binary else lambda c: p.write_text(c, encoding="utf-8", newline="\n"))(content)


def remote_file(rel):
    return subprocess.run(["git", "show", f"main:{rel}"], cwd=REMOTE, capture_output=True, check=True).stdout.decode()


def setup_remote():
    subprocess.run(["git", "init", "--bare", "-b", "main", str(REMOTE)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(REMOTE), str(WORK)], check=True, capture_output=True)
    write("core/memory/engine.py", ENGINE)
    write("core/ai/prompt.py", PROMPT)
    write("web/app.jsx", APP)
    write("README.md", "# test\n")
    write("model.bin", b"\0\1\2" * 100, binary=True)
    write("prompts/main.txt", PROMPT_TXT)
    write("installer.iss", "[Setup]\nAppName=XOS1\n")                    # protected on connect
    write("core/system/update/apply.py", UPDATER)                         # protected on connect
    for i in range(1, 9):
        write(f"docs/page{i}.md", f"# Page {i}\n\nNothing to see.\n")
    git("add", "-A")
    git("commit", "-m", "seed")
    git("push", "origin", "HEAD:main")


def login(name, code=""):
    c = TestClient(app)
    c.__enter__()
    r = c.post("/api/auth/login", json={"email": name, "password": PW[name], "code": code}, headers=H)
    assert r.status_code == 200, r.text
    return c


def now_code(secret):
    return totp._code(secret, int(time.time()) // 30)


def enroll(c):
    """Set up an authenticator the way a person would; the session counts as signed in with one."""
    r = c.post("/api/account/authenticator/start", headers=H)
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    r = c.post("/api/account/authenticator/confirm", json={"code": now_code(secret)}, headers=H)
    assert r.status_code == 200, r.text
    return secret


class Codebase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_remote()
        cls.u = {n: login(n) for n in PW}
        cls.secrets = {n: enroll(c) for n, c in cls.u.items() if n not in NO_AUTHENTICATOR}
        with db.connect() as conn:
            ids = {r["email"].split("@")[0]: r["id"] for r in conn["staff"].find({}, {"id": 1, "email": 1})}
            conn["staff"].update_one({"_id": ids["max"]}, {"$set": {"reports_to": ids["dee"]}})
            conn["staff"].update_many({"_id": {"$in": [ids["emma"], ids["ian"]]}}, {"$set": {"reports_to": ids["max"]}})
        cls.ids = ids
        r = cls.u["boss"].post("/api/code/repos", json={"name": "XOS1", "url": str(REMOTE), "branch": "main"}, headers=H)
        assert r.status_code == 200, r.text
        cls.rid = r.json()["id"]
        for _ in range(100):
            st = cls.u["boss"].get("/api/code/repos").json()["items"][0]
            if st["status"] != "cloning":
                break
            time.sleep(0.1)
        assert st["status"] == "ready", st

    def api(self, who, method, path, body=None):
        c = self.u[who]
        url = f"/api/code/{self.rid}{path}"
        if method == "get":
            return c.get(url)
        if method == "delete":
            return c.delete(url, headers=H)
        return getattr(c, method)(url, json=body or {}, headers=H)

    def ok(self, r, code=200):
        self.assertEqual(r.status_code, code, r.text)
        return r.json()

    # ── 1. map and roles ─────────────────────────────────────────────────────
    def test_01_map_without_code(self):
        files = {f["p"]: f for f in self.ok(self.api("emma", "get", "/tree"))["files"]}
        self.assertEqual(set(files), {"core/memory/engine.py", "core/ai/prompt.py", "web/app.jsx", "README.md", "model.bin",
                                      "prompts/main.txt", "installer.iss", "core/system/update/apply.py"}
                         | {f"docs/page{i}.md" for i in range(1, 9)})
        self.assertTrue(all(f["a"] == "none" for f in files.values()))
        self.assertEqual({p for p, f in files.items() if f.get("k")}, {"installer.iss", "core/system/update/apply.py"})
        self.ok(self.api("emma", "get", "/file?path=core/ai/prompt.py"), 403)
        self.ok(self.api("helen", "get", "/tree"))            # HR sees nothing but may use the access page
        self.assertEqual(self.ok(self.api("helen", "get", "/tree"))["files"], [])

    def test_02_owners(self):
        self.ok(self.api("boss", "post", "/owners", {"staff_id": self.ids["dee"], "role": "owner", "path": "core/memory"}))
        self.ok(self.api("boss", "post", "/owners", {"staff_id": self.ids["max"], "role": "reviewer", "path": "core/memory"}))
        r = self.api("boss", "post", "/owners", {"staff_id": self.ids["emma"], "role": "owner", "path": "core"})
        self.ok(r, 400)                                         # an employee can't own code
        self.ok(self.api("emma", "post", "/owners", {"staff_id": self.ids["emma"], "role": "reviewer", "path": "web"}), 403)

    # ── 2. grants ────────────────────────────────────────────────────────────
    def test_03_reviewer_gives_read_to_team_only(self):
        body = {"staff_id": self.ids["emma"], "items": [{"kind": "symbol", "path": "core/memory/engine.py", "symbol": "Engine.run"}]}
        self.ok(self.api("max", "post", "/grants", body | {"can_edit": True}), 403)     # reviewers: read only
        self.ok(self.api("max", "post", "/grants", body))
        self.ok(self.api("max", "post", "/grants", {"staff_id": self.ids["emma"],
                                                    "items": [{"kind": "file", "path": "core/ai/prompt.py"}]}), 403)

    def test_04_owner_gives_edit(self):
        self.ok(self.api("dee", "post", "/grants", {"staff_id": self.ids["emma"], "can_edit": True,
                                                    "items": [{"kind": "symbol", "path": "core/memory/engine.py",
                                                               "symbol": "Engine.run"}]}))
        self.ok(self.api("dee", "post", "/grants", {"staff_id": self.ids["vee"],
                                                    "items": [{"kind": "file", "path": "core/memory/engine.py"}]}), 403)
        self.ok(self.api("dee", "post", "/grants", {"staff_id": self.ids["emma"],
                                                    "items": [{"kind": "symbol", "path": "core/memory/engine.py",
                                                               "symbol": "Nope.nothing"}]}), 400)

    def test_05_partial_file_view_leaks_nothing(self):
        f = self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"))
        self.assertEqual(f["access"], "partial")
        shown = [b for b in f["blocks"] if b["kind"] == "shown"]
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0]["lines"][0].strip(), "def run(self, x):")
        self.assertTrue(shown[0]["editable"])
        raw = json.dumps(f)
        self.assertNotIn("secret_sauce", raw)
        self.assertNotIn("stopped", raw)
        self.assertEqual(f["symbols"], [])                   # no structure beyond what's given

    # ── 3. a change, reviewed and merged ─────────────────────────────────────
    def test_06_change_flow(self):
        f = self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"))
        seg = next(b for b in f["blocks"] if b["kind"] == "shown")
        c = self.ok(self.api("emma", "post", "/changes", {"title": "Run doubles then adds one", "body": "Tiny fix."}))
        cid = c["id"]
        outside = {"path": "core/memory/engine.py", "mode": "segments", "base_sha": f["head"],
                   "segments": [{"start": 1, "end": 1, "text": "import sys"}]}
        self.ok(self.api("emma", "put", f"/changes/{cid}/files", outside), 403)
        self.ok(self.api("emma", "put", f"/changes/{cid}/files", {"path": "core/memory/engine.py", "mode": "full",
                                                                   "text": "x = 1\n", "base_sha": f["head"]}), 403)
        new = "    def run(self, x):\n        y = helper(x)\n        return y * 2 + 1"
        d = self.ok(self.api("emma", "put", f"/changes/{cid}/files", {
            "path": "core/memory/engine.py", "mode": "segments", "base_sha": f["head"],
            "segments": [{"start": seg["start"], "end": seg["end"], "text": new}]}))
        rows = [r for h in d["file_list"][0]["hunks"] for r in h]
        self.assertTrue(any(r["t"] == "hidden" for r in rows))
        self.assertNotIn("secret_sauce", json.dumps(d))       # the author's diff hides what they can't see
        d = self.ok(self.api("emma", "post", f"/changes/{cid}/submit"))
        self.assertEqual(d["status"], "review")
        # The owner sees the whole file in the diff.
        full = self.ok(self.api("dee", "get", f"/changes/{cid}"))
        self.assertFalse(any(r["t"] == "hidden" for h in full["file_list"][0]["hunks"] for r in h))
        self.ok(self.api("emma", "post", f"/changes/{cid}/review", {"verdict": "approve"}), 403)   # not your own
        self.ok(self.api("max", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        self.ok(self.api("max", "post", f"/changes/{cid}/merge"), 409)                            # reviewers don't merge
        d = self.ok(self.api("dee", "post", f"/changes/{cid}/merge"))
        self.assertEqual(d["status"], "merged")
        self.assertEqual(d["github"], "pushed")
        self.assertIn("return y * 2 + 1", remote_file("core/memory/engine.py"))
        self.assertIn("secret_sauce", remote_file("core/memory/engine.py"))    # the rest untouched
        author = subprocess.run(["git", "log", "-1", "--format=%an|%ae|%cn", "main"], cwd=REMOTE,
                                capture_output=True, text=True).stdout.strip()
        self.assertEqual(author, "Emma Test|emma@xos1.com|XiteAI Terminal")

    # ── 4. code moves on GitHub; grants follow ───────────────────────────────
    def test_07_grants_follow_the_code(self):
        self.ok(self.api("dee", "post", "/grants", {"staff_id": self.ids["ian"], "items": [
            {"kind": "lines", "path": "core/memory/engine.py", "line_start": 4, "line_end": 5}]}))
        git("pull", "-q", "origin", "main")
        write("core/memory/engine.py", "# a\n# b\n# c\n" + remote_file("core/memory/engine.py"))
        git("commit", "-qam", "comments on top")
        git("push", "-q", "origin", "HEAD:main")
        self.ok(self.u["boss"].post(f"/api/code/repos/{self.rid}/sync", json={}, headers=H))
        f = self.ok(self.api("ian", "get", "/file?path=core/memory/engine.py"))
        shown = next(b for b in f["blocks"] if b["kind"] == "shown")
        self.assertEqual((shown["start"], shown["end"]), (7, 8))
        self.assertEqual(shown["lines"][0], "def helper(x):")
        f = self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"))
        self.assertEqual(next(b for b in f["blocks"] if b["kind"] == "shown")["lines"][0].strip(), "def run(self, x):")

    # ── 5. safety ────────────────────────────────────────────────────────────
    def test_08_secrets_and_syntax_are_refused(self):
        f = self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"))
        seg = next(b for b in f["blocks"] if b["kind"] == "shown")
        for bad, why in (("    def run(self, x):\n        key = 'sk-" + "a" * 30 + "'\n        return 1", "No secrets"),
                         ("    def run(self, x)\n        return 1", "Python syntax")):
            cid = self.ok(self.api("emma", "post", "/changes", {"title": "Bad one"}))["id"]
            self.ok(self.api("emma", "put", f"/changes/{cid}/files", {"path": "core/memory/engine.py", "mode": "segments",
                                                                       "base_sha": f["head"], "segments": [{"start": seg["start"], "end": seg["end"], "text": bad}]}))
            r = self.ok(self.api("emma", "post", f"/changes/{cid}/submit"), 400)
            self.assertIn(why, r["detail"])
            self.ok(self.api("emma", "post", f"/changes/{cid}/withdraw"))

    def test_09_heavy_things_are_refused(self):
        cid = self.ok(self.api("boss", "post", "/changes", {"title": "Add a model"}))["id"]
        self.ok(self.api("boss", "put", f"/changes/{cid}/files", {"path": "core/models/x.gguf", "mode": "new", "text": "x"}), 415)
        self.ok(self.api("boss", "get", "/file?path=model.bin"), 415)
        big = "x" * (config.CODE_MAX_FILE_KB * 1024 + 10)
        self.ok(self.api("boss", "put", f"/changes/{cid}/files", {"path": "core/big.py", "mode": "new", "text": big}), 413)
        r = self.u["boss"].put(f"/api/code/{self.rid}/changes/{cid}/files", content=b"{" + b" " * (3 * 1024 * 1024) + b"}",
                               headers=H | {"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_10_intern_needs_two_approvals(self):
        self.ok(self.api("dee", "post", "/grants", {"staff_id": self.ids["ian"], "can_edit": True, "items": [
            {"kind": "symbol", "path": "core/memory/engine.py", "symbol": "Engine.stop"}]}))
        f = self.ok(self.api("ian", "get", "/file?path=core/memory/engine.py"))
        seg = next(b for b in f["blocks"] if b["kind"] == "shown" and b["editable"])
        cid = self.ok(self.api("ian", "post", "/changes", {"title": "Stop says bye"}))["id"]
        self.ok(self.api("ian", "put", f"/changes/{cid}/files", {"path": "core/memory/engine.py", "mode": "segments",
                                                                  "base_sha": f["head"], "segments": [{"start": seg["start"], "end": seg["end"],
                                                                                                       "text": "    def stop(self):\n        return 'bye'"}]}))
        self.ok(self.api("ian", "post", f"/changes/{cid}/submit"))
        self.ok(self.api("max", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        d = self.ok(self.api("dee", "get", f"/changes/{cid}"))
        self.assertFalse(d["can"]["merge"])
        self.assertIn("2 approvals", d["can"]["merge_why"])
        self.ok(self.api("dee", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        self.assertEqual(self.ok(self.api("dee", "post", f"/changes/{cid}/merge"))["status"], "merged")
        self.assertIn("return 'bye'", remote_file("core/memory/engine.py"))

    def test_11_conflict_goes_back_to_the_author(self):
        f = self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"))
        seg = next(b for b in f["blocks"] if b["kind"] == "shown")
        cid = self.ok(self.api("emma", "post", "/changes", {"title": "Triple it"}))["id"]
        self.ok(self.api("emma", "put", f"/changes/{cid}/files", {"path": "core/memory/engine.py", "mode": "segments",
                                                                   "base_sha": f["head"], "segments": [{"start": seg["start"], "end": seg["end"],
                                                                                                        "text": "    def run(self, x):\n        return helper(x) * 3"}]}))
        self.ok(self.api("emma", "post", f"/changes/{cid}/submit"))
        git("pull", "-q", "origin", "main")
        write("core/memory/engine.py", remote_file("core/memory/engine.py").replace("return y * 2 + 1", "return y * 4"))
        git("commit", "-qam", "someone else edits run")
        git("push", "-q", "origin", "HEAD:main")
        self.ok(self.api("max", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        r = self.ok(self.api("dee", "post", f"/changes/{cid}/merge"), 409)
        self.assertIn("same place", r["detail"])
        self.assertEqual(self.ok(self.api("emma", "get", f"/changes/{cid}"))["status"], "conflict")
        self.assertIn("return y * 4", remote_file("core/memory/engine.py"))   # GitHub untouched

    # ── 6. features, expiry, revoking ────────────────────────────────────────
    def test_12_features(self):
        o = self.ok(self.api("vee", "post", "/features", {"name": "Prompts and UI", "items": [
            {"kind": "file", "path": "core/ai/prompt.py"}, {"kind": "folder", "path": "web"}]}))
        fid = o["features"][0]["id"]
        self.ok(self.api("vee", "post", "/grants", {"staff_id": self.ids["ian"], "feature_id": fid}))
        self.ok(self.api("ian", "get", "/file?path=core/ai/prompt.py"))
        self.ok(self.api("ian", "get", "/file?path=web/app.jsx"))
        self.ok(self.api("vee", "post", f"/features/{fid}/items", {"items": [{"kind": "file", "path": "README.md"}]}))
        self.ok(self.api("ian", "get", "/file?path=README.md"))            # added to the feature: ian has it at once

    def test_13_hr_takes_access_away(self):
        grants = self.ok(self.api("helen", "get", "/access"))["grants"]
        mine = [g for g in grants if g["person"]["id"] == self.ids["emma"]]
        self.assertTrue(mine)
        for g in mine:
            self.ok(self.api("helen", "delete", f"/grants/{g['id']}"))
        self.ok(self.api("emma", "get", "/file?path=core/memory/engine.py"), 403)

    def test_14_expired_grants_stop(self):
        self.ok(self.api("vee", "post", "/grants", {"staff_id": self.ids["emma"], "expires_on": "2020-01-01",
                                                    "items": [{"kind": "file", "path": "README.md"}]}), 400)
        from server.features.code import store
        with store.tx() as t:
            gid = t.run("INSERT INTO code_grants (repo_id, staff_id, granted_by, granted_at, expires_at) VALUES (?,?,?,?,?)",
                        (self.rid, self.ids["emma"], self.ids["vee"], db.now_iso(), "2020-01-01T00:00:00+00:00")).lastrowid
            t.run("INSERT INTO code_items (repo_id, grant_id, kind, path) VALUES (?,?,?,?)",
                  (self.rid, gid, "file", "README.md"))
        self.ok(self.api("emma", "get", "/file?path=README.md"), 403)

    def test_16_lost_copy_comes_back_from_github(self):
        from server.features.code import gitops
        gitops.remove(self.rid)
        self.assertFalse(gitops.repo_dir(self.rid).exists())
        self.ok(self.api("boss", "get", "/tree"), 409)
        for _ in range(100):
            if self.api("boss", "get", "/tree").status_code == 200:
                break
            time.sleep(0.1)
        files = {f["p"] for f in self.ok(self.api("boss", "get", "/tree"))["files"]}
        self.assertIn("core/memory/engine.py", files)

    # ── 7. authenticator ─────────────────────────────────────────────────────
    def test_20_no_authenticator_no_code(self):
        r = self.u["nora"].get("/api/code/repos")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["detail"]["field"], "authenticator")
        self.secrets["nora"] = enroll(self.u["nora"])
        self.ok(self.u["nora"].get("/api/code/repos"))

    def test_21_sign_in_asks_for_the_code(self):
        c = TestClient(app)
        c.__enter__()
        r = c.post("/api/auth/login", json={"email": "emma", "password": PW["emma"], "code": ""}, headers=H)
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.json().get("need_code"))
        r = c.post("/api/auth/login", json={"email": "emma", "password": PW["emma"], "code": "000000"}, headers=H)
        self.assertEqual(r.status_code, 401)
        good = login("emma", now_code(self.secrets["emma"]))
        self.ok(good.get("/api/code/repos"))
        with db.connect() as conn:
            stored = conn["staff"].find_one({"_id": self.ids["emma"]}, {"totp_secret": 1})["totp_secret"]
        self.assertNotIn(self.secrets["emma"], stored)          # sealed, never the seed itself

    # ── 8. protected paths ───────────────────────────────────────────────────
    def test_22_protected_is_a_wall(self):
        self.ok(self.api("vee", "get", "/file?path=core/memory/engine.py"))                  # read_all reads code...
        self.ok(self.api("vee", "get", "/file?path=core/system/update/apply.py"), 403)      # ...but not the updater
        self.ok(self.api("vee", "post", "/grants", {"staff_id": self.ids["max"], "items": [{"kind": "folder", "path": "core"}]}))
        self.ok(self.api("max", "get", "/file?path=core/ai/prompt.py"))
        self.ok(self.api("max", "get", "/file?path=core/system/update/apply.py"), 403)      # a wider grant stops at the wall
        self.ok(self.api("vee", "post", "/grants", {"staff_id": self.ids["max"],
                                                    "items": [{"kind": "folder", "path": "core/system/update"}]}), 403)
        self.ok(self.api("vee", "post", "/owners", {"staff_id": self.ids["dee"], "role": "owner", "path": "core/system/update"}), 403)
        self.ok(self.api("vee", "post", "/features", {"name": "Build", "items": [{"kind": "file", "path": "installer.iss"}]}), 403)
        self.ok(self.api("vee", "get", "/symbols?path=installer.iss"), 403)
        self.ok(self.api("boss", "post", "/grants", {"staff_id": self.ids["emma"], "can_edit": True,
                                                     "items": [{"kind": "file", "path": "installer.iss"}]}))
        self.ok(self.api("emma", "get", "/file?path=installer.iss"))

    def test_23_protected_changes_need_the_founder(self):
        f = self.ok(self.api("emma", "get", "/file?path=installer.iss"))
        cid = self.ok(self.api("emma", "post", "/changes", {"title": "Name the installer"}))["id"]
        self.ok(self.api("emma", "put", f"/changes/{cid}/files", {"path": "installer.iss", "mode": "segments", "base_sha": f["head"],
                                                                   "segments": [{"start": 1, "end": f["lines_total"],
                                                                                 "text": "[Setup]\nAppName=XiteAI OS1"}]}))
        d = self.ok(self.api("emma", "post", f"/changes/{cid}/submit"))
        self.assertTrue(any(ch.get("warn") and ch["file"] == "installer.iss" for ch in d["checks"]))   # build file: look closely
        self.ok(self.api("vee", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        d = self.ok(self.api("vee", "get", f"/changes/{cid}"))
        self.assertFalse(d["can"]["merge"])
        self.assertIn("only the founder", d["can"]["merge_why"])
        self.assertTrue(d["file_list"][0]["hidden"])                    # the VP can't see inside protected code
        self.ok(self.api("vee", "post", f"/changes/{cid}/merge"), 409)
        self.ok(self.api("boss", "post", f"/changes/{cid}/review", {"verdict": "approve"}))
        self.assertEqual(self.ok(self.api("boss", "post", f"/changes/{cid}/merge"))["status"], "merged")
        self.assertIn("AppName=XiteAI OS1", remote_file("installer.iss"))

    def test_24_diffs_stay_inside_access(self):
        head = self.ok(self.api("boss", "get", "/file?path=web/app.jsx"))["head"]
        cid = self.ok(self.api("boss", "post", "/changes", {"title": "Two areas at once"}))["id"]
        for path, line in (("core/memory/engine.py", "import os  # engine"), ("web/app.jsx", "import { useState } from 'react';")):
            self.ok(self.api("boss", "put", f"/changes/{cid}/files", {"path": path, "mode": "segments", "base_sha": head,
                                                                       "segments": [{"start": 1, "end": 1, "text": line}]}))
        self.ok(self.api("boss", "post", f"/changes/{cid}/submit"))
        d = {f["path"]: f for f in self.ok(self.api("max", "get", f"/changes/{cid}"))["file_list"]}
        self.assertTrue(d["core/memory/engine.py"]["hunks"])            # max reviews core/memory...
        self.assertTrue(d["web/app.jsx"]["hidden"])                      # ...so web/ stays closed to him
        self.assertEqual(d["web/app.jsx"]["hunks"], [])
        self.ok(self.api("boss", "post", f"/changes/{cid}/withdraw"))

    # ── 9. search ────────────────────────────────────────────────────────────
    def test_25_search_only_what_you_see(self):
        r = self.ok(self.api("boss", "get", "/search?q=secret_sauce"))
        self.assertEqual([(h["path"], h["symbol"]["name"]) for h in r["hits"]], [("core/memory/engine.py", "Engine.__init__")])
        self.assertEqual(self.ok(self.api("ian", "get", "/search?q=secret_sauce"))["hits"], [])
        f = self.ok(self.api("ian", "get", "/file?path=core/memory/engine.py"))
        visible = {n for b in f["blocks"] if b["kind"] == "shown" for n in range(b["start"], b["end"] + 1)}
        hits = self.ok(self.api("ian", "get", "/search?q=helper"))["hits"]
        self.assertTrue(hits)
        self.assertTrue(all(h["line"] in visible for h in hits if h["path"] == "core/memory/engine.py"))
        self.assertEqual(self.ok(self.api("ian", "get", "/search?q=verify(update)"))["hits"], [])      # protected
        names = [f["path"] for f in self.ok(self.api("emma", "get", "/search?q=page3"))["files"]]
        self.assertIn("docs/page3.md", names)
        self.ok(self.api("emma", "get", "/search?q=x"), 400)

    # ── 10. prompt sections and settings ─────────────────────────────────────
    def test_26_prompt_sections_by_name(self):
        syms = {s["name"]: s for s in self.ok(self.api("boss", "get", "/symbols?path=prompts/main.txt"))["symbols"]}
        self.assertEqual(set(syms), {"THE RULES", "THE TEST"})
        self.ok(self.api("boss", "post", "/grants", {"staff_id": self.ids["nora"], "can_edit": True,
                                                     "items": [{"kind": "symbol", "path": "prompts/main.txt", "symbol": "THE TEST"}]}))
        f = self.ok(self.api("nora", "get", "/file?path=prompts/main.txt"))
        shown = [ln for b in f["blocks"] if b["kind"] == "shown" for ln in b["lines"]]
        self.assertEqual(shown, ["THE TEST. Could this be said to a stranger?", "Then leave it out."])
        self.assertNotIn("Never lie", json.dumps(f))
        from server.features.code import text
        self.assertIn(("TOP_K", "setting"), [(s["name"], s["kind"]) for s in text.symbols("x.py", ["TOP_K = 8", "def f():", "    return TOP_K"])])

    # ── 11. look closely ─────────────────────────────────────────────────────
    def test_27_risky_lines_are_flagged_not_blocked(self):
        f = self.ok(self.api("boss", "get", "/file?path=core/ai/prompt.py"))
        cid = self.ok(self.api("boss", "post", "/changes", {"title": "Shell out"}))["id"]
        self.ok(self.api("boss", "put", f"/changes/{cid}/files", {
            "path": "core/ai/prompt.py", "mode": "segments", "base_sha": f["head"],
            "segments": [{"start": 1, "end": 1, "text": "import subprocess\nsubprocess.run(['ls'])\nPROMPT = 'x'"}]}))
        d = self.ok(self.api("boss", "post", f"/changes/{cid}/submit"))
        self.assertEqual(d["status"], "review")
        self.assertTrue(any(ch.get("warn") and "program" in ch["detail"] for ch in d["checks"]))
        self.ok(self.api("boss", "post", f"/changes/{cid}/withdraw"))

    # ── 12. the reading alarm ────────────────────────────────────────────────
    def test_28_reading_alarm_pauses_then_founder_resumes(self):
        for i in range(1, 7):
            self.ok(self.api("vic", "get", f"/file?path=docs/page{i}.md"))
        with db.connect() as conn:
            told = conn["notifications"].count_documents({"staff_id": self.ids["boss"], "kind": "code.unusual"})
        self.assertEqual(told, 1)
        self.ok(self.api("vic", "get", "/file?path=docs/page7.md"))
        self.ok(self.api("vic", "get", "/file?path=docs/page8.md"))
        r = self.api("vic", "get", "/file?path=README.md")                    # the ninth file: paused
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["detail"]["field"], "paused")
        self.assertEqual(self.api("vic", "get", "/tree").status_code, 403)   # the whole codebase, not one file
        sec = self.ok(self.u["boss"].get("/api/code/security"))
        self.assertIn(self.ids["vic"], [p["id"] for p in sec["paused"]])
        self.ok(self.u["boss"].post(f"/api/code/people/{self.ids['vic']}/resume", json={}, headers=H))
        self.ok(self.api("vic", "get", "/file?path=README.md"))

    def test_29_hr_resets_a_lost_authenticator(self):
        self.ok(self.u["helen"].post(f"/api/people/{self.ids['emma']}/reset-authenticator", json={}, headers=H))
        self.assertEqual(self.u["emma"].get("/api/code/repos").status_code, 401)      # signed out everywhere
        emma = login("emma")                                                          # no code needed any more...
        r = emma.get("/api/code/repos")
        self.assertEqual(r.json()["detail"]["field"], "authenticator")               # ...but code stays shut
        self.ok(self.u["boss"].put("/api/code/security", json={"require_mfa": False}, headers=H))
        self.ok(emma.get("/api/code/repos"))                                          # the founder's switch
        self.ok(self.u["boss"].put("/api/code/security", json={"require_mfa": True}, headers=H))
        self.assertEqual(emma.get("/api/code/repos").status_code, 403)
        self.secrets["emma"] = enroll(emma)
        self.u["emma"] = emma
        self.ok(emma.get("/api/code/repos"))

    # ── 13. history, undo, restore, checkpoints, backups ─────────────────────
    def sync(self):
        return self.u["boss"].post(f"/api/code/repos/{self.rid}/sync", json={}, headers=H)

    def github_commit(self, rel, content, msg):
        git("pull", "-q", "origin", "main")
        write(rel, content)
        git("commit", "-qam", msg)
        git("push", "-q", "origin", "HEAD:main")

    def test_30_history_is_trimmed_to_access(self):
        everything = self.ok(self.api("boss", "get", "/history"))["commits"]
        self.assertTrue(any(c["change"] for c in everything))          # merges link back to their change request
        mine = self.ok(self.api("emma", "get", "/history"))["commits"]  # emma reads installer.iss in full, nothing else
        self.assertTrue(mine)
        self.assertTrue(all(f["path"] == "installer.iss" for c in mine for f in c["files"]))
        self.ok(self.api("emma", "get", "/history?path=core/memory/engine.py"), 403)
        self.ok(self.api("emma", "get", "/history?path=installer.iss"))
        engine_change = next(c for c in everything if any(f["path"] == "core/memory/engine.py" for f in c["files"]))
        self.ok(self.api("boss", "get", f"/commits/{engine_change['sha']}"))
        self.ok(self.api("emma", "get", f"/commits/{engine_change['sha']}"), 403)

    def test_31_who_changed_each_line(self):
        runs = self.ok(self.api("boss", "get", "/blame?path=core/memory/engine.py"))["runs"]
        self.assertEqual(runs[0]["start"], 1)
        self.assertEqual(runs[-1]["end"], len(remote_file("core/memory/engine.py").splitlines()))
        self.assertIn("Ian Test", {r["author"] for r in runs})          # the intern's merged stop() change
        f = self.ok(self.api("ian", "get", "/file?path=core/memory/engine.py"))
        visible = {n for b in f["blocks"] if b["kind"] == "shown" for n in range(b["start"], b["end"] + 1)}
        for r in self.ok(self.api("ian", "get", "/blame?path=core/memory/engine.py"))["runs"]:
            self.assertTrue(set(range(r["start"], r["end"] + 1)) <= visible)

    def test_32_old_versions_and_restoring_a_file(self):
        seed = subprocess.run(["git", "rev-list", "--max-parents=0", "main"], cwd=REMOTE, capture_output=True, text=True).stdout.strip()
        self.github_commit("docs/page1.md", "# Page 1\n\nRewritten by hand.\n", "rewrite page 1")
        self.ok(self.sync())
        old = self.ok(self.api("boss", "get", f"/file?path=docs/page1.md&rev={seed}"))
        self.assertEqual(old["lines"], ["# Page 1", "", "Nothing to see."])
        self.ok(self.api("emma", "get", f"/file?path=docs/page1.md&rev={seed}"), 403)
        d = self.ok(self.api("boss", "post", "/restore", {"path": "docs/page1.md", "rev": seed}))
        self.assertEqual(d["status"], "review")
        self.assertTrue(d["title"].startswith("Restore page1.md"))
        self.assertEqual(self.ok(self.api("boss", "post", f"/changes/{d['id']}/merge", {"override": True}))["status"], "merged")
        self.assertEqual(remote_file("docs/page1.md"), "# Page 1\n\nNothing to see.\n")

    def test_33_undo_keeps_later_work_and_refuses_tangles(self):
        changes_ = self.ok(self.api("boss", "get", "/changes"))["items"]
        doubled = next(c for c in changes_ if c["title"] == "Run doubles then adds one")
        r = self.ok(self.api("boss", "post", f"/changes/{doubled['id']}/undo"), 409)       # GitHub rewrote those lines since
        self.assertIn("Later changes touched the same lines", r["detail"])
        stop = next(c for c in changes_ if c["title"] == "Stop says bye")
        self.ok(self.api("emma", "post", f"/changes/{stop['id']}/undo"), 403)                 # needs edit on all of it
        d = self.ok(self.api("boss", "post", f"/changes/{stop['id']}/undo"))
        self.assertEqual(d["status"], "review")
        self.assertTrue(d["title"].startswith("Undo: Stop says bye"))
        self.assertEqual(self.ok(self.api("boss", "post", f"/changes/{d['id']}/merge", {"override": True}))["status"], "merged")
        engine = remote_file("core/memory/engine.py")
        self.assertIn('return "stopped"', engine)                                          # taken back
        self.assertIn("return y * 4", engine)                                              # later work kept
        self.assertIn("# a", engine)

    def test_34_checkpoints(self):
        self.ok(self.api("emma", "post", "/checkpoints", {"name": "nope"}), 403)
        self.ok(self.api("boss", "post", "/checkpoints", {"name": "--evil"}), 400)
        cps = self.ok(self.api("boss", "post", "/checkpoints", {"name": "before big change", "note": "Safe point"}))["items"]
        self.assertEqual(cps[0]["name"], "before-big-change")
        self.assertTrue(cps[0]["on_github"])
        tags_ = subprocess.run(["git", "tag"], cwd=REMOTE, capture_output=True, text=True).stdout.split()
        self.assertIn("before-big-change", tags_)
        self.github_commit("docs/page2.md", "# Page 2\n\nChanged after the checkpoint.\n", "after checkpoint")
        self.ok(self.sync())
        cmp_ = self.ok(self.api("boss", "get", "/compare?base=before-big-change"))
        self.assertEqual([f["path"] for f in cmp_["files"]], ["docs/page2.md"])
        hist = self.ok(self.api("boss", "get", "/history"))["commits"]
        self.assertIn("before-big-change", [c["checkpoint"] for c in hist])

    def test_35_offline_backup_restores_without_github(self):
        b = self.ok(self.u["boss"].post(f"/api/code/{self.rid}/backups", json={}, headers=H))
        self.assertEqual(len(b["items"]), 1)
        bundle_path = Path(b["folder"]) / b["items"][0]["name"]
        out = TMP / "restored"
        subprocess.run(["git", "clone", "-q", str(bundle_path), str(out)], check=True, capture_output=True)
        self.assertEqual((out / "installer.iss").read_text(encoding="utf-8"), remote_file("installer.iss"))
        self.ok(self.u["vee"].get(f"/api/code/{self.rid}/backups"), 403)                    # founder only

    def test_36_line_comments(self):
        f = self.ok(self.api("ian", "get", "/file?path=core/memory/engine.py"))
        seg = next(b for b in f["blocks"] if b["kind"] == "shown" and b["editable"])
        cid = self.ok(self.api("ian", "post", "/changes", {"title": "Stop says goodbye"}))["id"]
        self.ok(self.api("ian", "put", f"/changes/{cid}/files", {"path": "core/memory/engine.py", "mode": "segments",
                                                                  "base_sha": f["head"], "segments": [{"start": seg["start"], "end": seg["end"],
                                                                                                       "text": "    def stop(self):\n        return 'goodbye'"}]}))
        self.ok(self.api("ian", "post", f"/changes/{cid}/submit"))
        new_line = seg["start"] + 1
        self.ok(self.api("dee", "post", f"/changes/{cid}/comments", {"path": "core/memory/engine.py", "side": "new",
                                                                      "line": new_line, "body": "Say bye instead?"}))
        self.ok(self.api("dee", "post", f"/changes/{cid}/comments", {"path": "core/memory/engine.py", "side": "new",
                                                                      "line": 1, "body": "Top-of-file note"}))
        seen = self.ok(self.api("ian", "get", f"/changes/{cid}"))["comments"]
        self.assertEqual([c["body"] for c in seen], ["Say bye instead?"])                   # the other line isn't his to see
        self.ok(self.api("ian", "post", f"/changes/{cid}/comments", {"path": "core/memory/engine.py", "side": "new",
                                                                      "line": 1, "body": "sneaky"}), 403)
        with db.connect() as conn:
            told = conn["notifications"].count_documents({"staff_id": self.ids["ian"], "kind": "code.comment"})
        self.assertGreaterEqual(told, 1)
        self.ok(self.api("ian", "post", f"/changes/{cid}/comments/{seen[0]['id']}/resolve"))
        self.assertTrue(self.ok(self.api("dee", "get", f"/changes/{cid}"))["comments"][0]["resolved"])
        self.ok(self.api("ian", "post", f"/changes/{cid}/withdraw"))

    def test_37_versions_that_look_like_options_are_refused(self):
        f = self.ok(self.api("boss", "get", "/file?path=README.md"))
        cid = self.ok(self.api("boss", "post", "/changes", {"title": "Injection attempt"}))["id"]
        evil = str(TMP / "pwned.txt")
        # A long one is stopped by input validation (422) before git is involved; a short one
        # gets past that and must be stopped by the version check itself (400). Either way: refused.
        for bad in (f"--output={evil}", "--output=pwned", "HEAD~1", "main..HEAD", "a b"):
            r = self.api("boss", "put", f"/changes/{cid}/files", {"path": "README.md", "mode": "segments", "base_sha": bad,
                                                                   "segments": [{"start": 1, "end": 1, "text": "x"}]})
            self.assertIn(r.status_code, (400, 422), r.text)
            self.assertEqual(self.api("boss", "get", f"/file?path=README.md&rev={bad}").status_code, 400)
            self.assertEqual(self.api("boss", "get", f"/compare?base={bad}").status_code, 400)
        self.assertEqual(self.api("boss", "put", f"/changes/{cid}/files", {"path": "README.md", "mode": "segments",
                                                                           "base_sha": "--output=pwned", "segments": [
                                                                               {"start": 1, "end": 1, "text": "x"}]}).status_code, 400)
        from server.features.code import gitops
        self.assertFalse(Path(evil).exists())
        self.assertFalse((gitops.repo_dir(self.rid) / "pwned").exists())
        self.ok(self.api("boss", "post", f"/changes/{cid}/withdraw"))
        self.assertTrue(f["head"])

    def test_38_deleting_a_feature_ends_its_access(self):
        """Deleting a feature takes its items, and every grant of it, in the same
        step: nobody keeps access to code through a feature that's gone."""
        from server.features.code import store

        def level(path):          # the map, not opening the file: opening would count towards the reading alarm
            return {f["p"]: f["a"] for f in self.ok(self.api("emma", "get", "/tree"))["files"]}[path]

        self.assertEqual(level("docs/page8.md"), "none")
        o = self.ok(self.api("vee", "post", "/features", {"name": "Page eight", "items": [
            {"kind": "file", "path": "docs/page8.md"}]}))
        fid = next(f["id"] for f in o["features"] if f["name"] == "Page eight")
        self.ok(self.api("vee", "post", "/grants", {"staff_id": self.ids["emma"], "feature_id": fid}))
        self.assertEqual(level("docs/page8.md"), "full")
        self.ok(self.api("vee", "delete", f"/features/{fid}"))
        self.assertEqual(level("docs/page8.md"), "none")
        self.assertEqual(store.scalar("SELECT COUNT(*) FROM code_grants WHERE feature_id = ?", (fid,)), 0)
        self.assertEqual(store.scalar("SELECT COUNT(*) FROM code_items WHERE feature_id = ?", (fid,)), 0)

    def test_39_history_guard_catches_a_force_push(self):
        before = self.ok(self.u["boss"].get("/api/code/repos"))["items"][0]["head_sha"]
        git("fetch", "-q", "origin")
        git("reset", "-q", "--hard", "origin/main~3")
        git("push", "-q", "--force", "origin", "HEAD:main")                                # someone rewrites GitHub
        r = self.sync()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["field"], "rewritten")
        repo = self.ok(self.u["boss"].get("/api/code/repos"))["items"][0]
        self.assertEqual(repo["head_sha"], before)                                          # the Terminal didn't follow
        self.assertEqual(self.sync().status_code, 409)
        with db.connect() as conn:
            told = conn["notifications"].count_documents({"staff_id": self.ids["boss"], "kind": "code.rewritten"})
        self.assertEqual(told, 1)                                                           # told once, not every sync
        self.ok(self.u["vee"].post(f"/api/code/repos/{self.rid}/history/put-back", json={}, headers=H), 403)
        self.ok(self.u["boss"].post(f"/api/code/repos/{self.rid}/history/put-back", json={}, headers=H))
        github_now = subprocess.run(["git", "rev-parse", "main"], cwd=REMOTE, capture_output=True, text=True).stdout.strip()
        self.assertEqual(github_now, before)                                                # the real history is back on GitHub
        self.ok(self.sync())
        # A second rewrite, and this time the founder follows GitHub; ours stays pinned.
        git("fetch", "-q", "origin")
        git("reset", "-q", "--hard", "origin/main~2")
        git("push", "-q", "--force", "origin", "HEAD:main")
        self.assertEqual(self.sync().status_code, 409)
        self.ok(self.u["boss"].post(f"/api/code/repos/{self.rid}/history/accept", json={}, headers=H))
        repo = self.ok(self.u["boss"].get("/api/code/repos"))["items"][0]
        self.assertEqual(repo["head_sha"], subprocess.run(["git", "rev-parse", "main"], cwd=REMOTE, capture_output=True,
                                                          text=True).stdout.strip())
        from server.features.code import gitops
        kept = subprocess.run(["git", "for-each-ref", "--format=%(objectname)", "refs/terminal/kept"],
                              cwd=gitops.repo_dir(self.rid), capture_output=True, text=True).stdout.split()
        self.assertIn(before, kept)                                                         # nothing is ever lost

    def test_15_opening_code_is_on_the_record(self):
        with db.connect() as conn:
            n = conn["audit"].count_documents({"action": "code.opened", "actor_id": self.ids["ian"]})
        self.assertGreaterEqual(n, 1)


if __name__ == "__main__":
    assert config.MONGO_DB_NAME == MONGO_DB_NAME and MONGO_DB_NAME != "xiteai_terminal" and \
        all(p.is_relative_to(TMP) for p in (config.CODE_DIR, config.CODE_BACKUP_DIR, config.CODE_DB_PATH)), \
        "refusing to run outside the sandbox"
    try:
        result = unittest.main(verbosity=2, exit=False).result
    finally:
        db.client().drop_database(MONGO_DB_NAME)
    sys.exit(0 if result.wasSuccessful() else 1)
