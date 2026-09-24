"""Repositories, the folder map, opening a file, and who was given what.

GitHub is the master copy; the server keeps a clone that follows it. Every
read goes through access.Viewer, so a person only ever receives the lines
they may see."""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from ...access import levels
from ...core import audit, config, db, notify, settings
from . import gitops, text
from .access import Viewer, covers, protected_paths

log = logging.getLogger("terminal.code")

# What a supply-chain attack would aim at: code that ships to every user or
# decides what they trust. Seeded as protected on connect (the ones that
# exist); the founder edits the list from Codebase > Repositories.
PROTECT_SUGGEST = [
    ".github", "keys", "core/system/update", "build_release.py", "publish_release.py", "build_manifest.py",
    "installer.iss", "ella.spec", "requirements.txt", "requirements-dev.txt", "pyinstaller_hooks",
    "tools/gen_update_key.py", "package.json", "package-lock.json", "Dockerfile",
]

# Never accepted as a change, whatever their contents: models, media,
# archives, programs, databases, images, fonts. Code and text only.
BLOCKED_EXT = {
    ".gguf", ".onnx", ".pt", ".pth", ".bin", ".safetensors", ".ckpt", ".h5", ".pb", ".tflite", ".npy", ".npz",
    ".pkl", ".pickle", ".joblib", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".flac", ".ogg", ".m4a",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".xz", ".exe", ".dll", ".so", ".dylib", ".msi", ".iso", ".db", ".sqlite",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".psd", ".ttf", ".otf", ".woff", ".woff2",
}
_GITHUB_URL = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?$")
_BRANCH = re.compile(r"^[\w./-]{1,100}$")


def blocked(path: str) -> bool:
    low = path.lower()
    return any(low.endswith(ext) for ext in BLOCKED_EXT)


# ── repositories ──────────────────────────────────────────────────────────────

def repo(conn, repo_id: int, ready: bool = True) -> dict:
    row = db.strip(conn["code_repos"].find_one({"_id": repo_id}))
    if not row:
        raise HTTPException(404, "No repository by that id.")
    if row["status"] == "ready" and not gitops.repo_dir(repo_id).exists():
        # The server's copy is gone (a new server, a wiped disk): GitHub has it all.
        conn["code_repos"].update_one({"_id": repo_id}, {"$set": {"status": "cloning",
                                                                  "status_detail": "Copying it again from GitHub"}})
        threading.Thread(target=_clone, args=(repo_id, row["remote_url"], row["branch"]), daemon=True).start()
        row["status"] = "cloning"
    if ready and row["status"] != "ready":
        raise HTTPException(409, "This repository isn't ready yet." if row["status"] == "cloning"
                            else f"This repository couldn't be set up: {row['status_detail']}")
    if row["status"] == "ready":
        seed_protected(conn, row)
    return row


def _insert_ignore(coll, doc: dict) -> None:
    try:
        coll.insert_one(doc)
    except DuplicateKeyError:
        pass


def seed_protected(conn, row: dict) -> None:
    """Once per repository: protect the suggested paths that exist in it. Once
    only, so a path the founder deliberately unprotects stays unprotected."""
    key = f"code_protected_seeded:{row['id']}"
    if settings.get(conn, key) == "1":
        return
    files = [p for p, _ in gitops.ls(row["id"], row["head_sha"] or "HEAD")]
    now = db.now_iso()
    wanted = [p for p in PROTECT_SUGGEST if any(covers(p, f) for f in files)]
    if wanted:
        ids = db.next_ids(conn, "code_protected", len(wanted))
        for pid, p in zip(ids, wanted):
            _insert_ignore(conn["code_protected"], {"_id": pid, "id": pid, "repo_id": row["id"], "path": p,
                                                    "added_by": None, "added_at": now})
    settings.put(conn, key, "1")


