"""Who may read and change which code.

A person's reach in a repository comes from three places:
  • their level: the founder has everything; `code.read_all` reads everything
  • what they answer for: an owner reads and edits it, a reviewer reads it
  • grants: folders, files, functions/classes, line ranges, or whole features,
    each read-only or editable, optionally until a date

Protected paths (the updater, signing, build and release scripts, dependency
lists) are a wall: `code.read_all`, grants and roles on anything wider stop at
their edge. Only a grant or role placed inside one reaches in, and only the
founder can place those.

Resolved per file into: the whole file, some line ranges, or nothing. The
server sends only what resolves; the UI never gets a line it may not show.

Codebase records come from store (SQLite); people from MongoDB (`conn`)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...core import db
from . import store, text


def covers(scope: str, path: str) -> bool:
    """A folder or file scope covers `path` ('' covers everything)."""
    scope = scope.strip("/")
    return scope == "" or path == scope or path.startswith(scope + "/")


@dataclass
class FileAccess:
    read_full: bool = False
    edit_full: bool = False
    ranges: list = field(default_factory=list)    # [(start, end, editable)] merged; only when not read_full

    @property
    def any(self) -> bool:
        return self.read_full or bool(self.ranges)

    @property
    def can_edit(self) -> bool:
        return self.edit_full or any(ed for _, _, ed in self.ranges)

    def visible(self) -> set[int] | None:
        """Line numbers they may read; None = all of them."""
        if self.read_full:
            return None
        return {n for s, e, _ in self.ranges for n in range(s, e + 1)}


class Viewer:
    """One person's reach in one repository, loaded once per request."""

    def __init__(self, conn, repo_id: int, actor: dict):
        self.id = actor["id"]
        self.level = actor["eff_level"]
        self.perms = actor["perms"]
        self.founder = self.level == "founder"
        self.read_all = self.founder or "code.read_all" in self.perms
        self.merge_all = self.founder or "code.merge_all" in self.perms
        self.protected = protected_paths(repo_id)
        self.items = store.rows("""
            SELECT i.kind, i.path, i.line_start, i.line_end, i.symbol, g.can_edit
              FROM code_grants g
              JOIN code_items i ON i.grant_id = g.id OR (g.feature_id IS NOT NULL AND i.feature_id = g.feature_id)
             WHERE g.repo_id = ? AND g.staff_id = ? AND i.missing = 0
               AND (g.expires_at IS NULL OR g.expires_at > ?)""", (repo_id, self.id, db.now_iso()))
        self.roles = roles_of(repo_id, self.id)

    # ── protected paths ─────────────────────────────────────────────────────
    def guarded(self, path: str) -> str | None:
        """The protected area `path` is in, if any."""
        return guard_of(self.protected, path)

    def reaches(self, scope: str, path: str) -> bool:
        """A scope covers `path` and, if `path` is protected, sits inside that protection."""
        return reaches(self.protected, scope, path)

    # ── what they answer for ────────────────────────────────────────────────
    def role_for(self, path: str) -> str | None:
        found = {role for role, scope in self.roles if self.reaches(scope, path)}
        return "owner" if "owner" in found else ("reviewer" if found else None)

    # ── per file, without opening it (the folder map) ───────────────────────
    def level_for(self, path: str) -> tuple[str, bool]:
        """('full' | 'partial' | 'none', can edit something in it)."""
        role = self.role_for(path)
        if self.founder:
            return "full", True
        full = (self.read_all and not self.guarded(path)) or role is not None
        edit = role == "owner"
        partial = False
        for it in self.items:
            if it["kind"] in ("folder", "file") and self.reaches(it["path"], path):
                full = True
                edit = edit or bool(it["can_edit"])
            elif it["path"] == path:
                partial = True
                edit = edit or bool(it["can_edit"])
        return ("full" if full else "partial" if partial else "none"), edit

    # ── per file, opened ────────────────────────────────────────────────────
    def access(self, path: str, lines: list[str]) -> FileAccess:
        role = self.role_for(path)
        if self.founder:
            return FileAccess(True, True)
        acc = FileAccess(read_full=(self.read_all and not self.guarded(path)) or role is not None,
                         edit_full=role == "owner")
        ranges = []
        for it in self.items:
            if it["kind"] in ("folder", "file") and self.reaches(it["path"], path):
                acc.read_full = True
                acc.edit_full = acc.edit_full or bool(it["can_edit"])
            elif it["path"] == path:
                span = resolve(it, path, lines)
                if span:
                    ranges.append((span[0], span[1], bool(it["can_edit"])))
        if acc.edit_full:
            acc.read_full = True
        if acc.read_full:
            # Whole file readable; editable in parts only if some grant says so.
            acc.ranges = [] if acc.edit_full else [r for r in text.merge_ranges(ranges) if r[2]]
        else:
            acc.ranges = text.merge_ranges(ranges)
        return acc

    def editable_lines(self, path: str, lines: list[str]) -> tuple[bool, list[tuple[int, int]]]:
        """(whole file editable, [(start, end)] editable ranges otherwise)."""
        acc = self.access(path, lines)
        if acc.edit_full:
            return True, []
        return False, [(s, e) for s, e, ed in acc.ranges if ed]


def resolve(item: dict, path: str, lines: list[str]) -> tuple[int, int] | None:
    """Where a lines or symbol item sits in the file right now."""
    if item["kind"] == "symbol":
        return text.find_symbol(path, lines, item["symbol"])
    if item["kind"] == "lines" and item["line_start"] and item["line_end"]:
        s, e = max(1, item["line_start"]), min(len(lines), item["line_end"])
        return (s, e) if s <= e else None
    return None


def roles_of(repo_id: int, staff_id: int) -> list[tuple[str, str]]:
    """[(role, folder-or-file scope)]. A feature someone owns counts as every
    folder and file in it (a function or lines inside a file count as that
    whole file: reviewing needs the file around the change)."""
    out = []
    for r in store.rows("SELECT role, path, feature_id FROM code_owners WHERE repo_id = ? AND staff_id = ?",
                        (repo_id, staff_id)):
        if r["feature_id"]:
            for it in store.rows("SELECT path FROM code_items WHERE feature_id = ? AND missing = 0", (r["feature_id"],)):
                out.append((r["role"], it["path"]))
        else:
            out.append((r["role"], r["path"] or ""))
    return out


def protected_paths(repo_id: int) -> list[str]:
    return [r["path"] for r in store.rows("SELECT path FROM code_protected WHERE repo_id = ?", (repo_id,))]


def guard_of(protected: list[str], path: str) -> str | None:
    return next((p for p in protected if covers(p, path)), None)


def reaches(protected: list[str], scope: str, path: str) -> bool:
    if not covers(scope, path):
        return False
    g = guard_of(protected, path)
    return g is None or covers(g, scope.strip("/"))


def people_answering_for(conn, repo_id: int, path: str) -> list[tuple[int, str]]:
    """[(staff_id, role)] of active people who own or review `path` (inside a
    protected area, only roles placed inside it count)."""
    out = {}
    protected = protected_paths(repo_id)
    owner_ids = [r["staff_id"] for r in store.rows("SELECT DISTINCT staff_id FROM code_owners WHERE repo_id = ?",
                                                   (repo_id,))]
    active = set(conn["staff"].distinct("id", {"id": {"$in": owner_ids}, "status": "active"})) if owner_ids else set()
    for staff_id in owner_ids:
        if staff_id not in active:
            continue
        for role, scope in roles_of(repo_id, staff_id):
            if reaches(protected, scope, path):
                if out.get(staff_id) != "owner":
                    out[staff_id] = role
    return list(out.items())
