from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...access import levels
from ...core import audit, clock, config, db, notify, settings
from ...security import mfa
from ...web.deps import actor, writable
from . import changes, gitops, history, service, store, text
from .access import Viewer

router = APIRouter(prefix="/api/code", tags=["code"])

_ANY = {"code.map", "code.request", "code.read_all", "code.access_view", "code.grant", "code.grant_all",
        "code.owners", "code.merge_all", "code.revoke", "code.connect"}
_MANAGE = {"code.access_view", "code.grant", "code.grant_all", "code.owners", "code.revoke", "code.connect"}


NEED_CODE = ("Opening company code needs your authenticator. Set it up from Account (it takes a minute), "
             "then sign in again with a code.")


def mfa_required(conn) -> bool:
    return settings.get(conn, "code_requires_mfa", "1") == "1"


def member(a: dict = Depends(actor)) -> dict:
    """The codebase's front door: the right permission, a session opened with an
    authenticator code (unless the founder switched that off), and not paused."""
    if not (_ANY & a["perms"]):
        raise HTTPException(403, "Your level doesn't include the codebase.")
    if a.get("code_paused") and a["level"] != "founder":
        raise HTTPException(403, {"message": service.PAUSED, "field": "paused"})
    if not a["mfa"]:
        with db.connect() as conn:
            if mfa_required(conn):
                raise HTTPException(403, {"message": NEED_CODE, "field": "authenticator",
                                          "enrolled": mfa.enrolled(a)})
    return a


def _need(a: dict, *perms: str) -> None:
    if a["eff_level"] != "founder" and not (set(perms) & a["perms"]):
        raise HTTPException(403, "Your level doesn't include this.")


# ── repositories ──────────────────────────────────────────────────────────────

class RepoBody(BaseModel):
    name: str = Field(max_length=80)
    url: str = Field(max_length=300)
    branch: str = Field(default="", max_length=100)   # blank = use the repository's own default branch


@router.get("/repos")
def repos(a: dict = Depends(member)):
    items = [service.repo_card(r) for r in store.rows("SELECT * FROM code_repos ORDER BY id")]
    return {"items": items,
            "can_connect": "code.connect" in a["perms"] and not a["previewing"],
            "can_sync": bool({"code.connect", "code.merge_all"} & a["perms"]) and not a["previewing"]}


