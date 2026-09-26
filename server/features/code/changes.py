"""Change requests: a draft of edits, sent for review, approved by whoever
answers for that code, merged here and pushed to GitHub under the author's
name.

  draft ─ submit ─► review ─┬─ approve (enough) ─ merge ─► merged
     ▲                      ├─ ask for changes ─► changes ─ resubmit ─► review
     │                      └─ reject ─► rejected
  (conflict: GitHub moved under the same lines; the author redoes the edit)

A person edits only lines they were given; the server rebuilds the whole
file itself, so an edit can never reach outside what they could see.

Change requests, their files, reviews and comments live in store (SQLite);
people, notifications and the audit trail in MongoDB (`conn`)."""
from __future__ import annotations

import json
import re

from fastapi import HTTPException

from ...access import perms as perms_mod
from ...core import audit, config, db, notify
from . import gitops, service, store, text
from .access import Viewer, guard_of, people_answering_for, protected_paths

OPEN = ("draft", "changes", "conflict")

_SECRETS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bjwt:eyJ[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|password)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"),
]


def _display_names(conn, ids=None) -> dict[int, str]:
    """{staff id: display name} from MongoDB; everyone when `ids` is None."""
    filt = {} if ids is None else {"id": {"$in": sorted({i for i in ids if i})}}
    return {r["id"]: r["display_name"] for r in conn["staff"].find(filt, {"id": 1, "display_name": 1})}


# ── loading ───────────────────────────────────────────────────────────────────

def get(change_id: int, repo_id: int) -> dict:
    c = store.one("SELECT * FROM code_changes WHERE id = ? AND repo_id = ?", (change_id, repo_id))
    if not c:
        raise HTTPException(404, "No change request by that number.")
    return c


def files(change_id: int) -> list[dict]:
    return store.rows("SELECT * FROM code_change_files WHERE change_id = ? ORDER BY path", (change_id,))


def approvals(conn, c: dict) -> list[dict]:
    """Approvals that still count: given after the files last changed."""
    rows = store.rows("SELECT * FROM code_reviews WHERE change_id = ? AND verdict = 'approve' AND at >= ?",
                      (c["id"], c["files_at"]))
    names = _display_names(conn, [r["staff_id"] for r in rows])
    for r in rows:
        r["display_name"] = names.get(r["staff_id"])
    return rows


def can_see(c: dict, v: Viewer) -> bool:
    if c["author_id"] == v.id or v.merge_all:
        return True
    return any(v.role_for(f["path"]) for f in files(c["id"]))


def reviewer_role(c: dict, v: Viewer) -> str | None:
    """How this person may review: 'all' (merge_all), 'owner', 'reviewer' or None."""
    if v.merge_all:
        return "all"
    roles = {v.role_for(f["path"]) for f in files(c["id"])} - {None}
    return "owner" if "owner" in roles else ("reviewer" if roles else None)


def protected_in(c: dict) -> list[str]:
    """The files in this change that sit inside a protected area."""
    protected = protected_paths(c["repo_id"])
    return [f["path"] for f in files(c["id"]) if guard_of(protected, f["path"])]


def approval_state(conn, c: dict) -> dict:
    """What's still missing before this can be merged. A protected file counts
    as approved only by the founder or someone placed inside its protection;
    `code.merge_all` doesn't reach in."""
    got = approvals(conn, c)
    fs = files(c["id"])
    protected = protected_paths(c["repo_id"])
    uncovered = []
    for f in fs:
        answering = {sid for sid, _ in people_answering_for(conn, c["repo_id"], f["path"])}
        walled = guard_of(protected, f["path"]) is not None
        if not any(a["staff_id"] in answering or (_is_founder(conn, a["staff_id"]) if walled else _merge_all(conn, a["staff_id"]))
                   for a in got):
            uncovered.append(f["path"])
    walled_files = [f["path"] for f in fs if guard_of(protected, f["path"])]
    return {"have": len({a["staff_id"] for a in got}), "need": c["need_approvals"], "uncovered": uncovered,
            "by": [a["display_name"] for a in got], "protected": walled_files,
            "ready": len({a["staff_id"] for a in got}) >= c["need_approvals"] and not uncovered}


def _merge_all(conn, staff_id: int) -> bool:
    row = conn["staff"].find_one({"_id": staff_id}, {"level": 1})
    lv = row["level"] if row else None
    return bool(lv) and (lv == "founder" or "code.merge_all" in perms_mod.effective(conn, lv))


def _is_founder(conn, staff_id: int) -> bool:
    row = conn["staff"].find_one({"_id": staff_id}, {"level": 1})
    return bool(row) and row["level"] == "founder"


# ── drafting ──────────────────────────────────────────────────────────────────