def repo_card(row: dict) -> dict:
    return {k: row[k] for k in ("id", "name", "remote_url", "branch", "status", "status_detail", "head_sha",
                                "last_sync_at", "created_at", "held_remote")} | {
        "pushes": bool(config.GITHUB_TOKEN) or not row["remote_url"].startswith("https://")}


def connect_repo(conn, actor: dict, name: str, url: str, branch: str) -> dict:
    name, url, branch = name.strip()[:80], url.strip(), (branch or "main").strip()
    if len(name) < 2:
        raise HTTPException(400, "Give the repository a name.")
    if not _BRANCH.match(branch):
        raise HTTPException(400, "That isn't a branch name.")
    if not (_GITHUB_URL.match(url) or (config.CODE_ALLOW_LOCAL and not url.startswith(("http:", "https:")))):
        raise HTTPException(400, "Use the repository's GitHub address, like https://github.com/you/repo.")
    rid = db.next_id(conn, "code_repos")
    conn["code_repos"].insert_one({
        "_id": rid, "id": rid, "name": name, "remote_url": url, "branch": branch, "status": "cloning",
        "status_detail": "", "head_sha": "", "remote_sha": "", "held_remote": "", "last_sync_at": None,
        "created_by": actor["id"], "created_at": db.now_iso(),
    })
    audit.record(conn, actor, "code.repo_connected", name, url, actor["ip"])
    threading.Thread(target=_clone, args=(rid, url, branch), daemon=True, name=f"clone-{rid}").start()
    return repo_card(db.strip(conn["code_repos"].find_one({"_id": rid})))


def _clone(rid: int, url: str, branch: str) -> None:
    try:
        with gitops.lock(rid):
            sha = gitops.clone(rid, url, branch)
        with db.connect() as conn:
            conn["code_repos"].update_one({"_id": rid}, {"$set": {"status": "ready", "status_detail": "",
                                                                  "head_sha": sha, "remote_sha": sha,
                                                                  "held_remote": "", "last_sync_at": db.now_iso()}})
    except gitops.GitError as e:
        with db.connect() as conn:
            conn["code_repos"].update_one({"_id": rid}, {"$set": {"status": "failed", "status_detail": str(e)}})


def sync(conn, row: dict) -> dict:
    """Follow GitHub now; move every grant along with the code. If GitHub's
    history was rewritten, stop and tell the founder (once)."""
    try:
        with gitops.lock(row["id"]):
            old, new, remote = gitops.sync(row["id"], row["remote_url"], row["branch"], row["remote_sha"])
            if old != new:
                remap(conn, row["id"], old, new)
        conn["code_repos"].update_one({"_id": row["id"]}, {"$set": {"head_sha": new, "remote_sha": remote,
                                                                    "held_remote": "", "last_sync_at": db.now_iso(),
                                                                    "status_detail": ""}})
    except gitops.HistoryRewritten as e:
        rewritten(conn, row, e)
    except gitops.GitError as e:
        conn["code_repos"].update_one({"_id": row["id"]}, {"$set": {"status_detail": f"Last sync failed: {e}"}})
        raise HTTPException(502, f"Couldn't sync with GitHub: {e}")
    return db.strip(conn["code_repos"].find_one({"_id": row["id"]}))


REWRITTEN = ("GitHub's history for this repository was rewritten (someone force-pushed). The Terminal kept the real "
             "history and stopped following GitHub. The founder decides what happens next, from Repositories.")


def rewritten(conn, row: dict, e) -> None:
    """Hold the line and raise the alarm, once per rewrite."""
    if row["held_remote"] != e.remote:
        conn["code_repos"].update_one({"_id": row["id"]}, {"$set": {
            "held_remote": e.remote, "status_detail": "GitHub's history was rewritten. Waiting for the founder."}})
        audit.record(conn, None, "code.history_rewritten", row["name"], f"GitHub now at {e.remote[:10]}; kept ours at "
                     f"{row['head_sha'][:10]}")
        notify.send(conn, founders(conn), "code.rewritten", f"GitHub's history for {row['name']} was rewritten",
                    "Someone force-pushed. Nothing was lost: the Terminal kept the real history and stopped following. "
                    "Decide from Codebase > Repositories.", "/console/code/repos", row["id"])
    raise HTTPException(409, {"message": REWRITTEN, "field": "rewritten"})


