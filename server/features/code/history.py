"""History: every change that reached the code, from here or straight to
GitHub, in plain words, trimmed to what each person may see.

The rule is the same one the change requests follow: a file's contents (its
diff, its old versions) are shown only to someone who can read the whole
file today. Someone who was given a few lines sees who changed those lines,
nothing more."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from ...core import config, db
from . import gitops, service, store, text
from .access import Viewer


def _rev(value: str) -> str:
    try:
        return gitops.safe_rev(value)
    except gitops.GitError:
        raise HTTPException(400, "That isn't a version this server knows.") from None


def _links(row: dict) -> tuple[dict, dict]:
    """{sha: change request} and {sha: checkpoint name}."""
    changes = {r["merged_sha"]: {"id": r["id"], "title": r["title"]}
               for r in store.rows("SELECT id, title, merged_sha FROM code_changes WHERE repo_id = ? AND merged_sha != ''",
                                   (row["id"],))}
    return changes, gitops.tags(row["id"])


def _can_read_whole(v: Viewer, path: str) -> bool:
    return v.level_for(path)[0] == "full"


def timeline(row: dict, v: Viewer, path: str | None = None, skip: int = 0, limit: int = 40) -> dict:
    """Newest first. The repository's history shows a commit if at least one of
    its files is readable in full; a file's history needs that file."""
    if path is not None and not _can_read_whole(v, path):
        raise HTTPException(403, "A file's history is open to people who can read the whole file.")
    raw = gitops.log(row["id"], row["head_sha"], path=path, limit=limit, skip=skip)
    changes, checkpoints = _links(row)
    out = []
    for c in raw:
        shown, hidden = [], 0
        for st, p, np in c["files"]:
            if _can_read_whole(v, np) or (st == "D" and _can_read_whole(v, p)):
                shown.append({"status": st, "path": np, "from": p if st in "RC" else None})
            else:
                hidden += 1
        if not shown and c["files"]:
            continue
        out.append({"sha": c["sha"], "short": c["sha"][:8], "author": c["author"], "at": c["at"],
                    "subject": c["subject"], "body": c["body"][:2000], "files": shown, "hidden_files": hidden,
                    "change": changes.get(c["sha"]), "checkpoint": checkpoints.get(c["sha"])})
    return {"commits": out, "more": len(raw) == limit, "next": skip + limit}


def _diffs(row: dict, v: Viewer, before_rev: str | None, after_rev: str, files: list[tuple[str, str, str]]) -> list[dict]:
    """Per-file hunks between two versions, for the files this viewer may read."""
    readable = [(st, p, np) for st, p, np in files if _can_read_whole(v, np) or (st == "D" and _can_read_whole(v, p))]
    cap = config.CODE_MAX_FILE_KB * 1024
    before = gitops.show_many(row["id"], before_rev, [p for st, p, _ in readable if st != "A"], cap) if before_rev else {}
    after = gitops.show_many(row["id"], after_rev, [np for st, _, np in readable if st != "D"], cap)
    out = []
    for st, p, np in readable[:80]:
        entry = {"status": st, "path": np, "from": p if st in "RC" else None}
        try:
            old = text.Text(before[p]).lines if st != "A" and p in before else []
            new = text.Text(after[np]).lines if st != "D" and np in after else []
            entry["hunks"] = text.hunks(old, new, 3)
            entry["added"], entry["removed"] = text.stats(old, new)
        except text.NotText:
            entry["binary"] = True
        out.append(entry)
    hidden = len(files) - len(readable)
    if hidden:
        out.append({"hidden_count": hidden})
    return out


def commit(row: dict, v: Viewer, sha: str) -> dict:
    sha = _rev(sha)
    found = gitops.log(row["id"], sha, limit=1)
    if not found:
        raise HTTPException(404, "No such change in this repository's history.")
    c = found[0]
    if not gitops.is_ancestor(row["id"], c["sha"], row["head_sha"]):
        raise HTTPException(404, "No such change in this repository's history.")
    files = _diffs(row, v, c["parents"][0] if c["parents"] else None, c["sha"], c["files"])
    if not any("hunks" in f or "binary" in f for f in files) and c["files"]:
        raise HTTPException(403, "None of the files in this change are shared with you.")
    changes, checkpoints = _links(row)
    return {"sha": c["sha"], "short": c["sha"][:8], "author": c["author"], "at": c["at"], "subject": c["subject"],
            "body": c["body"], "files": files, "change": changes.get(c["sha"]), "checkpoint": checkpoints.get(c["sha"]),
            "can_undo": bool(c["parents"]) and (v.founder or "code.request" in v.perms)}


def compare(row: dict, v: Viewer, base: str, target: str = "HEAD") -> dict:
    """Everything that changed between two versions (a checkpoint and now, say)."""
    base, target = _rev(base), _rev(target if target != "HEAD" else row["head_sha"])
    files = gitops.changed(row["id"], base, target)
    return {"base": base, "target": target, "files": _diffs(row, v, base, target, files), "count": len(files)}


def blame(row: dict, v: Viewer, path: str) -> dict:
    """Who last changed each line, in runs of lines; only lines they may see."""
    level = v.level_for(path)[0]
    if level == "none":
        raise HTTPException(403, "You don't have access to this file.")
    t = service.load(row, path)
    visible = None if level == "full" else (v.access(path, t.lines).visible() or set())
    changes, _ = _links(row)
    runs = []
    for n, ln in enumerate(gitops.blame(row["id"], row["head_sha"], path), start=1):
        if visible is not None and n not in visible:
            continue
        if runs and runs[-1]["sha"] == ln["sha"] and runs[-1]["end"] == n - 1:
            runs[-1]["end"] = n
            continue
        at = ln.get("at")
        runs.append({"start": n, "end": n, "sha": ln["sha"], "short": ln["sha"][:8], "author": ln.get("author", ""),
                     "at": db.iso(datetime.fromtimestamp(at, timezone.utc)) if isinstance(at, int) else None,
                     "summary": ln.get("summary", ""), "change": changes.get(ln["sha"])})
    return {"path": path, "runs": runs}


def open_at(conn, row: dict, v: Viewer, actor: dict, path: str, rev: str) -> dict:
    """A file as it was at an earlier version. Whole-file readers only: a few
    granted lines today say nothing about which lines those were back then."""
    rev = _rev(rev)
    if not _can_read_whole(v, path):
        raise HTTPException(403, "Earlier versions are open to people who can read the whole file.")
    if not gitops.is_ancestor(row["id"], rev, row["head_sha"]):
        raise HTTPException(404, "That version isn't in this repository's history.")
    t = service.load(row, path, rev)
    service.note_read(conn, actor, "open", f"{path}@{rev[:12]}")
    return {"path": path, "rev": rev, "lines": t.lines, "lines_total": len(t.lines),
            "symbols": text.symbols(path, t.lines)}