def create(row: dict, actor: dict, title: str, body: str) -> int:
    title = title.strip()[:120]
    if len(title) < 3:
        raise HTTPException(400, "Give the change a short title that says what it does.")
    now = db.now_iso()
    need = 2 if actor["level"] == "intern" else 1
    return store.run("INSERT INTO code_changes (repo_id, author_id, title, body, need_approvals, created_at, updated_at, "
                     "files_at) VALUES (?,?,?,?,?,?,?,?)",
                     (row["id"], actor["id"], title, body.strip()[:4000], need, now, now, now)).lastrowid


def _own_open(c: dict, actor: dict) -> None:
    if c["author_id"] != actor["id"]:
        raise HTTPException(403, "Only the person who wrote this change can edit it.")
    if c["status"] not in OPEN:
        raise HTTPException(409, "This change is no longer a draft.")


def _limits(change_id: int, path: str, new_text: str | None) -> None:
    if new_text is not None:
        if "\0" in new_text:
            raise HTTPException(415, "Only text can go into the codebase.")
        if len(new_text.encode("utf-8")) > config.CODE_MAX_FILE_KB * 1024:
            raise HTTPException(413, f"A file can be at most {config.CODE_MAX_FILE_KB} KB here.")
    others = [f for f in files(change_id) if f["path"] != path]
    if len(others) + 1 > config.CODE_MAX_FILES:
        raise HTTPException(413, f"A change can touch at most {config.CODE_MAX_FILES} files.")
    total = sum(len((f["new_text"] or "").encode("utf-8")) for f in others) + len((new_text or "").encode("utf-8"))
    if total > config.CODE_MAX_CHANGE_MB * 1024 * 1024:
        raise HTTPException(413, f"A change can be at most {config.CODE_MAX_CHANGE_MB} MB.")


def put_file(row: dict, v: Viewer, actor: dict, c: dict, body: dict) -> None:
    """One file's edit. mode: segments (their lines only), full (whole file),
    new (create in a folder they can edit), delete."""
    _own_open(c, actor)
    if "code.request" not in v.perms and not v.founder:
        raise HTTPException(403, "Your level doesn't include sending changes.")
    path = (body.get("path") or "").strip().strip("/")
    mode = body.get("mode")
    if not path or ".." in path.split("/") or path.startswith(".git/") or "\\" in path:
        raise HTTPException(400, "That isn't a file path in this repository.")
    if service.blocked(path):
        raise HTTPException(415, "Code and text only: models, media, archives and programs can't be added here.")

    if mode == "new":
        if service.exists(row, path):
            raise HTTPException(409, "That file already exists. Open it and edit it instead.")
        level, edit = v.level_for(path)
        if not (edit and level == "full"):
            raise HTTPException(403, "You can only add files inside a folder you can edit.")
        new_text = "\n".join(text.split_lines(body.get("text") or "")) + "\n"
        _limits(c["id"], path, new_text)
        _store(c, path, row["head_sha"], None, new_text, "")
        return

    base_sha = body.get("base_sha") or row["head_sha"]
    base = service.load(row, path, base_sha)
    head = base if base_sha == row["head_sha"] else service.load(row, path)
    whole, ranges_head = v.editable_lines(path, head.lines)
    if base_sha != row["head_sha"] and not whole:
        ranges = [r for r in (text.map_range(head.lines, base.lines, s, e) for s, e in ranges_head) if r]
    else:
        ranges = ranges_head
    old_text = base.to_bytes().decode("utf-8")

    if mode == "delete":
        if not whole:
            raise HTTPException(403, "Deleting a file needs edit access to all of it.")
        _limits(c["id"], path, None)
        _store(c, path, base_sha, old_text, None, "")
        return

    if mode == "full":
        if not whole:
            raise HTTPException(403, "You can edit only parts of this file. Edit those parts.")
        new_text = base.to_bytes(text.split_lines(body.get("text") or "")).decode("utf-8")
        _limits(c["id"], path, new_text)
        _store(c, path, base_sha, old_text, new_text, "")
        return

    if mode != "segments":
        raise HTTPException(400, "Unknown kind of edit.")
    segs = body.get("segments") or []
    allowed = set(ranges) if not whole else None
    lines = list(base.lines)
    if not segs:
        raise HTTPException(400, "Nothing was edited.")
    new_seen, shift, last_end = [], 0, 0
    for seg in sorted(segs, key=lambda s: int(s.get("start", 0))):
        s, e = int(seg.get("start", 0)), int(seg.get("end", 0))
        if s <= last_end:
            raise HTTPException(400, "Two edits overlap. Reload the file and try again.")
        last_end = e
        if allowed is not None and (s, e) not in allowed:
            raise HTTPException(403, f"Lines {s} to {e} aren't all yours to edit. Reload the file and try again.")
        if not (1 <= s <= e <= len(base.lines)):
            raise HTTPException(400, "Those lines aren't in the file any more. Reload it.")
        repl = text.split_lines(seg.get("text") or "")
        lines[s - 1 + shift:e + shift] = repl
        new_seen.append((s + shift, s + shift + len(repl) - 1))
        shift += len(repl) - (e - s + 1)
    new_text = base.to_bytes(lines).decode("utf-8")
    view = "" if whole or v.access(path, base.lines).read_full else json.dumps({
        "old": sorted(v.access(path, base.lines).visible() or []),
        "new": sorted({n for a, b in new_seen for n in range(a, b + 1)})})
    _limits(c["id"], path, new_text)
    _store(c, path, base_sha, old_text, new_text, view)