def backup_daily(conn, row: dict) -> Path | None:
    """Once a day, the whole history into one file that restores without GitHub
    (`git clone <file>`); the newest CODE_BACKUPS_KEEP are kept."""
    if config.CODE_BACKUPS_KEEP <= 0 or row["status"] != "ready":
        return None
    folder = config.CODE_BACKUP_DIR / f"repo-{row['id']}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest = folder / f"{re.sub(r'[^A-Za-z0-9._-]+', '-', row['name'])}-{stamp}.bundle"
    if dest.exists():
        return dest
    with gitops.lock(row["id"]):
        gitops.bundle(row["id"], dest)
    for old in sorted(folder.glob("*.bundle"))[:-config.CODE_BACKUPS_KEEP]:
        old.unlink(missing_ok=True)
    return dest


def backups(row: dict) -> list[dict]:
    folder = config.CODE_BACKUP_DIR / f"repo-{row['id']}"
    if not folder.is_dir():
        return []
    return [{"name": f.name, "size": f.stat().st_size,
             "at": db.iso(datetime.fromtimestamp(f.stat().st_mtime, timezone.utc))}
            for f in sorted(folder.glob("*.bundle"), reverse=True)]


_loop_started = False


def start_sync_loop() -> None:
    global _loop_started
    if _loop_started or config.CODE_SYNC_MIN <= 0:
        return
    _loop_started = True

    def loop():
        while True:
            time.sleep(config.CODE_SYNC_MIN * 60)
            try:
                with db.connect() as conn:
                    for row in [db.strip(r) for r in conn["code_repos"].find({"status": "ready"})]:
                        try:
                            backup_daily(conn, sync(conn, row))
                        except HTTPException:
                            pass                    # already recorded on the repository; the founder sees it
                        except gitops.GitError:
                            log.exception("code backup")
            except Exception:
                log.exception("code sync loop")
    threading.Thread(target=loop, daemon=True, name="code-sync").start()


# ── following the code: grants move when files change ────────────────────────

def remap(conn, repo_id: int, old: str, new: str) -> None:
    changes = gitops.changed(repo_id, old, new)
    if not changes:
        return
    touched = {p for _, p, _ in changes} | {np for _, _, np in changes}
    items = [i for i in (db.strip(r) for r in conn["code_items"].find({"repo_id": repo_id}))
             if i["path"] in touched or i["kind"] == "folder"]
    cache: dict[tuple[str, str], list[str] | None] = {}

    def lines_at(rev: str, path: str):
        if (rev, path) not in cache:
            data = gitops.show(repo_id, rev, path)
            try:
                cache[(rev, path)] = text.Text(data).lines if data is not None else None
            except text.NotText:
                cache[(rev, path)] = None
        return cache[(rev, path)]

    moves = {p: (st, np) for st, p, np in changes}
    now_files = None
    for it in items:
        path, fields = it["path"], {}
        if it["kind"] == "folder":
            if any(st in "DR" and covers(path, p) for st, p, _ in changes) and path:
                now_files = now_files or [p for p, _ in gitops.ls(repo_id, new)]
                fields["missing"] = not any(covers(path, p) for p in now_files)
        elif path in moves:
            st, np = moves[path]
            if st == "D":
                fields["missing"] = True
            else:
                if st == "R":
                    fields["path"] = np
                if it["kind"] == "lines" and not it["missing"]:
                    old_l, new_l = lines_at(old, path), lines_at(new, np)
                    span = text.map_range(old_l, new_l, it["line_start"], it["line_end"]) if old_l and new_l else None
                    if span:
                        fields.update(line_start=span[0], line_end=span[1])
                    else:
                        fields["missing"] = True
                elif it["kind"] == "symbol":
                    new_l = lines_at(new, np)
                    fields["missing"] = not (new_l and text.find_symbol(np, new_l, it["symbol"]))
        if fields:
            conn["code_items"].update_one({"_id": it["id"]}, {"$set": fields})
    renames = [(p, np) for st, p, np in changes if st == "R"]
    for p, np in renames:
        conn["code_owners"].update_many({"repo_id": repo_id, "path": p}, {"$set": {"path": np}})


