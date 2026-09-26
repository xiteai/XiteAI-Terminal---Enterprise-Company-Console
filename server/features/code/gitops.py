"""The server's copy of a repository, driven through the git command line.

GitHub is the master copy. This clone follows it (fetch + fast-forward), and
an approved change is committed here under its author's name and pushed.
The GitHub token never touches disk and never appears on a command line (any
user on the machine can list those): it rides in the git process's own
environment (GIT_CONFIG_COUNT/KEY/VALUE), readable only by this user.
Every command for one repository runs under that repository's lock."""
from __future__ import annotations

import base64
import os
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import psutil

from ...core import config

_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


class GitError(Exception):
    pass


# ── live progress while cloning, and cancelling it ────────────────────────────
# git prints its progress as a percentage, redrawing the same terminal line
# with \r — read raw and split on \r or \n to catch every update, not just the
# handful of lines that end in \n. Kept in memory only (repo_card() reads it
# while status is "cloning"): nothing here needs to survive a restart.
_progress: dict[int, dict] = {}
_progress_guard = threading.Lock()
_procs: dict[int, subprocess.Popen] = {}
_procs_guard = threading.Lock()
_PCT = re.compile(r"(\d+)%")


def _phase_of(line: str) -> str:
    """'remote: Counting objects: 100% (...)' -> 'Counting objects', not just
    'remote' (github reports its own-side steps with that prefix first)."""
    line = line.removeprefix("remote:").strip()
    return line.split(":")[0].strip() if ":" in line else line


def _report(repo_id: int, line: str) -> None:
    m = _PCT.search(line)
    with _progress_guard:
        p = _progress.setdefault(repo_id, {"started": time.time(), "pct": None})
        p["note"] = line
        p["phase"] = _phase_of(line)
        if m:
            p["pct"] = int(m.group(1))


def progress(repo_id: int) -> dict | None:
    """What a repository's clone is doing right now, for the progress bar —
    None once it's finished (or never started)."""
    with _progress_guard:
        p = _progress.get(repo_id)
        return {**p, "elapsed_s": round(time.time() - p["started"], 1)} if p else None


def _clear_progress(repo_id: int) -> None:
    with _progress_guard:
        _progress.pop(repo_id, None)


CLONE_SILENT_S = 120          # no output at all from git for this long: it's hung, not slow
CLONE_MAX_S = 1800            # the whole copy, however much output it gives


def _kill_tree(proc: subprocess.Popen) -> None:
    """git spawns a helper for the network transfer (on Windows a separate
    git-remote-https.exe); killing only the git.exe we started leaves that
    helper running and holding the files about to be deleted. Kill the whole
    tree, children first."""
    try:
        parent = psutil.Process(proc.pid)
        family = parent.children(recursive=True) + [parent]
    except psutil.Error:
        family = []
    for p in family:
        try:
            p.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(family, timeout=5)
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def cancel(repo_id: int) -> bool:
    """Stop a clone in progress. True if there was one running to stop."""
    with _procs_guard:
        proc = _procs.get(repo_id)
    if not proc or proc.poll() is not None:
        return False
    _kill_tree(proc)
    return True


def kill_orphans(repo_id: int) -> int:
    """git processes still writing into this repository's folder with nobody
    watching them (the server that started them restarted mid-copy). They'd
    hold the folder and block a fresh copy. Returns how many were stopped."""
    target = str(repo_dir(repo_id)).lower()
    stopped = 0
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower().startswith("git") and \
                    target in " ".join(p.info["cmdline"] or []).lower():
                p.kill()
                stopped += 1
        except psutil.Error:
            pass
    return stopped


_SHA = re.compile(r"^[0-9a-f]{7,64}$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,48}$")


def safe_rev(rev: str) -> str:
    """Every version name that reaches git comes from here. A value like
    `--output=/some/file` would otherwise be read by git as an OPTION (and
    `git show --output` writes files): only HEAD, a commit id, or a
    checkpoint-style tag name is let through."""
    rev = (rev or "").strip()
    if rev == "HEAD" or _SHA.match(rev) or (_TAG.match(rev) and ".." not in rev):
        return rev
    raise GitError("That isn't a version this server knows.")