def _store(c, path, base_sha, old_text, new_text, view) -> None:
    now = db.now_iso()
    with store.tx() as t:
        t.run("INSERT INTO code_change_files (change_id, path, base_sha, old_text, new_text, author_view) "
              "VALUES (?,?,?,?,?,?) ON CONFLICT (change_id, path) DO UPDATE SET base_sha = excluded.base_sha, "
              "old_text = excluded.old_text, new_text = excluded.new_text, author_view = excluded.author_view",
              (c["id"], path, base_sha, old_text, new_text, view))
        t.run("UPDATE code_changes SET updated_at = ?, files_at = ?, checks_json = '[]' WHERE id = ?", (now, now, c["id"]))


def drop_file(actor: dict, c: dict, path: str) -> None:
    _own_open(c, actor)
    now = db.now_iso()
    with store.tx() as t:
        t.run("DELETE FROM code_change_files WHERE change_id = ? AND path = ?", (c["id"], path))
        t.run("UPDATE code_changes SET updated_at = ?, files_at = ? WHERE id = ?", (now, now, c["id"]))


# ── checks ────────────────────────────────────────────────────────────────────

def run_checks(fs: list[dict]) -> list[dict]:
    """Syntax for Python and JSON, and no secrets in added lines."""
    out = []
    for f in fs:
        if f["new_text"] is None:
            continue
        path, new = f["path"], f["new_text"]
        if path.lower().endswith(text.PY):
            try:
                compile(new, path, "exec", dont_inherit=True)
                out.append({"file": path, "check": "Python syntax", "ok": True, "detail": ""})
            except SyntaxError as e:
                out.append({"file": path, "check": "Python syntax", "ok": False,
                            "detail": f"Line {e.lineno}: {e.msg}"})
        elif path.lower().endswith(".json"):
            try:
                json.loads(new)
                out.append({"file": path, "check": "JSON", "ok": True, "detail": ""})
            except ValueError as e:
                out.append({"file": path, "check": "JSON", "ok": False, "detail": str(e)[:200]})
        old_lines = text.split_lines(f["old_text"] or "")
        added = [r for g in text.hunks(old_lines, text.split_lines(new), 0) for r in g if r["t"] == "+"]
        leak = next((r for r in added if any(rx.search(r["text"]) for rx in _SECRETS)), None)
        out.append({"file": path, "check": "No secrets", "ok": leak is None,
                    "detail": f"Line {leak['b']} looks like a key or password. Keys never go in code." if leak else ""})
        out += look_closely(path, added)
    return out