# ── the folder map ────────────────────────────────────────────────────────────

_tree_cache: dict[tuple[int, str], list[tuple[str, int]]] = {}


def files_at_head(row: dict) -> list[tuple[str, int]]:
    key = (row["id"], row["head_sha"])
    if key not in _tree_cache:
        _tree_cache.clear()
        _tree_cache[key] = gitops.ls(row["id"], row["head_sha"])
    return _tree_cache[key]


def tree(conn, row: dict, v: Viewer) -> list[dict]:
    """[{p: path, s: size, a: full|partial|none, e: can edit, k: protected}].
    Without the map permission, only the files they can open."""
    show_all = v.founder or "code.map" in v.perms or v.read_all
    out = []
    for path, size in files_at_head(row):
        level, edit = v.level_for(path)
        if level == "none" and not show_all:
            continue
        f = {"p": path, "s": size, "a": level, "e": edit}
        if v.guarded(path):
            f["k"] = 1
        out.append(f)
    return out


def exists(row: dict, path: str, folder: bool = False) -> bool:
    files = files_at_head(row)
    if folder:
        return path == "" or any(covers(path, p) for p, _ in files)
    return any(p == path for p, _ in files)


# ── opening a file ────────────────────────────────────────────────────────────

def load(row: dict, path: str, rev: str | None = None) -> text.Text:
    try:
        rev = gitops.safe_rev(rev or row["head_sha"])
    except gitops.GitError:
        raise HTTPException(400, "That isn't a version this server knows.") from None
    size = next((s for p, s in files_at_head(row) if p == path), None) if rev == row["head_sha"] else gitops.size(row["id"], rev, path)
    if size is None:
        raise HTTPException(404, "No such file.")
    if size > config.CODE_MAX_FILE_KB * 1024:
        raise HTTPException(413, f"This file is over {config.CODE_MAX_FILE_KB} KB, so it isn't opened here.")
    data = gitops.show(row["id"], rev, path)
    if data is None:
        raise HTTPException(404, "No such file.")
    try:
        return text.Text(data)
    except text.NotText:
        raise HTTPException(415, "This isn't a text file, so it isn't opened here.") from None


def blocks(n_lines: int, acc) -> list[dict]:
    """Per-line state (0 hidden, 1 read, 2 edit) grouped into runs."""
    state = [1 if acc.read_full else 0] * n_lines
    if acc.edit_full:
        state = [2] * n_lines
    else:
        for s, e, ed in acc.ranges:
            for i in range(s - 1, min(e, n_lines)):
                state[i] = 2 if ed else max(state[i], 1)
    out = []
    for i, st in enumerate(state):
        if out and out[-1]["state"] == st:
            out[-1]["end"] = i + 1
        else:
            out.append({"state": st, "start": i + 1, "end": i + 1})
    return out