@router.post("/repos")
def connect(body: RepoBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    if not a["mfa"]:
        # Even with the company-wide switch off: bringing the code in is never done on a password alone.
        raise HTTPException(403, {"message": "Connecting the company's code needs your authenticator. "
                                             "Set it up from Account, then sign in again with a code.",
                                  "field": "authenticator", "enrolled": mfa.enrolled(a)})
    with db.connect() as conn:
        return service.connect_repo(conn, a, body.name, body.url, body.branch)


@router.post("/repos/{rid}/sync")
def sync(rid: int, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect", "code.merge_all")
    with db.connect() as conn:
        return service.repo_card(service.sync(conn, service.repo(conn, rid)))


@router.post("/repos/{rid}/history/accept")
def accept_rewrite(rid: int, a: dict = Depends(member)):
    """After GitHub's history was rewritten: follow GitHub (ours stays pinned)."""
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        if not row["held_remote"]:
            raise HTTPException(409, "Nothing is waiting: GitHub and the Terminal agree.")
        with gitops.lock(rid):
            old, new = gitops.accept_remote(rid, row["remote_url"], row["branch"])
            if old != new:
                service.remap(rid, old, new)
        store.run("UPDATE code_repos SET head_sha = ?, remote_sha = ?, held_remote = '', status_detail = '', "
                  "last_sync_at = ? WHERE id = ?", (new, new, db.now_iso(), rid))
        audit.record(conn, a, "code.rewrite_accepted", row["name"], f"followed GitHub to {new[:10]}; kept {old[:10]}", a["ip"])
        return service.repo_card(service.repo(conn, rid))


@router.post("/repos/{rid}/history/put-back")
def put_back_history(rid: int, a: dict = Depends(member)):
    """After GitHub's history was rewritten: put the real history back on GitHub."""
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        if not row["held_remote"]:
            raise HTTPException(409, "Nothing is waiting: GitHub and the Terminal agree.")
        try:
            with gitops.lock(rid):
                sha = gitops.put_back(rid, row["remote_url"], row["branch"], row["held_remote"])
        except gitops.GitError as e:
            raise HTTPException(502, f"GitHub didn't take it back: {e}")
        store.run("UPDATE code_repos SET remote_sha = ?, held_remote = '', status_detail = '', last_sync_at = ? "
                  "WHERE id = ?", (sha, db.now_iso(), rid))
        audit.record(conn, a, "code.rewrite_reversed", row["name"], f"GitHub put back to {sha[:10]}", a["ip"])
        return service.repo_card(service.repo(conn, rid))


@router.delete("/repos/{rid}")
def disconnect(rid: int, a: dict = Depends(member)):
    """Also doubles as Cancel: removing a repository that's still being copied
    from GitHub stops that copy first, so it doesn't keep running (or keep
    the files locked) after it's gone from the list."""
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid, ready=False)
        cancelled = gitops.cancel(rid)
        with gitops.lock(rid):
            store.run("DELETE FROM code_repos WHERE id = ?", (rid,))   # everything under it goes too
            gitops.remove(rid)
        detail = "cancelled while copying from GitHub" if cancelled else \
            "grants, features and change requests removed with it"
        audit.record(conn, a, "code.repo_removed", row["name"], detail, a["ip"])
        return {"ok": True}


@router.get("/changes/{cid}/where")
def where(cid: int, a: dict = Depends(member)):
    """Which repository a change request belongs to (links carry only its number).
    Declared before the /{rid}/ routes so 'changes' isn't read as a repository id."""
    row = store.one("SELECT repo_id FROM code_changes WHERE id = ?", (cid,))
    if not row:
        raise HTTPException(404, "No change request by that number.")
    return {"repo_id": row["repo_id"]}


# ── security: the founder's switches (declared before the /{rid}/ routes) ─────

class SecurityBody(BaseModel):
    require_mfa: bool


def _security(conn) -> dict:
    staff = [db.strip(r) for r in conn["staff"].find({"status": "active", "is_demo": False}).sort("display_name", 1)]
    code_people = [s for s in staff if s["level"] == "founder" or _ANY & perms_of(conn, s["level"])]
    return {
        "require_mfa": mfa_required(conn),
        "paused": [{"id": s["id"], "name": s["display_name"], "level_label": levels.LABEL[s["level"]]}
                   for s in staff if s["code_paused"]],
        "no_authenticator": [{"id": s["id"], "name": s["display_name"], "level_label": levels.LABEL[s["level"]]}
                             for s in code_people if not mfa.enrolled(s)],
        "alarm": {"alert_files": config.CODE_ALERT_FILES_HOUR, "pause_files": config.CODE_PAUSE_FILES_HOUR,
                  "alert_searches": config.CODE_ALERT_SEARCHES_HOUR, "pause_searches": config.CODE_PAUSE_SEARCHES_HOUR},
    }


def perms_of(conn, level: str) -> set[str]:
    from ...access import perms
    return perms.effective(conn, level)


@router.get("/security")
def security(a: dict = Depends(member)):
    _need(a, "code.connect")
    with db.connect() as conn:
        return _security(conn)


@router.put("/security")
def set_security(body: SecurityBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        settings.put(conn, "code_requires_mfa", "1" if body.require_mfa else "0", a["id"])
        audit.record(conn, a, "code.security_changed", "authenticator required for code",
                     "on" if body.require_mfa else "OFF", a["ip"])
        return _security(conn)


@router.post("/people/{sid}/resume")
def resume(sid: int, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        person = conn["staff"].find_one({"_id": sid}, {"id": 1, "display_name": 1, "email": 1})
        if not person:
            raise HTTPException(404, "No one by that id.")
        conn["staff"].update_one({"_id": sid}, {"$set": {"code_paused": False}})
        store.run("DELETE FROM code_reads WHERE staff_id = ?", (sid,))    # a fresh count, or they'd pause again at once
        audit.record(conn, a, "code.resumed", person["email"], "", a["ip"])
        notify.send(conn, [sid], "code.resumed", "Your code access is back", f"Resumed by {a['display_name']}.",
                    "/console/code")
        return _security(conn)


# ── reading code ──────────────────────────────────────────────────────────────

def _ctx(conn, rid: int, a: dict):
    row = service.repo(conn, rid)
    return row, Viewer(conn, rid, a)


@router.get("/{rid}/tree")
def tree(rid: int, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return {"repo": service.repo_card(row), "files": service.tree(row, v),
                "can_request": v.founder or "code.request" in v.perms}


@router.get("/{rid}/file")
def open_file(rid: int, path: str, rev: str | None = None, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        if rev:
            return history.open_at(conn, row, v, a, path, rev)
        return service.open_file(conn, row, v, a, path)


@router.get("/{rid}/symbols")
def symbols(rid: int, path: str, a: dict = Depends(member)):
    """The named parts of a file, for picking what to give. Names only, no code."""
    _need(a, "code.grant", "code.grant_all", "code.owners")
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        if v.guarded(path) and not v.founder:
            raise HTTPException(403, "That file is protected. Only the founder gives access to it.")
        t = service.load(row, path)
        return {"path": path, "lines_total": len(t.lines), "symbols": text.symbols(path, t.lines)}


@router.get("/{rid}/search")
def search(rid: int, q: str = "", a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return service.search(conn, row, v, a, q)


# ── protected paths (the founder's) ───────────────────────────────────────────

class PathBody(BaseModel):
    path: str = Field(max_length=500)


def _protected(conn, row: dict) -> dict:
    names = {r["id"]: r["display_name"] for r in conn["staff"].find({}, {"id": 1, "display_name": 1})}
    have = store.rows("SELECT * FROM code_protected WHERE repo_id = ? ORDER BY path", (row["id"],))
    return {"items": [{"path": p["path"], "at": p["added_at"], "by": names.get(p["added_by"], "set up automatically")}
                      for p in have],
            "suggested": [p for p in service.PROTECT_SUGGEST
                          if p not in {h["path"] for h in have} and (service.exists(row, p, folder=True) or service.exists(row, p))]}


@router.get("/{rid}/protected")
def protected(rid: int, a: dict = Depends(member)):
    _need(a, "code.connect")
    with db.connect() as conn:
        return _protected(conn, service.repo(conn, rid))


@router.post("/{rid}/protected")
def protect(rid: int, body: PathBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    path = body.path.strip().strip("/")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        if not path:
            raise HTTPException(400, "Pick a folder or a file.")
        if not (service.exists(row, path, folder=True) or service.exists(row, path)):
            raise HTTPException(400, f"There's no folder or file {path}.")
        store.run("INSERT OR IGNORE INTO code_protected (repo_id, path, added_by, added_at) VALUES (?,?,?,?)",
                  (rid, path, a["id"], db.now_iso()))
        audit.record(conn, a, "code.protected", f"{row['name']}:{path}", "", a["ip"])
        return _protected(conn, row)


@router.delete("/{rid}/protected")
def unprotect(rid: int, path: str, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        n = store.run("DELETE FROM code_protected WHERE repo_id = ? AND path = ?", (rid, path)).rowcount
        if n:
            audit.record(conn, a, "code.unprotected", f"{row['name']}:{path}", "", a["ip"])
        return _protected(conn, row)


# ── who was given what ────────────────────────────────────────────────────────

class Item(BaseModel):
    kind: str
    path: str = Field(default="", max_length=500)
    line_start: int | None = None
    line_end: int | None = None
    symbol: str = Field(default="", max_length=200)


class GrantBody(BaseModel):
    staff_id: int
    feature_id: int | None = None
    items: list[Item] = []
    can_edit: bool = False
    expires_on: str | None = Field(default=None, max_length=10)     # YYYY-MM-DD, access ends after that day
    note: str = Field(default="", max_length=300)


class FeatureBody(BaseModel):
    name: str = Field(max_length=60)
    description: str = Field(default="", max_length=300)
    items: list[Item] = []


class ItemsBody(BaseModel):
    items: list[Item]


class OwnerBody(BaseModel):
    staff_id: int
    role: str
    path: str | None = Field(default=None, max_length=500)
    feature_id: int | None = None


@router.get("/{rid}/access")
def access(rid: int, a: dict = Depends(member)):
    _need(a, *_MANAGE)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return service.access_overview(conn, row, v)


@router.get("/{rid}/people")
def people(rid: int, a: dict = Depends(member)):
    """Who can be picked: everyone active below you, and you (for owners)."""
    _need(a, *_MANAGE)
    with db.connect() as conn:
        out = []
        rows = conn["staff"].find({"status": "active", "is_demo": False},
                                  {"id": 1, "display_name": 1, "level": 1, "title": 1, "reports_to": 1}
                                  ).sort("display_name", 1)
        for r in rows:
            if r["id"] == a["id"] or a["eff_level"] == "founder" or levels.outranks(a["eff_level"], r["level"]):
                out.append({"id": r["id"], "name": r["display_name"], "level": r["level"],
                            "level_label": levels.LABEL[r["level"]], "title": r["title"], "me": r["id"] == a["id"]})
        return {"items": out}


def _expiry(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # The end of that day on the company's clock (IST by default), stored in UTC.
        day = datetime.strptime(value, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc) - clock.OFFSET
    except ValueError:
        raise HTTPException(400, "Use a date like 2026-12-31.") from None
    if day <= datetime.now(timezone.utc):
        raise HTTPException(400, "Pick a date in the future.")
    return db.iso(day)


@router.post("/{rid}/grants")
def grant(rid: int, body: GrantBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.grant", "code.grant_all")
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        target = service.target_person(conn, body.staff_id)
        if body.feature_id:
            f = store.one("SELECT * FROM code_features WHERE id = ? AND repo_id = ?", (body.feature_id, rid))
            if not f:
                raise HTTPException(404, "No feature by that id.")
            items = store.rows("SELECT kind, path FROM code_items WHERE feature_id = ?", (f["id"],))
            what = f"feature {f['name']}"
        else:
            items = service.clean_items(row, [i.model_dump() for i in body.items])
            what = "; ".join(service.describe(i) for i in items)[:300]
        service.check_grant_power(conn, v, items, target, body.can_edit)
        expires = _expiry(body.expires_on)
        with store.tx() as t:
            gid = t.run("INSERT INTO code_grants (repo_id, staff_id, feature_id, can_edit, note, granted_by, granted_at, "
                        "expires_at) VALUES (?,?,?,?,?,?,?,?)",
                        (rid, target["id"], body.feature_id, int(body.can_edit), body.note.strip(), a["id"],
                         db.now_iso(), expires)).lastrowid
            if not body.feature_id:
                service.add_items(t, rid, items, grant_id=gid)
        audit.record(conn, a, "code.access_given", target["display_name"],
                     f"{'edit' if body.can_edit else 'read'}: {what}", a["ip"])
        notify.send(conn, [target["id"]], "code.access", f"{a['display_name']} gave you access to code",
                            f"{'Read and edit' if body.can_edit else 'Read'}: {what}"[:200], "/console/code", gid)
        return service.access_overview(conn, row, v)


@router.delete("/{rid}/grants/{gid}")
def revoke(rid: int, gid: int, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        g = store.one("SELECT * FROM code_grants WHERE id = ? AND repo_id = ?", (gid, rid))
        if not g:
            raise HTTPException(404, "No grant by that id.")
        target = db.strip(conn["staff"].find_one({"_id": g["staff_id"]})) or \
            {"display_name": "someone removed", "level": "intern"}
        above = v.founder or levels.outranks(v.level, target["level"])
        items = service.items_of(feature_id=g["feature_id"]) if g["feature_id"] else service.items_of(grant_id=gid)
        owns_all = bool(items) and all(v.role_for(i["path"]) == "owner" for i in items)
        if not (v.founder or (above and ("code.revoke" in v.perms or g["granted_by"] == v.id or
                                        ({"code.grant", "code.grant_all"} & v.perms and owns_all)))):
            raise HTTPException(403, "You can't take this access away.")
        store.run("DELETE FROM code_grants WHERE id = ?", (gid,))     # its own items go with it
        audit.record(conn, a, "code.access_removed", target["display_name"],
                     "; ".join(i["label"] for i in items)[:300], a["ip"])
        return service.access_overview(conn, row, v)


def _features(a: dict) -> None:
    _need(a, "code.grant_all", "code.owners")


@router.post("/{rid}/features")
def new_feature(rid: int, body: FeatureBody, a: dict = Depends(member)):
    writable(a)
    _features(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        name = body.name.strip()
        if len(name) < 2:
            raise HTTPException(400, "Give the feature a name.")
        if store.one("SELECT id FROM code_features WHERE repo_id = ? AND name = ?", (rid, name)):
            raise HTTPException(409, "A feature with that name exists.")
        items = service.clean_items(row, [i.model_dump() for i in body.items])
        service.founder_only_inside_protection(v, items, "puts into features")
        try:
            with store.tx() as t:
                fid = t.run("INSERT INTO code_features (repo_id, name, description, created_by, created_at) "
                            "VALUES (?,?,?,?,?)", (rid, name, body.description.strip(), a["id"], db.now_iso())).lastrowid
                service.add_items(t, rid, items, feature_id=fid)
        except sqlite3.IntegrityError:
            raise HTTPException(409, "A feature with that name exists.") from None   # made at the same moment
        audit.record(conn, a, "code.feature_created", name, "; ".join(service.describe(i) for i in items)[:300], a["ip"])
        return service.access_overview(conn, row, v)


@router.post("/{rid}/features/{fid}/items")
def feature_add(rid: int, fid: int, body: ItemsBody, a: dict = Depends(member)):
    writable(a)
    _features(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        f = store.one("SELECT * FROM code_features WHERE id = ? AND repo_id = ?", (fid, rid))
        if not f:
            raise HTTPException(404, "No feature by that id.")
        items = service.clean_items(row, [i.model_dump() for i in body.items])
        service.founder_only_inside_protection(v, items, "puts into features")
        service.add_items(store, rid, items, feature_id=fid)
        audit.record(conn, a, "code.feature_changed", f["name"], "added " + "; ".join(service.describe(i) for i in items)[:280], a["ip"])
        return service.access_overview(conn, row, v)


@router.delete("/{rid}/features/{fid}/items/{iid}")
def feature_remove_item(rid: int, fid: int, iid: int, a: dict = Depends(member)):
    writable(a)
    _features(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        feat = store.one("SELECT * FROM code_features WHERE id = ? AND repo_id = ?", (fid, rid))
        it = feat and store.one("SELECT * FROM code_items WHERE id = ? AND feature_id = ?", (iid, fid))
        if not it:
            raise HTTPException(404, "Not in this feature.")
        store.run("DELETE FROM code_items WHERE id = ?", (iid,))
        audit.record(conn, a, "code.feature_changed", feat["name"],
                     "removed " + service.describe(it), a["ip"])
        return service.access_overview(conn, row, v)


@router.delete("/{rid}/features/{fid}")
def feature_delete(rid: int, fid: int, a: dict = Depends(member)):
    writable(a)
    _features(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        f = store.one("SELECT * FROM code_features WHERE id = ? AND repo_id = ?", (fid, rid))
        if not f:
            raise HTTPException(404, "No feature by that id.")
        n = store.scalar("SELECT COUNT(*) FROM code_grants WHERE feature_id = ?", (fid,))
        # Its items, the grants of it and the roles over it all go in the same step.
        store.run("DELETE FROM code_features WHERE id = ?", (fid,))
        audit.record(conn, a, "code.feature_deleted", f["name"], f"{n} grant(s) of it ended", a["ip"])
        return service.access_overview(conn, row, v)


@router.post("/{rid}/owners")
def add_owner(rid: int, body: OwnerBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.owners")
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        target = service.target_person(conn, body.staff_id)
        service.check_owner_target(v, target, body.role)
        if body.feature_id:
            if not store.one("SELECT id FROM code_features WHERE id = ? AND repo_id = ?", (body.feature_id, rid)):
                raise HTTPException(404, "No feature by that id.")
            path = None
            scope = store.rows("SELECT path FROM code_items WHERE feature_id = ?", (body.feature_id,))
        else:
            path = (body.path or "").strip().strip("/")
            if not (service.exists(row, path, folder=True) or service.exists(row, path)):
                raise HTTPException(400, f"There's no folder or file {path}.")
            scope = [{"path": path}]
        service.founder_only_inside_protection(v, scope, "chooses owners of")
        store.run("INSERT INTO code_owners (repo_id, staff_id, role, path, feature_id, added_by, added_at) "
                  "VALUES (?,?,?,?,?,?,?)", (rid, target["id"], body.role, path, body.feature_id, a["id"], db.now_iso()))
        audit.record(conn, a, "code.owner_set", target["display_name"],
                     f"{body.role} of {'feature #' + str(body.feature_id) if body.feature_id else (path or 'everything')}", a["ip"])
        return service.access_overview(conn, row, v)


@router.delete("/{rid}/owners/{oid}")
def remove_owner(rid: int, oid: int, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.owners")
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        o = store.one("SELECT * FROM code_owners WHERE id = ? AND repo_id = ?", (oid, rid))
        if not o:
            raise HTTPException(404, "Not found.")
        person = conn["staff"].find_one({"_id": o["staff_id"]}, {"display_name": 1, "level": 1}) or \
            {"display_name": "someone removed", "level": ""}
        if person["level"] == "founder" and not v.founder:
            raise HTTPException(403, "Only the founder changes what the founder owns.")
        store.run("DELETE FROM code_owners WHERE id = ?", (oid,))
        audit.record(conn, a, "code.owner_removed", person["display_name"], f"{o['role']} of {o['path'] or 'feature'}", a["ip"])
        return service.access_overview(conn, row, v)


# ── change requests ───────────────────────────────────────────────────────────

class ChangeBody(BaseModel):
    title: str = Field(max_length=120)
    body: str = Field(default="", max_length=4000)


class Segment(BaseModel):
    start: int
    end: int
    text: str = Field(max_length=2_000_000)


class FileBody(BaseModel):
    path: str = Field(max_length=500)
    mode: str
    base_sha: str | None = Field(default=None, max_length=64)
    text: str | None = Field(default=None, max_length=2_000_000)
    segments: list[Segment] = []


class ReviewBody(BaseModel):
    verdict: str
    body: str = Field(default="", max_length=4000)


class MergeBody(BaseModel):
    override: bool = False


@router.get("/{rid}/changes")
def list_changes(rid: int, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return {"items": changes.listing(conn, row, v)}


@router.post("/{rid}/changes")
def new_change(rid: int, body: ChangeBody, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.request")
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        cid = changes.create(row, a, body.title, body.body)
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.get("/{rid}/changes/{cid}")
def change(rid: int, cid: int, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.patch("/{rid}/changes/{cid}")
def edit_change(rid: int, cid: int, body: ChangeBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        c = changes.get(cid, rid)
        changes._own_open(c, a)
        if len(body.title.strip()) < 3:
            raise HTTPException(400, "Give the change a short title that says what it does.")
        store.run("UPDATE code_changes SET title = ?, body = ?, updated_at = ? WHERE id = ?",
                  (body.title.strip()[:120], body.body.strip()[:4000], db.now_iso(), cid))
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.put("/{rid}/changes/{cid}/files")
def put_file(rid: int, cid: int, body: FileBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.put_file(row, v, a, changes.get(cid, rid), body.model_dump())
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.delete("/{rid}/changes/{cid}/files")
def drop_file(rid: int, cid: int, path: str, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.drop_file(a, changes.get(cid, rid), path)
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.post("/{rid}/changes/{cid}/submit")
def submit(rid: int, cid: int, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.submit(conn, row, a, changes.get(cid, rid))
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.post("/{rid}/changes/{cid}/review")
def review(rid: int, cid: int, body: ReviewBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.review(conn, row, v, a, changes.get(cid, rid), body.verdict, body.body)
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.post("/{rid}/changes/{cid}/merge")
def merge(rid: int, cid: int, body: MergeBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.merge(conn, row, v, a, changes.get(cid, rid), body.override)
        return changes.detail(conn, service.repo(conn, rid), v, changes.get(cid, rid))


@router.post("/{rid}/changes/{cid}/withdraw")
def withdraw(rid: int, cid: int, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        changes.withdraw(a, changes.get(cid, rid))
        return changes.detail(conn, row, v, changes.get(cid, rid))


class CommentBody(BaseModel):
    path: str = Field(max_length=500)
    side: str = "new"
    line: int
    body: str = Field(max_length=4000)


@router.post("/{rid}/changes/{cid}/comments")
def add_comment(rid: int, cid: int, body: CommentBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        c = changes.get(cid, rid)
        changes.comment(conn, v, a, c, body.path, body.side, body.line, body.body)
        return changes.detail(conn, row, v, changes.get(cid, rid))


@router.post("/{rid}/changes/{cid}/comments/{mid}/resolve")
def resolve_comment(rid: int, cid: int, mid: int, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        c = changes.get(cid, rid)
        changes.resolve_comment(v, a, c, mid)
        return changes.detail(conn, row, v, changes.get(cid, rid))


# ── history: what changed, who changed it, and taking it back ────────────────

@router.get("/{rid}/history")
def timeline(rid: int, path: str | None = None, skip: int = 0, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return history.timeline(row, v, path=path, skip=max(0, skip))


@router.get("/{rid}/commits/{sha}")
def commit(rid: int, sha: str, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return history.commit(row, v, sha)


@router.get("/{rid}/compare")
def compare(rid: int, base: str, target: str = "HEAD", a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return history.compare(row, v, base, target)


@router.get("/{rid}/blame")
def blame(rid: int, path: str, a: dict = Depends(member)):
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        return history.blame(row, v, path)


class RestoreBody(BaseModel):
    path: str = Field(max_length=500)
    rev: str = Field(max_length=64)


@router.post("/{rid}/commits/{sha}/undo")
def undo_commit(rid: int, sha: str, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        c = changes.undo(conn, row, v, a, sha)
        audit.record(conn, a, "code.undo_opened", f"{row['name']} #{c['id']}", f"undoes {sha[:10]}", a["ip"])
        return changes.detail(conn, row, v, c)


@router.post("/{rid}/changes/{cid}/undo")
def undo_change(rid: int, cid: int, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        original = changes.get(cid, rid)
        if original["status"] != "merged" or not original["merged_sha"]:
            raise HTTPException(409, "Only a merged change can be undone.")
        c = changes.undo(conn, row, v, a, original["merged_sha"])
        audit.record(conn, a, "code.undo_opened", f"{row['name']} #{c['id']}", f"undoes #{cid}", a["ip"])
        return changes.detail(conn, row, v, c)


@router.post("/{rid}/restore")
def restore(rid: int, body: RestoreBody, a: dict = Depends(member)):
    writable(a)
    with db.connect() as conn:
        row, v = _ctx(conn, rid, a)
        c = changes.restore(conn, row, v, a, body.path, body.rev)
        audit.record(conn, a, "code.restore_opened", f"{row['name']} #{c['id']}", f"{body.path} to {body.rev[:10]}", a["ip"])
        return changes.detail(conn, row, v, c)


# ── checkpoints and backups ───────────────────────────────────────────────────

class CheckpointBody(BaseModel):
    name: str = Field(max_length=49)
    note: str = Field(default="", max_length=300)


def _checkpoints(conn, row: dict) -> list[dict]:
    rows = store.rows("SELECT * FROM code_checkpoints WHERE repo_id = ? ORDER BY created_at DESC, id DESC", (row["id"],))
    names = {r["id"]: r["display_name"] for r in conn["staff"].find(
        {"id": {"$in": sorted({c["created_by"] for c in rows if c["created_by"]})}}, {"id": 1, "display_name": 1})}
    return [{"name": c["name"], "sha": c["sha"], "short": c["sha"][:8], "note": c["note"], "at": c["created_at"],
             "by": names.get(c["created_by"], "someone removed"), "on_github": bool(c["on_github"])} for c in rows]


@router.get("/{rid}/checkpoints")
def checkpoints(rid: int, a: dict = Depends(member)):
    with db.connect() as conn:
        row, _ = _ctx(conn, rid, a)
        return {"items": _checkpoints(conn, row), "can_create": a["eff_level"] == "founder" or "code.merge_all" in a["perms"]}


@router.post("/{rid}/checkpoints")
def make_checkpoint(rid: int, body: CheckpointBody, a: dict = Depends(member)):
    """A named point in the history, e.g. before-memory-rewrite: a tag here, and on GitHub."""
    writable(a)
    _need(a, "code.merge_all")
    name = body.name.strip().replace(" ", "-")
    with db.connect() as conn:
        row, _ = _ctx(conn, rid, a)
        if store.one("SELECT id FROM code_checkpoints WHERE repo_id = ? AND name = ?", (rid, name)):
            raise HTTPException(409, "A checkpoint with that name exists.")
        try:
            with gitops.lock(rid):
                sha = gitops.make_tag(rid, name, body.note.strip() or name, a["display_name"], a["email"])
                on_github = False
                if not (row["remote_url"].startswith("https://") and not config.GITHUB_TOKEN):
                    try:
                        gitops.push_tag(rid, row["remote_url"], name)
                        on_github = True
                    except gitops.GitError:
                        pass
        except gitops.GitError as e:
            raise HTTPException(400, str(e))
        store.run("INSERT INTO code_checkpoints (repo_id, name, sha, note, created_by, created_at, on_github) "
                  "VALUES (?,?,?,?,?,?,?)", (rid, name, sha, body.note.strip(), a["id"], db.now_iso(), int(on_github)))
        audit.record(conn, a, "code.checkpoint", f"{row['name']}:{name}", sha[:10], a["ip"])
        return {"items": _checkpoints(conn, row), "can_create": True}


@router.get("/{rid}/backups")
def backups(rid: int, a: dict = Depends(member)):
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        return {"items": service.backups(row), "keep": config.CODE_BACKUPS_KEEP,
                "folder": str(config.CODE_BACKUP_DIR / f"repo-{rid}")}


@router.post("/{rid}/backups")
def backup_now(rid: int, a: dict = Depends(member)):
    writable(a)
    _need(a, "code.connect")
    with db.connect() as conn:
        row = service.repo(conn, rid)
        try:
            service.backup_daily(row)
        except gitops.GitError as e:
            raise HTTPException(500, f"The backup didn't finish: {e}")
        audit.record(conn, a, "code.backup", row["name"], "", a["ip"])
        return {"items": service.backups(row), "keep": config.CODE_BACKUPS_KEEP,
                "folder": str(config.CODE_BACKUP_DIR / f"repo-{rid}")}