# Not wrong in themselves, and never blocking: the kinds of added line a
# reviewer should read twice, because that's where a backdoor or a data leak
# would have to live.
_RISKY = [
    (re.compile(r"\bsubprocess\b|\bos\.(system|popen|exec\w*|spawn\w*)\b|\bchild_process\b|\bexecSync\b|\bshell\s*=\s*True"),
     "starts a program or shell command"),
    (re.compile(r"(?<![\w.])(eval|exec)\s*\(|__import__\s*\(|\bnew Function\s*\(|\bimportlib\.import_module\b"),
     "runs code that's built while running"),
    (re.compile(r"\b(requests|httpx|aiohttp)\.\w+\(|\burllib\.request\b|\bfetch\s*\(|\bsocket\.|\bXMLHttpRequest\b|\bWebSocket\s*\("),
     "sends or receives over the network"),
    (re.compile(r"https?://(?!localhost|127\.0\.0\.1)[^\s'\"<>)]+"), "names a web address"),
    (re.compile(r"\bshutil\.rmtree\b|\bos\.(remove|unlink|rmdir)\b|\.unlink\s*\(|\brm\s+-rf\b|\bfs\.(rm|unlink)\w*\b"),
     "deletes files"),
    (re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|CERT_NONE|check_hostname\s*=\s*False"),
     "turns off a security check"),
    (re.compile(r"\bbase64\.(b64decode|b85decode|a85decode)\b|\batob\s*\(|\bcodecs\.decode\b"), "decodes hidden data"),
    (re.compile(r"\b(pickle|marshal|dill)\.loads?\b|\byaml\.load\s*\((?!.*SafeLoader)"), "loads data that can run code"),
    (re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"), "carries a long encoded blob"),
    (re.compile(r"\bctypes\b|\bwinreg\b|\bcrontab\b|\bschtasks\b|\bRegSetValue"), "reaches into the operating system"),
]
_BUILD_FILES = re.compile(r"(^|/)(requirements[^/]*\.txt|package(-lock)?\.json|pyproject\.toml|setup\.(py|cfg)|"
                          r"[^/]*\.spec|[^/]*\.iss|Dockerfile|\.github/.*)$", re.I)


def look_closely(path: str, added: list[dict]) -> list[dict]:
    notes = []
    if _BUILD_FILES.search(path) and added:
        notes.append({"file": path, "check": "Look closely", "ok": True, "warn": True, "line": added[0]["b"],
                      "detail": "Changes what gets installed or built. New dependencies ship to every user."})
    for r in added:
        for rx, why in _RISKY:
            if rx.search(r["text"]):
                notes.append({"file": path, "check": "Look closely", "ok": True, "warn": True, "line": r["b"],
                              "detail": f"Line {r['b']} {why}.", "text": r["text"].strip()[:200]})
                break
        if len(notes) >= 25:
            break
    return notes


# ── the review loop ───────────────────────────────────────────────────────────

def submit(conn, row: dict, actor: dict, c: dict) -> dict:
    _own_open(c, actor)
    fs = files(c["id"])
    if not fs:
        raise HTTPException(400, "Add at least one file edit first.")
    checks = run_checks(fs)
    now = db.now_iso()
    store.run("UPDATE code_changes SET checks_json = ?, updated_at = ? WHERE id = ?", (json.dumps(checks), now, c["id"]))
    failed = [ch for ch in checks if not ch["ok"]]
    if failed:
        raise HTTPException(400, f"{failed[0]['file']}: {failed[0]['check']} failed. {failed[0]['detail']}")
    store.run("UPDATE code_changes SET status = 'review', submitted_at = ?, updated_at = ? WHERE id = ?",
              (now, now, c["id"]))
    who = set()
    for f in fs:
        who |= {sid for sid, _ in people_answering_for(conn, row["id"], f["path"])}
    if not who:
        who = set(perms_mod.holders(conn, "code.merge_all", "intern")) | set(service.founders(conn))
    if protected_in(c):
        who |= set(service.founders(conn))              # protected code is the founder's call
    who.discard(actor["id"])
    notify.send(conn, who, "code.review", f"{actor['display_name']} sent a change for review",
                c["title"], f"/console/code/changes/{c['id']}", c["id"])
    audit.record(conn, actor, "code.change_sent", f"{row['name']} #{c['id']}", c["title"], actor["ip"])
    return get(c["id"], row["id"])


def review(conn, row: dict, v: Viewer, actor: dict, c: dict, verdict: str, body: str) -> None:
    if verdict not in ("approve", "changes", "comment", "reject"):
        raise HTTPException(400, "Unknown review.")
    body = (body or "").strip()[:4000]
    mine = c["author_id"] == actor["id"]
    role = reviewer_role(c, v)
    if verdict == "comment":
        if not (mine or role):
            raise HTTPException(403, "Only the author and the people answering for this code can comment.")
        if not body:
            raise HTTPException(400, "Write something.")
    else:
        if mine:
            raise HTTPException(403, "You can't review your own change.")
        if not role:
            raise HTTPException(403, "You don't answer for any of the code in this change.")
        if c["status"] != "review":
            raise HTTPException(409, "This change isn't waiting for review.")
        if verdict == "reject" and role == "reviewer":
            raise HTTPException(403, "Only an owner can reject a change. Ask for changes instead.")
        if verdict in ("changes", "reject") and not body:
            raise HTTPException(400, "Say what needs to change, so they know what to do.")
    now = db.now_iso()
    status = {"changes": "changes", "reject": "rejected"}.get(verdict, c["status"])
    with store.tx() as t:
        t.run("INSERT INTO code_reviews (change_id, staff_id, verdict, body, at) VALUES (?,?,?,?,?)",
              (c["id"], actor["id"], verdict, body, now))
        t.run("UPDATE code_changes SET status = ?, updated_at = ? WHERE id = ?", (status, now, c["id"]))
    if not mine and c["author_id"]:
        words = {"approve": "approved", "changes": "asked for changes to", "reject": "rejected",
                 "comment": "commented on"}[verdict]
        notify.send(conn, [c["author_id"]], "code.reviewed", f"{actor['display_name']} {words} your change",
                    c["title"], f"/console/code/changes/{c['id']}", c["id"])
    audit.record(conn, actor, f"code.change_{verdict}", f"{row['name']} #{c['id']}", body[:200], actor["ip"])


def withdraw(actor: dict, c: dict) -> None:
    if c["author_id"] != actor["id"]:
        raise HTTPException(403, "Only the author can withdraw it.")
    if c["status"] in ("merged", "rejected", "withdrawn"):
        raise HTTPException(409, "It's already closed.")
    store.run("UPDATE code_changes SET status = 'withdrawn', updated_at = ? WHERE id = ?", (db.now_iso(), c["id"]))


def can_merge(conn, c: dict, v: Viewer) -> tuple[bool, str]:
    if c["status"] != "review":
        return False, "It isn't waiting for review."
    if c["author_id"] == v.id and not v.founder:
        return False, "Someone else merges your change."
    fs = files(c["id"])
    walled = protected_in(c)
    if walled and not v.founder:
        return False, f"It touches protected code ({walled[0]}), so only the founder merges it."
    if not (v.merge_all or all(v.role_for(f["path"]) == "owner" for f in fs)):
        return False, "An owner of every file in it, or someone who can merge anything, merges it."
    st = approval_state(conn, c)
    if not st["ready"]:
        mine = any(a["staff_id"] == v.id for a in approvals(conn, c))
        if st["uncovered"] and not mine and c["author_id"] != v.id and \
                (v.merge_all or any(v.role_for(p) for p in st["uncovered"])):
            if st["need"] <= 1:
                return False, "Approve it first; then you can merge it."
            return False, f"Needs {st['need']} approvals; yours can be one of them."
        if st["uncovered"]:
            return False, f"Still needs an approval from whoever answers for {st['uncovered'][0]}."
        return False, f"Needs {st['need']} approval{'s' if st['need'] > 1 else ''}; has {st['have']}."
    return True, ""


def merge(conn, row: dict, v: Viewer, actor: dict, c: dict, override: bool) -> dict:
    ok, why = can_merge(conn, c, v)
    if not ok and not (override and v.founder and c["status"] == "review"):
        raise HTTPException(409, why)
    fs = files(c["id"])
    with gitops.lock(row["id"]):
        # Level with GitHub first, so the merge lands on what's really there.
        try:
            old_head, head, remote = gitops.sync(row["id"], row["remote_url"], row["branch"], row["remote_sha"])
        except gitops.HistoryRewritten as e:
            service.rewritten(conn, row, e)                   # nothing merges until the founder decides
        except gitops.GitError as e:
            raise HTTPException(502, f"Couldn't reach GitHub before merging: {e}")
        if old_head != head:
            service.remap(row["id"], old_head, head)
        writes, conflicts = {}, []
        for f in fs:
            current = gitops.show(row["id"], head, f["path"])
            base = f["old_text"].encode("utf-8") if f["old_text"] is not None else None
            new = f["new_text"].encode("utf-8") if f["new_text"] is not None else None
            if base is None:                                   # a new file
                if current is not None:
                    conflicts.append(f["path"])
                writes[f["path"]] = new
            elif new is None:                                  # a deletion
                if current != base:
                    conflicts.append(f["path"])
                writes[f["path"]] = None
            elif current == base:
                writes[f["path"]] = new
            elif current is None:
                conflicts.append(f["path"])
            else:
                merged, clean = gitops.merge_file(current, base, new)
                if not clean:
                    conflicts.append(f["path"])
                writes[f["path"]] = merged
        checks = run_checks([{"path": p, "old_text": (gitops.show(row["id"], head, p) or b"").decode("utf-8", "replace"),
                              "new_text": d.decode("utf-8", "replace") if d is not None else None}
                             for p, d in writes.items() if p not in conflicts])
        broken = [ch for ch in checks if not ch["ok"]]
        if conflicts or broken:
            store.run("UPDATE code_changes SET status = 'conflict', updated_at = ? WHERE id = ?", (db.now_iso(), c["id"]))
            what = (f"Someone changed {conflicts[0]} on GitHub in the same place." if conflicts
                    else f"After combining with the latest code, {broken[0]['file']} fails: {broken[0]['detail']}")
            notify.send(conn, [c["author_id"]], "code.conflict", "Your change needs redoing on the latest code",
                        what, f"/console/code/changes/{c['id']}", c["id"])
            raise HTTPException(409, what + " It's back with the author to redo on the latest code.")
        author = (db.strip(conn["staff"].find_one({"_id": c["author_id"]}, {"display_name": 1, "email": 1})) or
                 {"display_name": "Former team member", "email": config.CODE_COMMITTER_EMAIL})
        approved = ", ".join(approval_state(conn, c)["by"]) or ("nobody (founder override)" if override else "nobody")
        message = (f"{c['title']}\n\n{c['body']}\n\n" if c["body"] else f"{c['title']}\n\n") + \
                  f"Change #{c['id']} in XiteAI Terminal. Approved by {approved}. Merged by {actor['display_name']}.\n"
        try:
            sha = gitops.commit(row["id"], writes, author["display_name"], author["email"], message)
        except gitops.GitError as e:
            gitops.undo_last(row["id"], head)
            raise HTTPException(500, f"Couldn't commit: {e}")
        github, detail = "pushed", ""
        if row["remote_url"].startswith("https://") and not config.GITHUB_TOKEN:
            github, detail = "local", "Not on GitHub yet: the server has no GitHub token."
        else:
            try:
                gitops.push(row["id"], row["remote_url"], row["branch"])
                remote = sha                                  # the guard's memory moves with our own push
            except gitops.GitError as e:
                github, detail = "failed", f"Merged here; GitHub push failed ({e}). It retries on the next sync."
        service.remap(row["id"], head, sha)
    now = db.now_iso()
    with store.tx() as t:
        t.run("UPDATE code_repos SET head_sha = ?, remote_sha = ?, last_sync_at = ? WHERE id = ?",
              (sha, remote, now, row["id"]))
        t.run("UPDATE code_changes SET status = 'merged', merged_by = ?, merged_at = ?, merged_sha = ?, github = ?, "
              "github_detail = ?, updated_at = ? WHERE id = ?", (actor["id"], now, sha, github, detail, now, c["id"]))
    if c["author_id"] != actor["id"]:
        notify.send(conn, [c["author_id"]], "code.merged", f"{actor['display_name']} merged your change",
                    c["title"], f"/console/code/changes/{c['id']}", c["id"])
    notify.clear(conn, "code.review", c["id"])
    audit.record(conn, actor, "code.change_merged", f"{row['name']} #{c['id']}",
                 ("founder override; " if override and not ok else "") + f"{sha[:10]} {github}", actor["ip"])
    return get(c["id"], row["id"])


# ── undo and restore: new changes, reviewed like any other ────────────────────

def _decode(data: bytes | None, path: str) -> str | None:
    if data is None:
        return None
    try:
        return text.Text(data).to_bytes().decode("utf-8")
    except text.NotText:
        raise HTTPException(415, f"{path} isn't a text file, so it can't be changed here.") from None


def _whole_file_edit(v: Viewer, row: dict, path: str, exists_now: bool) -> None:
    if v.founder:
        return
    if exists_now:
        whole, _ = v.editable_lines(path, service.load(row, path).lines)
    else:
        level, edit = v.level_for(path)
        whole = level == "full" and edit
    if not whole:
        raise HTTPException(403, f"This needs edit access to all of {path}.")


def _open_as_change(conn, row: dict, v: Viewer, actor: dict, title: str, body: str,
                    writes: dict[str, tuple[str | None, str | None]]) -> dict:
    if not writes:
        raise HTTPException(409, "There's nothing to change: the code already looks like that.")
    if "code.request" not in v.perms and not v.founder:
        raise HTTPException(403, "Your level doesn't include sending changes.")
    cid = create(row, actor, title, body)
    c = get(cid, row["id"])
    for path, (old, new) in writes.items():
        _limits(cid, path, new)
        _store(c, path, row["head_sha"], old, new, "")
    try:
        return submit(conn, row, actor, get(cid, row["id"]))
    except HTTPException:
        return get(cid, row["id"])            # a failed check leaves it as a draft, with the reason on it


def undo(conn, row: dict, v: Viewer, actor: dict, sha: str) -> dict:
    """Take one past change back out, keeping everything written since: for each
    file, a three-way merge of (now, what that change produced, what was there
    before it). If later work touched the same lines, nothing is guessed."""
    try:
        sha = gitops.safe_rev(sha)
    except gitops.GitError:
        raise HTTPException(400, "That isn't a version this server knows.") from None
    found = gitops.log(row["id"], sha, limit=1)
    if not found or not gitops.is_ancestor(row["id"], found[0]["sha"], row["head_sha"]):
        raise HTTPException(404, "No such change in this repository's history.")
    c = found[0]
    if not c["parents"]:
        raise HTTPException(400, "The very first version can't be undone.")
    parent, head = c["parents"][0], row["head_sha"]
    writes, tangled = {}, []
    for st, p, np in c["files"]:
        path = p if st == "D" else np
        if v.guarded(path) and not v.founder:
            raise HTTPException(403, f"{path} is protected. Only the founder undoes protected code.")
        before = gitops.show(row["id"], parent, p) if st != "A" else None
        after = gitops.show(row["id"], c["sha"], np) if st != "D" else None
        now = gitops.show(row["id"], head, path)
        if st == "A":                                   # it added a file: remove it, if nobody changed it since
            if now is None:
                continue
            if now != after:
                tangled.append(path)
                continue
            _whole_file_edit(v, row, path, True)
            writes[path] = (_decode(now, path), None)
        elif st == "D":                                 # it deleted a file: bring it back
            if now is not None:
                tangled.append(path)
                continue
            _whole_file_edit(v, row, path, False)
            writes[path] = (None, _decode(before, path))
        else:
            if now is None:
                tangled.append(path)
                continue
            merged, clean = gitops.merge_file(now, after or b"", before or b"")
            if not clean:
                tangled.append(path)
                continue
            _whole_file_edit(v, row, path, True)
            if merged != now:
                writes[path] = (_decode(now, path), _decode(merged, path))
    if tangled:
        raise HTTPException(409, f"Later changes touched the same lines in {tangled[0]}"
                                 + (f" and {len(tangled) - 1} more" if len(tangled) > 1 else "")
                                 + ". Undo those first, or change it by hand.")
    changes, _ = history_links(row)
    origin = f"change #{changes[c['sha']]['id']}" if c["sha"] in changes else c["sha"][:10]
    body = (f"Takes back {origin}, \"{c['subject']}\" by {c['author']} on {c['at'][:10]}. "
            f"Anything written since stays as it is.")
    return _open_as_change(conn, row, v, actor, f"Undo: {c['subject']}"[:120], body, writes)


def restore(conn, row: dict, v: Viewer, actor: dict, path: str, rev: str) -> dict:
    """Put one file back the way it was at an earlier version (a checkpoint, a date)."""
    try:
        rev = gitops.safe_rev(rev)
    except gitops.GitError:
        raise HTTPException(400, "That isn't a version this server knows.") from None
    if not gitops.is_ancestor(row["id"], rev, row["head_sha"]):
        raise HTTPException(404, "That version isn't in this repository's history.")
    if v.guarded(path) and not v.founder:
        raise HTTPException(403, f"{path} is protected. Only the founder restores protected code.")
    then = gitops.show(row["id"], rev, path)
    now = gitops.show(row["id"], row["head_sha"], path)
    if then is None:
        raise HTTPException(404, f"{path} didn't exist at that version.")
    _whole_file_edit(v, row, path, now is not None)
    if now == then:
        raise HTTPException(409, "It already looks exactly like that.")
    when = next(iter(gitops.log(row["id"], rev, limit=1)), {}).get("at", "")[:10]
    return _open_as_change(conn, row, v, actor, f"Restore {path.rsplit('/', 1)[-1]} to {when or rev[:10]}"[:120],
                           f"Puts {path} back exactly as it was at {rev[:10]}" + (f" ({when})." if when else "."),
                           {path: (_decode(now, path), _decode(then, path))})


def history_links(row: dict) -> tuple[dict, dict]:
    from .history import _links
    return _links(row)


# ── comments on exact lines ───────────────────────────────────────────────────

def _file_view(v: Viewer, c: dict, path: str) -> tuple[set | None, set | None] | None:
    """(old lines, new lines) this person may see in this change's diff of
    `path`, None for all, or None overall when they can't see the file."""
    f = store.one("SELECT author_view FROM code_change_files WHERE change_id = ? AND path = ?", (c["id"], path))
    if not f:
        return None
    if v.level_for(path)[0] == "full":
        return (None, None)
    if c["author_id"] == v.id:
        if not f["author_view"]:
            return (None, None)
        view = json.loads(f["author_view"])
        return (set(view["old"]), set(view["new"]))
    return None


def comment(conn, v: Viewer, actor: dict, c: dict, path: str, side: str, line: int, body: str) -> None:
    body = (body or "").strip()[:4000]
    if side not in ("new", "old") or line < 1 or not body:
        raise HTTPException(400, "Say which line, and write something.")
    if not (c["author_id"] == actor["id"] or reviewer_role(c, v)):
        raise HTTPException(403, "Only the author and the people answering for this code can comment.")
    view = _file_view(v, c, path)
    if view is None:
        raise HTTPException(403, "That file isn't shared with you.")
    allowed = view[1] if side == "new" else view[0]
    if allowed is not None and line not in allowed:
        raise HTTPException(403, "That line isn't shared with you.")
    now = db.now_iso()
    with store.tx() as t:
        t.run("INSERT INTO code_comments (change_id, path, side, line, body, staff_id, at) VALUES (?,?,?,?,?,?,?)",
              (c["id"], path, side, line, body, actor["id"], now))
        t.run("UPDATE code_changes SET updated_at = ? WHERE id = ?", (now, c["id"]))
    if actor["id"] != c["author_id"]:
        who = [c["author_id"]]
    else:
        who = [r["staff_id"] for r in store.rows(
            "SELECT staff_id FROM code_reviews WHERE change_id = ? UNION SELECT staff_id FROM code_comments WHERE change_id = ?",
            (c["id"], c["id"])) if r["staff_id"] and r["staff_id"] != actor["id"]]
    notify.send(conn, who, "code.comment", f"{actor['display_name']} commented on line {line} of {path.rsplit('/', 1)[-1]}",
                body[:140], f"/console/code/changes/{c['id']}", c["id"])


def resolve_comment(v: Viewer, actor: dict, c: dict, comment_id: int) -> None:
    row = store.one("SELECT * FROM code_comments WHERE id = ? AND change_id = ?", (comment_id, c["id"]))
    if not row:
        raise HTTPException(404, "No such comment.")
    if not (actor["id"] in (row["staff_id"], c["author_id"]) or reviewer_role(c, v)):
        raise HTTPException(403, "The author, the commenter or a reviewer marks it done.")
    store.run("UPDATE code_comments SET resolved_by = ?, resolved_at = ? WHERE id = ?",
              (actor["id"], db.now_iso(), comment_id))


def comments_for(v: Viewer, c: dict, names: dict[int, str]) -> list[dict]:
    views: dict[str, tuple | None] = {}
    out = []
    for r in store.rows("SELECT * FROM code_comments WHERE change_id = ? ORDER BY at, id", (c["id"],)):
        if r["path"] not in views:
            views[r["path"]] = _file_view(v, c, r["path"])
        view = views[r["path"]]
        if view is None:
            continue
        allowed = view[1] if r["side"] == "new" else view[0]
        if allowed is not None and r["line"] not in allowed:
            continue
        out.append({"id": r["id"], "path": r["path"], "side": r["side"], "line": r["line"], "body": r["body"],
                    "by": names.get(r["staff_id"], "someone removed"), "at": r["at"],
                    "resolved": bool(r["resolved_at"]), "resolved_by": names.get(r["resolved_by"]) if r["resolved_by"] else None})
    return out


# ── reading them ──────────────────────────────────────────────────────────────

def card(c: dict, names: dict) -> dict:
    fs = files(c["id"])
    added = removed = 0
    for f in fs:
        a, r = text.stats(text.split_lines(f["old_text"] or ""), text.split_lines(f["new_text"] or ""))
        added, removed = added + a, removed + r
    return {"id": c["id"], "title": c["title"], "status": c["status"], "author": names.get(c["author_id"], "someone removed"),
            "author_id": c["author_id"], "files": len(fs), "added": added, "removed": removed,
            "updated_at": c["updated_at"], "submitted_at": c["submitted_at"], "github": c["github"]}


def listing(conn, row: dict, v: Viewer) -> list[dict]:
    rows = store.rows("SELECT * FROM code_changes WHERE repo_id = ? ORDER BY updated_at DESC LIMIT 300", (row["id"],))
    names = _display_names(conn, [c["author_id"] for c in rows])
    out = []
    for c in rows:
        if c["status"] == "draft" and c["author_id"] != v.id:
            continue
        if can_see(c, v):
            out.append(card(c, names))
    return out


def detail(conn, row: dict, v: Viewer, c: dict) -> dict:
    if not can_see(c, v) or (c["status"] == "draft" and c["author_id"] != v.id):
        raise HTTPException(404, "No change request by that number.")
    mine = c["author_id"] == v.id
    role = reviewer_role(c, v)
    out_files = []
    for f in files(c["id"]):
        old, new = text.split_lines(f["old_text"] or ""), text.split_lines(f["new_text"] or "")
        kind = "new" if f["old_text"] is None else "deleted" if f["new_text"] is None else "edited"
        a, r = text.stats(old, new)
        entry = {"path": f["path"], "kind": kind, "added": a, "removed": r, "base_sha": f["base_sha"],
                 "protected": bool(v.guarded(f["path"]))}
        if mine and f["author_view"] and v.level_for(f["path"])[0] != "full":
            # The author sees their own edit, and only the lines they were given around it.
            view = json.loads(f["author_view"])
            entry["hunks"] = text.hunks(old, new, 3, set(view["old"]), set(view["new"]))
        elif mine or v.level_for(f["path"])[0] == "full":
            entry["hunks"] = text.hunks(old, new, 3)
        else:
            # Anyone else sees a file's diff only if they could open the whole file:
            # answering for one folder in a change doesn't reveal the others.
            entry["hunks"], entry["hidden"] = [], True
        out_files.append(entry)
    ok, why = can_merge(conn, c, v)
    review_rows = store.rows("SELECT * FROM code_reviews WHERE change_id = ? ORDER BY at, id", (c["id"],))
    comment_rows = store.rows("SELECT staff_id, resolved_by FROM code_comments WHERE change_id = ?", (c["id"],))
    names = _display_names(conn, [c["author_id"], c["merged_by"]] + [r["staff_id"] for r in review_rows]
                           + [x for r in comment_rows for x in (r["staff_id"], r["resolved_by"])])
    return card(c, names) | {
        "body": c["body"], "created_at": c["created_at"], "merged_at": c["merged_at"], "merged_sha": c["merged_sha"],
        "merged_by": names.get(c["merged_by"]) if c["merged_by"] else None, "github_detail": c["github_detail"],
        "need_approvals": c["need_approvals"], "checks": json.loads(c["checks_json"] or "[]"),
        "file_list": out_files, "approval": approval_state(conn, c),
        "reviews": [{"by": names.get(r["staff_id"]) or "someone removed", "verdict": r["verdict"],
                    "body": r["body"], "at": r["at"]} for r in review_rows],
        "comments": comments_for(v, c, names),
        "can": {"edit": mine and c["status"] in OPEN, "submit": mine and c["status"] in OPEN,
                "withdraw": mine and c["status"] not in ("merged", "rejected", "withdrawn"),
                "review": bool(role) and not mine and c["status"] == "review",
                "reject": role in ("owner", "all") and not mine and c["status"] == "review",
                "comment": mine or bool(role),
                "merge": ok, "merge_why": why,
                "override": v.founder and c["status"] == "review" and not ok,
                "undo": c["status"] == "merged" and bool(c["merged_sha"]) and (v.founder or "code.request" in v.perms)},
    }