def open_file(conn, row: dict, v: Viewer, actor: dict, path: str) -> dict:
    t = load(row, path)
    acc = v.access(path, t.lines)
    if not acc.any:
        raise HTTPException(403, "You don't have access to this file.")
    note_read(conn, actor, "open", path)          # counted before anything is sent
    runs = blocks(len(t.lines), acc)
    out_blocks = []
    for b in runs:
        if b["state"] == 0:
            out_blocks.append({"kind": "hidden", "start": b["start"], "end": b["end"]})
        else:
            out_blocks.append({"kind": "shown", "start": b["start"], "end": b["end"], "editable": b["state"] == 2,
                               "lines": t.lines[b["start"] - 1:b["end"]]})
    _note_view(conn, actor, row, path)
    return {
        "path": path, "head": row["head_sha"], "lines_total": len(t.lines),
        "access": "full" if acc.read_full else "partial", "edit_full": acc.edit_full, "can_edit": acc.can_edit,
        "blocks": out_blocks,
        "symbols": text.symbols(path, t.lines) if acc.read_full else [],
        "role": v.role_for(path),
        "protected": bool(v.guarded(path)),
    }


def _note_view(conn, actor: dict, row: dict, path: str) -> None:
    """Opening code is on the record, once per person per file per day."""
    since = db.iso(datetime.now(timezone.utc) - timedelta(days=1))
    target = f"{row['name']}:{path}"
    if not conn["audit"].find_one({"actor_id": actor["id"], "action": "code.opened", "target": target,
                                   "at": {"$gt": since}}, {"_id": 1}):
        audit.record(conn, actor, "code.opened", target, "", actor["ip"])


def symbols_for(row: dict, path: str) -> list[dict]:
    t = load(row, path)
    return text.symbols(path, t.lines)


# ── the reading alarm ─────────────────────────────────────────────────────────

PAUSED = "Your code access is paused because a lot of code was opened from your account in a short time. " \
         "The founder has been told and can resume it."


def founders(conn) -> list[int]:
    return conn["staff"].distinct("id", {"level": "founder", "status": "active", "is_demo": False})


def note_read(conn, actor: dict, kind: str, path: str = "") -> None:
    """Every file opened and every search, counted per person per hour. Past
    ALERT the founder is told; past PAUSE the codebase closes to that person
    until the founder resumes it. A stolen account or someone copying
    everything looks exactly like this; a normal day doesn't."""
    if actor["level"] == "founder":
        return
    now = datetime.now(timezone.utc)
    rid = db.next_id(conn, "code_reads")
    conn["code_reads"].insert_one({"_id": rid, "staff_id": actor["id"], "kind": kind, "path": path,
                                   "at": db.iso(now)})
    conn["code_reads"].delete_many({"at": {"$lt": db.iso(now - timedelta(days=2))}})
    since = db.iso(now - timedelta(hours=1))
    files = len(conn["code_reads"].distinct("path", {"staff_id": actor["id"], "kind": "open", "at": {"$gt": since}}))
    searches = conn["code_reads"].count_documents({"staff_id": actor["id"], "kind": "search", "at": {"$gt": since}})
    what = f"opened {files} different files" if kind == "open" else f"ran {searches} searches"
    if files >= config.CODE_PAUSE_FILES_HOUR or searches >= config.CODE_PAUSE_SEARCHES_HOUR:
        conn["staff"].update_one({"_id": actor["id"]}, {"$set": {"code_paused": True}})
        audit.record(conn, actor, "code.paused", actor["email"], f"{what} in an hour", actor["ip"])
        notify.send(conn, founders(conn), "code.paused", f"{actor['display_name']}'s code access was paused",
                    f"Their account {what} in the last hour. If that's expected, resume it from Codebase > Repositories.",
                    "/console/code/repos", actor["id"])
        raise HTTPException(403, {"message": PAUSED, "field": "paused"})
    if files >= config.CODE_ALERT_FILES_HOUR or searches >= config.CODE_ALERT_SEARCHES_HOUR:
        if not conn["audit"].find_one({"actor_id": actor["id"], "action": "code.unusual_reading",
                                       "at": {"$gt": since}}, {"_id": 1}):
            audit.record(conn, actor, "code.unusual_reading", actor["email"], f"{what} in an hour", actor["ip"])
            notify.send(conn, founders(conn), "code.unusual", f"{actor['display_name']} is reading a lot of code",
                        f"Their account {what} in the last hour. At {config.CODE_PAUSE_FILES_HOUR} files it pauses by itself.",
                        "/console/audit", actor["id"])