def lock(repo_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(repo_id, threading.Lock())


def repo_dir(repo_id: int) -> Path:
    return config.CODE_DIR / f"repo-{repo_id}"


def remove(repo_id: int) -> None:
    """Delete the server's copy. Git marks its object files read-only, which
    Windows refuses to delete until the flag is cleared."""
    def clear_and_retry(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    d = repo_dir(repo_id)
    if d.exists():
        shutil.rmtree(d, onexc=clear_and_retry)


def _basic() -> str:
    return base64.b64encode(f"x-access-token:{config.GITHUB_TOKEN}".encode()).decode()


def _env(url: str) -> dict:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", LC_ALL="C")
    for k in [k for k in env if k.startswith("GIT_CONFIG_")]:
        env.pop(k)
    if config.GITHUB_TOKEN and url.startswith("https://"):
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.extraHeader",
                   GIT_CONFIG_VALUE_0=f"Authorization: Basic {_basic()}")
    return env


def _clean_error(text: str) -> str:
    text = (text or "").strip()
    if config.GITHUB_TOKEN:
        text = text.replace(config.GITHUB_TOKEN, "***").replace(_basic(), "***")
    return text.splitlines()[-1][:300] if text else "git failed."


def run(args: list[str], cwd: Path | None = None, url: str = "", check: bool = True,
        input_bytes: bytes | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
    env = _env(url)
    cmd = ["git", "-c", "core.autocrlf=false", "-c", "core.quotepath=false", *args]
    # git never reads this server's stdin. Left inherited, it's a pipe a server
    # thread is blocked reading (serving.py), and on Windows a process that so
    # much as queries such a handle hangs forever: this froze every clone.
    feed = {"input": input_bytes} if input_bytes is not None else {"stdin": subprocess.DEVNULL}
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=timeout, **feed)
    except FileNotFoundError:
        raise GitError("git isn't installed on this server.") from None
    except subprocess.TimeoutExpired:
        raise GitError("git took too long and was stopped.") from None
    if check and p.returncode != 0:
        raise GitError(_clean_error(p.stderr.decode("utf-8", "replace") or p.stdout.decode("utf-8", "replace")))
    return p


def out(args: list[str], cwd: Path | None, url: str = "") -> str:
    return run(args, cwd=cwd, url=url).stdout.decode("utf-8", "replace").strip()


# ── clone and follow ──────────────────────────────────────────────────────────

def default_branch(url: str) -> str | None:
    """What GitHub calls this repository's default branch, without cloning it —
    so 'Connect' never has to guess main vs. master vs. something else."""
    try:
        out_text = out(["ls-remote", "--symref", url, "HEAD"], cwd=None, url=url)
    except GitError:
        return None
    m = re.search(r"^ref:\s+refs/heads/(\S+)\s+HEAD$", out_text, re.MULTILINE)
    return m.group(1) if m else None


def branches(url: str) -> list[str]:
    """Every branch name GitHub actually has, for a clearer error than 'not found'."""
    try:
        out_text = out(["ls-remote", "--heads", url], cwd=None, url=url)
    except GitError:
        return []
    names = []
    for line in out_text.splitlines():
        _, _, name = line.partition("refs/heads/")
        if name:
            names.append(name)
    return names


def clone(repo_id: int, url: str, branch: str) -> str:
    """Fresh clone into the repository's folder (a full clone: a partial one
    makes git fetch skipped blobs behind our back whenever it lists sizes).
    Streams git's own progress into `progress(repo_id)` as it runs, and can be
    stopped mid-way with `cancel(repo_id)`."""
    dest = repo_dir(repo_id)
    if dest.exists():
        raise GitError("That folder already exists on the server.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "-c", "core.autocrlf=false", "-c", "core.quotepath=false", "clone", "--branch", branch,
          "--single-branch", "--no-tags", "--progress", url, str(dest)]
    with _progress_guard:                       # the timer runs from the click, not from git's first line
        _progress[repo_id] = {"started": time.time(), "pct": None, "phase": "Cloning into", "note": ""}
    try:
        proc = subprocess.Popen(cmd, env=_env(url), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
    except FileNotFoundError:
        _clear_progress(repo_id)
        raise GitError("git isn't installed on this server.") from None
    with _procs_guard:
        _procs[repo_id] = proc

    # The watchdog: git can hang without printing anything, and a read that
    # never returns never gets to check a deadline. This thread does, and
    # kills git (which ends the read) on silence or on the overall limit.
    last_output = [time.time()]
    stopped_by: list[str] = []
    started = time.time()

    def watch() -> None:
        while proc.poll() is None:
            now = time.time()
            if now - last_output[0] > CLONE_SILENT_S:
                stopped_by.append(f"GitHub stopped responding for {CLONE_SILENT_S} seconds, so the copy was stopped. "
                                  "Try again.")
            elif now - started > CLONE_MAX_S:
                stopped_by.append("The copy took longer than 30 minutes and was stopped.")
            if stopped_by:
                _kill_tree(proc)
                return
            time.sleep(1)
    threading.Thread(target=watch, daemon=True, name=f"clone-watch-{repo_id}").start()

    tail: list[str] = []
    buf = b""
    try:
        while True:
            chunk = proc.stderr.read1(4096)     # whatever has arrived, now: progress in real time
            if not chunk:
                break
            last_output[0] = time.time()
            buf += chunk
            while b"\r" in buf or b"\n" in buf:
                cut = min(i for i in (buf.find(b"\r"), buf.find(b"\n")) if i != -1)
                line, buf = buf[:cut].decode("utf-8", "replace").strip(), buf[cut + 1:]
                if line:
                    tail.append(line)
                    del tail[:-40]
                    _report(repo_id, line)
        proc.wait(timeout=30)
    finally:
        proc.stderr.close()
        with _procs_guard:
            _procs.pop(repo_id, None)
        _clear_progress(repo_id)
    if stopped_by:
        remove(repo_id)
        raise GitError(stopped_by[0])
    if proc.returncode != 0:
        cleaned = _clean_error("\n".join(tail[-30:]))
        if "remote branch" in cleaned.lower() and "not found" in cleaned.lower():
            have = branches(url)
            hint = f" This repository's branches are: {', '.join(have[:8])}." if have else ""
            raise GitError(f"There's no branch called \"{branch}\" on GitHub.{hint}")
        raise GitError(cleaned)
    run(["config", "core.autocrlf", "false"], cwd=dest)
    return head(repo_id)


def head(repo_id: int) -> str:
    return out(["rev-parse", "HEAD"], repo_dir(repo_id))


class HistoryRewritten(GitError):
    """GitHub's branch no longer contains history it had at the last sync:
    someone force-pushed, by mistake or on purpose."""

    def __init__(self, remote: str):
        super().__init__("GitHub's history was rewritten (someone force-pushed). The Terminal kept the real "
                         "history and didn't follow.")
        self.remote = remote


def sync(repo_id: int, url: str, branch: str, last_remote: str = "") -> tuple[str, str, str]:
    """Bring the clone level with GitHub. Returns (old head, new head, GitHub's head).

    THE HISTORY GUARD: if GitHub's branch no longer contains what it had at the
    last sync (`last_remote`), its history was rewritten. Nothing here moves,
    what we had is pinned under refs/terminal/kept/, and HistoryRewritten is
    raised for the founder to decide. A plain fetch-and-reset would quietly
    follow an attacker's force-push and lose the real history.

    Local commits GitHub doesn't have yet (a push that failed) are replayed on
    top and pushed; if they can't be replayed cleanly, nothing is changed."""
    d = repo_dir(repo_id)
    old = head(repo_id)
    run(["fetch", "--no-tags", "origin", branch], cwd=d, url=url)
    remote_ref = f"origin/{branch}"
    remote = out(["rev-parse", remote_ref], d)
    if last_remote and remote != last_remote and not is_ancestor(repo_id, last_remote, remote):
        keep(repo_id, old, "rewrite")
        raise HistoryRewritten(remote)
    ahead = int(out(["rev-list", "--count", f"{remote_ref}..HEAD"], d) or 0)
    if ahead == 0:
        run(["reset", "--hard", remote_ref], cwd=d)
    else:
        p = run(["rebase", remote_ref], cwd=d, check=False)
        if p.returncode != 0:
            run(["rebase", "--abort"], cwd=d, check=False)
            raise GitError("Changes merged here conflict with new commits on GitHub. Someone needs to resolve them by hand.")
        run(["push", "origin", f"HEAD:{branch}"], cwd=d, url=url)
        remote = head(repo_id)
    return old, head(repo_id), remote


def is_ancestor(repo_id: int, a: str, b: str) -> bool:
    return run(["merge-base", "--is-ancestor", safe_rev(a), safe_rev(b)], cwd=repo_dir(repo_id),
               check=False).returncode == 0


def keep(repo_id: int, sha: str, why: str) -> str:
    """Pin `sha`, and all the history behind it, so git never throws it away."""
    ref = f"refs/terminal/kept/{why}-{time.strftime('%Y%m%d-%H%M%S')}"
    run(["update-ref", ref, sha], cwd=repo_dir(repo_id))
    return ref


def accept_remote(repo_id: int, url: str, branch: str) -> tuple[str, str]:
    """After a rewrite, the founder's first choice: follow GitHub's new history
    (what we had stays pinned). Returns (old head, new head)."""
    d = repo_dir(repo_id)
    old = head(repo_id)
    run(["fetch", "--no-tags", "origin", branch], cwd=d, url=url)
    keep(repo_id, old, "before-accept")
    run(["reset", "--hard", f"origin/{branch}"], cwd=d)
    return old, head(repo_id)


def put_back(repo_id: int, url: str, branch: str, expected_remote: str) -> str:
    """After a rewrite, the other choice: put the real history back on GitHub.
    Only if GitHub still holds exactly the rewritten head we saw, so a second
    push in between is never overwritten blind."""
    d = repo_dir(repo_id)
    run(["push", f"--force-with-lease={branch}:{safe_rev(expected_remote)}", "origin", f"HEAD:{branch}"], cwd=d, url=url)
    return head(repo_id)


# ── reading ───────────────────────────────────────────────────────────────────

def ls(repo_id: int, rev: str = "HEAD") -> list[tuple[str, int]]:
    """Every file at `rev` with its size in bytes: [(path, size)]."""
    raw = run(["ls-tree", "-r", "-l", "-z", safe_rev(rev)], cwd=repo_dir(repo_id)).stdout.decode("utf-8", "replace")
    files = []
    for entry in filter(None, raw.split("\0")):
        meta, path = entry.split("\t", 1)
        parts = meta.split()
        if parts[1] != "blob":
            continue
        files.append((path, int(parts[3]) if parts[3].isdigit() else 0))
    return files


def show(repo_id: int, rev: str, path: str) -> bytes | None:
    # `cat-file blob`, not `show`: plumbing that prints exactly the file, with no
    # options worth abusing even if a check upstream ever slipped.
    p = run(["cat-file", "blob", f"{safe_rev(rev)}:{path}"], cwd=repo_dir(repo_id), check=False)
    return p.stdout if p.returncode == 0 else None


def show_many(repo_id: int, rev: str, paths: list[str], max_bytes: int) -> dict[str, bytes]:
    """Several files at `rev` through one git process (`cat-file --batch`),
    skipping any over `max_bytes`: {path: bytes}."""
    if not paths:
        return {}
    rev = safe_rev(rev)
    paths = [p for p in paths if "\n" not in p]              # one request line per path, or answers misalign
    request = "".join(f"{rev}:{p}\n" for p in paths).encode("utf-8")
    raw = run(["cat-file", "--batch"], cwd=repo_dir(repo_id), input_bytes=request, check=False).stdout
    out, pos = {}, 0
    for p in paths:
        nl = raw.find(b"\n", pos)
        if nl < 0:
            break
        header = raw[pos:nl].split()
        pos = nl + 1
        if len(header) < 3:                                   # "<rev:path> missing": no content follows
            continue
        n = int(header[2])
        if header[1] == b"blob" and n <= max_bytes:
            out[p] = raw[pos:pos + n]
        pos += n + 1                                          # any content (even a tree's), then its newline
    return out


def size(repo_id: int, rev: str, path: str) -> int | None:
    p = run(["cat-file", "-s", f"{safe_rev(rev)}:{path}"], cwd=repo_dir(repo_id), check=False)
    return int(p.stdout.strip()) if p.returncode == 0 else None


def changed(repo_id: int, old: str, new: str) -> list[tuple[str, str, str]]:
    """[(status, path, new_path)] between two commits, renames detected.
    status: M modified, A added, D deleted, R renamed."""
    raw = run(["diff", "--name-status", "-M", "-z", safe_rev(old), safe_rev(new), "--"],
              cwd=repo_dir(repo_id)).stdout.decode("utf-8", "replace")
    parts = [p for p in raw.split("\0") if p]
    items, i = [], 0
    while i < len(parts):
        st = parts[i][0]
        if st == "R":
            items.append(("R", parts[i + 1], parts[i + 2]))
            i += 3
        else:
            items.append((st, parts[i + 1], parts[i + 1]))
            i += 2
    return items


def grep(repo_id: int, rev: str, needle: str, cap: int = 3000) -> tuple[list[tuple[str, int, str]], bool]:
    """Case-insensitive plain-text search of every text file at `rev`:
    ([(path, line, text)], more?). Streams, and stops reading at `cap` hits,
    so a common word costs the same as a rare one."""
    rev = safe_rev(rev)
    cmd = ["git", "-c", "core.quotepath=false", "grep", "-I", "-n", "-i", "-F", "-z", "--full-name",
           "-e", needle, rev, "--"]
    prefix = f"{rev}:"
    hits, more = [], False
    try:
        p = subprocess.Popen(cmd, cwd=repo_dir(repo_id), env=_env(""), stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise GitError("git isn't installed on this server.") from None
    try:
        for raw in p.stdout:
            parts = raw.rstrip(b"\r\n").split(b"\0", 2)
            if len(parts) != 3:
                continue
            path = parts[0].decode("utf-8", "replace")
            if path.startswith(prefix):
                path = path[len(prefix):]
            try:
                hits.append((path, int(parts[1]), parts[2].decode("utf-8", "replace")))
            except ValueError:
                continue
            if len(hits) >= cap:
                more = True
                break
    finally:
        p.kill() if p.poll() is None else None
        p.stdout.close()
        p.wait()
    return hits, more


# ── history ───────────────────────────────────────────────────────────────────

_REC, _FLD = "\x1e", "\x1f"


def log(repo_id: int, rev: str = "HEAD", path: str | None = None, limit: int = 50, skip: int = 0) -> list[dict]:
    """Commits, newest first: [{sha, parents, author, email, at, subject, body,
    files: [(status, path, new_path)]}]. With `path`, that file's history,
    followed across renames."""
    fmt = "--format=%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1f"     # git writes the separators itself
    args = ["log", fmt, "--name-status", "-M", f"-n{int(limit)}", f"--skip={int(skip)}", safe_rev(rev)]
    if path:
        args += ["--follow", "--", path]
    else:
        args += ["--"]
    raw = run(args, cwd=repo_dir(repo_id), check=False).stdout.decode("utf-8", "replace")
    out_ = []
    for chunk in raw.split(_REC)[1:]:
        f = chunk.split(_FLD)
        if len(f) < 8:
            continue
        files = []
        for line in f[7].splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0]:
                st = parts[0][0]
                files.append((st, parts[1], parts[2] if st in "RC" and len(parts) > 2 else parts[1]))
        out_.append({"sha": f[0], "parents": f[1].split(), "author": f[2], "email": f[3], "at": f[4],
                     "subject": f[5], "body": f[6].strip(), "files": files})
    return out_


def blame(repo_id: int, rev: str, path: str) -> list[dict]:
    """Who last changed each line: one entry per line, in order:
    {sha, author, at (unix seconds), summary}."""
    raw = run(["blame", "--porcelain", safe_rev(rev), "--", path], cwd=repo_dir(repo_id), check=False).stdout
    commits: dict[str, dict] = {}
    lines, cur = [], None
    for ln in raw.decode("utf-8", "replace").split("\n"):
        if ln.startswith("\t"):
            if cur:
                lines.append({"sha": cur, **commits.get(cur, {})})
            continue
        parts = ln.split(" ")
        if len(parts[0]) == 40 and len(parts) >= 3 and all(c in "0123456789abcdef" for c in parts[0]):
            cur = parts[0]
            commits.setdefault(cur, {})
        elif cur and parts[0] in ("author", "author-time", "summary"):
            key = {"author": "author", "author-time": "at", "summary": "summary"}[parts[0]]
            value = ln[len(parts[0]) + 1:]
            commits[cur][key] = int(value) if key == "at" and value.isdigit() else value
    # porcelain states a commit's details only the first time it appears
    return [{**ln, **commits.get(ln["sha"], {})} for ln in lines]


def tags(repo_id: int) -> dict[str, str]:
    """{commit sha: tag name} for every tag (annotated tags point at their commit)."""
    raw = out(["for-each-ref", "refs/tags", "--format=%(refname:short)%09%(objectname)%09%(*objectname)"],
              repo_dir(repo_id))
    found = {}
    for line in raw.splitlines():
        name, obj, peeled = (line.split("\t") + ["", ""])[:3]
        found[peeled or obj] = name
    return found


def make_tag(repo_id: int, name: str, message: str, author: str, email: str) -> str:
    if not _TAG.match(name) or ".." in name:
        raise GitError("A checkpoint name is letters, numbers, dots, dashes and underscores.")
    run(["-c", f"user.name={author}", "-c", f"user.email={email}", "tag", "-a", name, "-m", message, "HEAD"],
        cwd=repo_dir(repo_id))
    return head(repo_id)


def push_tag(repo_id: int, url: str, name: str) -> None:
    if not _TAG.match(name):
        raise GitError("That isn't a checkpoint name.")
    run(["push", "origin", f"refs/tags/{name}"], cwd=repo_dir(repo_id), url=url)


def bundle(repo_id: int, dest: Path) -> int:
    """The whole history, every branch, tag and pinned ref, in one file that
    `git clone` can restore from without GitHub."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    run(["bundle", "create", str(tmp), "--all"], cwd=repo_dir(repo_id), timeout=1800)
    os.replace(tmp, dest)
    return dest.stat().st_size


# ── writing ───────────────────────────────────────────────────────────────────

def merge_file(current: bytes, base: bytes, theirs: bytes) -> tuple[bytes, bool]:
    """Three-way merge of one file. (merged bytes, clean?)."""
    with tempfile.TemporaryDirectory() as td:
        paths = []
        for name, data in (("current", current), ("base", base), ("theirs", theirs)):
            p = Path(td) / name
            p.write_bytes(data)
            paths.append(str(p))
        p = run(["merge-file", "-p", *paths], check=False)
        return p.stdout, p.returncode == 0


def commit(repo_id: int, files: dict[str, bytes | None], author: str, email: str, message: str) -> str:
    """Write (or delete, for None) each file, commit as the author, return the sha."""
    d = repo_dir(repo_id)
    for rel, data in files.items():
        target = (d / rel).resolve()
        if not target.is_relative_to(d.resolve()) or ".git" in Path(rel).parts:
            raise GitError(f"Refused a path outside the repository: {rel}")
        if data is None:
            run(["rm", "-q", "--", rel], cwd=d)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            run(["add", "--", rel], cwd=d)
    run(["-c", f"user.name={config.CODE_COMMITTER_NAME}", "-c", f"user.email={config.CODE_COMMITTER_EMAIL}",
         "commit", "-q", f"--author={author} <{email}>", "-F", "-"], cwd=d, input_bytes=message.encode("utf-8"))
    return head(repo_id)


def push(repo_id: int, url: str, branch: str) -> None:
    run(["push", "origin", f"HEAD:{branch}"], cwd=repo_dir(repo_id), url=url)


def undo_last(repo_id: int, to_sha: str) -> None:
    run(["reset", "--hard", to_sha], cwd=repo_dir(repo_id))