# ── search ────────────────────────────────────────────────────────────────────

def search(conn, row: dict, v: Viewer, actor: dict, q: str) -> dict:
    """Words anywhere in the code, and in file names, as fast as git can read.
    Only lines the person may see come back; each hit says which function,
    class or section it sits in."""
    q = (q or "").strip()
    if len(q) < 2:
        raise HTTPException(400, "Type at least two characters.")
    if len(q) > 100:
        raise HTTPException(400, "That's too long to search for.")
    note_read(conn, actor, "search")
    t0 = time.time()
    raw, more = gitops.grep(row["id"], row["head_sha"], q)
    needle = q.lower()

    levels_seen: dict[str, str] = {}

    def level(p: str) -> str:
        if p not in levels_seen:
            levels_seen[p] = v.level_for(p)[0]
        return levels_seen[p]

    kept = [(p, n, s) for p, n, s in raw if level(p) != "none"]
    # Partial files, and the files whose hits get a function name: one git call.
    wanted = list(dict.fromkeys(p for p, _, _ in kept))[:80]
    blobs = gitops.show_many(row["id"], row["head_sha"], wanted, config.CODE_MAX_FILE_KB * 1024)
    lines_of, visible_of, symbols_of = {}, {}, {}
    for p, data in blobs.items():
        try:
            lines_of[p] = text.Text(data).lines
        except text.NotText:
            continue
        if level(p) == "partial":
            visible_of[p] = v.access(p, lines_of[p]).visible() or set()
        symbols_of[p] = text.symbols(p, lines_of[p])

    hits = []
    for p, n, s in kept:
        if level(p) == "partial" and n not in visible_of.get(p, set()):
            continue
        sym = None
        spans = [x for x in symbols_of.get(p, []) if x["start"] <= n <= x["end"]]
        if spans:
            best = min(spans, key=lambda x: x["end"] - x["start"])
            seen = visible_of.get(p)
            if seen is None or all(k in seen for k in range(best["start"], best["end"] + 1)):
                sym = {"name": best["name"], "kind": best["kind"]}
        hits.append({"path": p, "line": n, "text": s.strip()[:240], "symbol": sym})
        if len(hits) >= 300:
            more = True
            break

    names = []
    for p, _ in files_at_head(row):
        if needle in p.lower():
            lv = level(p)
            if lv != "none" or v.founder or "code.map" in v.perms:
                names.append({"path": p, "access": lv, "protected": bool(v.guarded(p))})
            if len(names) >= 30:
                break
    return {"q": q, "hits": hits, "files": names, "more": more, "ms": int((time.time() - t0) * 1000)}


# ── who was given what ────────────────────────────────────────────────────────

def in_team(conn, lead_id: int, staff_id: int) -> bool:
    seen, cur = set(), staff_id
    for _ in range(12):
        row = conn["staff"].find_one({"_id": cur}, {"reports_to": 1})
        boss = row["reports_to"] if row else None
        if not boss or boss in seen:
            return False
        if boss == lead_id:
            return True
        seen.add(boss)
        cur = boss
    return False


def clean_items(row: dict, raw: list[dict]) -> list[dict]:
    """Validate what's being given against the code as it is now."""
    if not raw:
        raise HTTPException(400, "Pick at least one folder, file, function or set of lines.")
    if len(raw) > 200:
        raise HTTPException(400, "That's too many items for one go.")
    out = []
    for it in raw:
        kind, path = it.get("kind"), (it.get("path") or "").strip().strip("/")
        if kind == "folder":
            if not exists(row, path, folder=True):
                raise HTTPException(400, f"There's no folder {path or '(everything)'}.")
            out.append({"kind": "folder", "path": path})
            continue
        if kind not in ("file", "lines", "symbol") or not exists(row, path):
            raise HTTPException(400, f"There's no file {path}.")
        if kind == "file":
            out.append({"kind": "file", "path": path})
        elif kind == "lines":
            t = load(row, path)
            s, e = int(it.get("line_start") or 0), int(it.get("line_end") or 0)
            if not (1 <= s <= e <= len(t.lines)):
                raise HTTPException(400, f"{path} has lines 1 to {len(t.lines)}.")
            out.append({"kind": "lines", "path": path, "line_start": s, "line_end": e})
        else:
            name = (it.get("symbol") or "").strip()
            if not name or not text.find_symbol(path, load(row, path).lines, name):
                raise HTTPException(400, f"There's no function, class, section or setting called {name} in {path}.")
            out.append({"kind": "symbol", "path": path, "symbol": name})
    return out


def check_grant_power(conn, v: Viewer, items: list[dict], target: dict, can_edit: bool) -> None:
    """You can only give what you have: owners give in what they own (edit
    too), reviewers give read-only to their own team, `code.grant_all`
    gives anywhere. Always to someone below you."""
    if target["level"] == "founder" or not (v.founder or levels.outranks(v.level, target["level"])):
        raise HTTPException(403, "You can only give access to people below your level.")
    founder_only_inside_protection(v, items, "gives access to")
    if v.founder or "code.grant_all" in v.perms:
        return
    if "code.grant" not in v.perms:
        raise HTTPException(403, "Your level doesn't include giving access.")
    for it in items:
        role = v.role_for(it["path"])
        if role == "owner":
            continue
        if role == "reviewer" and not can_edit and in_team(conn, v.id, target["id"]):
            continue
        what = it["path"] or "everything"
        raise HTTPException(403, f"You can't give access to {what}: " + (
            "reviewers give read-only access, to their own team." if role == "reviewer" else "you don't own it."))


def founder_only_inside_protection(v: Viewer, items: list[dict], verb: str) -> None:
    """Anything placed inside a protected area (a grant, an owner, a feature
    item) is the founder's call alone. Something wider, like the whole `core`
    folder, is fine: it simply stops at the protected edge."""
    if v.founder:
        return
    inside = next((it["path"] for it in items if v.guarded(it["path"])), None)
    if inside is not None:
        raise HTTPException(403, f"{inside} is protected. Only the founder {verb} protected code.")


def target_person(conn, staff_id: int) -> dict:
    t = db.strip(conn["staff"].find_one({"_id": staff_id}))
    if not t or t["status"] != "active":
        raise HTTPException(400, "They must be an active team member.")
    return t


def describe(item: dict) -> str:
    if item["kind"] == "folder":
        return f"{item['path'] or 'everything'}/" if item["path"] else "everything"
    if item["kind"] == "file":
        return item["path"]
    if item["kind"] == "lines":
        return f"{item['path']} lines {item['line_start']}-{item['line_end']}"
    return f"{item['symbol']} in {item['path']}"


def add_items(conn, repo_id: int, items: list[dict], *, grant_id=None, feature_id=None) -> None:
    if not items:
        return
    ids = db.next_ids(conn, "code_items", len(items))
    conn["code_items"].insert_many([
        {"_id": iid, "id": iid, "repo_id": repo_id, "feature_id": feature_id, "grant_id": grant_id,
         "kind": it["kind"], "path": it["path"], "line_start": it.get("line_start"), "line_end": it.get("line_end"),
         "symbol": it.get("symbol", ""), "missing": False}
        for iid, it in zip(ids, items)])


def items_of(conn, *, grant_id=None, feature_id=None) -> list[dict]:
    filt = {"grant_id": grant_id} if grant_id else {"feature_id": feature_id}
    rows = [db.strip(r) for r in conn["code_items"].find(filt).sort([("path", 1), ("line_start", 1)])]
    return [{"id": r["id"], "kind": r["kind"], "path": r["path"], "line_start": r["line_start"],
             "line_end": r["line_end"], "symbol": r["symbol"], "missing": bool(r["missing"]),
             "label": describe(r)} for r in rows]


def access_overview(conn, row: dict, v: Viewer) -> dict:
    """Grants, features and owners, trimmed to what this person may see."""
    see_all = v.founder or bool({"code.access_view", "code.grant_all", "code.owners", "code.revoke"} & v.perms)
    names = {r["id"]: r for r in conn["staff"].find({}, {"id": 1, "display_name": 1, "level": 1, "title": 1})}

    def person(i):
        r = names.get(i)
        return {"id": i, "name": r["display_name"], "level": r["level"], "level_label": levels.LABEL[r["level"]],
                "title": r["title"]} if r else {"id": i, "name": "someone removed", "level": "", "level_label": "", "title": ""}

    features = {f["id"]: db.strip(f) for f in conn["code_features"].find({"repo_id": row["id"]}).sort("name", 1)}
    grants = []
    for g in (db.strip(r) for r in conn["code_grants"].find({"repo_id": row["id"]}).sort("granted_at", -1)):
        if not (see_all or g["granted_by"] == v.id or g["staff_id"] == v.id or in_team(conn, v.id, g["staff_id"])):
            continue
        expired = bool(g["expires_at"] and g["expires_at"] <= db.now_iso())
        grants.append({"id": g["id"], "person": person(g["staff_id"]), "by": person(g["granted_by"]) if g["granted_by"] else None,
                       "at": g["granted_at"], "can_edit": bool(g["can_edit"]), "expires_at": g["expires_at"],
                       "expired": expired, "note": g["note"],
                       "feature": ({"id": g["feature_id"], "name": features[g["feature_id"]]["name"]}
                                   if g["feature_id"] in features else None),
                       "items": items_of(conn, feature_id=g["feature_id"]) if g["feature_id"] else items_of(conn, grant_id=g["id"])})
    owners = [{"id": o["id"], "person": person(o["staff_id"]), "role": o["role"], "path": o["path"],
               "feature": {"id": o["feature_id"], "name": features[o["feature_id"]]["name"]} if o["feature_id"] in features else None,
               "at": o["added_at"]}
              for o in (db.strip(r) for r in conn["code_owners"].find({"repo_id": row["id"]}).sort([("path", 1), ("role", 1)]))]
    return {
        "grants": grants,
        "owners": owners,
        "features": [{"id": f["id"], "name": f["name"], "description": f["description"],
                      "items": items_of(conn, feature_id=f["id"]),
                      "grants": sum(1 for g in grants if g["feature"] and g["feature"]["id"] == f["id"])}
                     for f in features.values()],
        "can": {"grant": v.founder or bool({"code.grant", "code.grant_all"} & v.perms),
                "grant_all": v.founder or "code.grant_all" in v.perms,
                "owners": v.founder or "code.owners" in v.perms,
                "features": v.founder or bool({"code.grant_all", "code.owners"} & v.perms),
                "revoke": v.founder or "code.revoke" in v.perms},
        "see_all": see_all,
    }


OWNER_MIN = {"owner": "director", "reviewer": "manager"}


def check_owner_target(v: Viewer, target: dict, role: str) -> None:
    if role not in OWNER_MIN:
        raise HTTPException(400, "Role is owner or reviewer.")
    if levels.RANK[target["level"]] < levels.RANK[OWNER_MIN[role]]:
        raise HTTPException(400, f"A{'n' if role == 'owner' else ''} {role} must be a {levels.LABEL[OWNER_MIN[role]]} or above.")
    if target["id"] != v.id and target["level"] != "founder" and not (v.founder or levels.outranks(v.level, target["level"])):
        raise HTTPException(403, "You can only choose people below your level (or yourself).")
    if target["level"] == "founder" and not v.founder:
        raise HTTPException(403, "Only the founder chooses what the founder owns.")
