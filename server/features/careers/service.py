"""Open roles, and applying to one. Public reads and applies need no sign-in;
posting and closing a role, and seeing who applied, need careers.manage."""
from __future__ import annotations

from fastapi import HTTPException

from ...core import audit, db
from ..join import options
from ..join import validate as v

APPLICANT_THRESHOLD = 10          # the count is shown only once it clears this


def _shape_public(row: dict, applicant_count: int) -> dict:
    return {
        "id": row["id"], "title": row["title"], "department": row["department"],
        "employment_type": row["employment_type"], "location": row["location"], "summary": row["summary"],
        "description": row["description"], "posted_at": row["posted_at"],
        "applicant_count": applicant_count if applicant_count > APPLICANT_THRESHOLD else None,
        "is_demo": bool(row.get("is_demo", False)),
    }


def _counts(conn, role_ids: list[int]) -> dict[int, int]:
    if not role_ids:
        return {}
    out = {r["_id"]: r["n"] for r in conn["job_applications"].aggregate([
        {"$match": {"role_id": {"$in": role_ids}}}, {"$group": {"_id": "$role_id", "n": {"$sum": 1}}}])}
    return out


def public_board(conn) -> list[dict]:
    """Only departments with something open. A department with nothing to
    show says nothing, rather than spending a whole section on saying so."""
    open_roles = list(conn["job_roles"].find({"status": "open"}).sort("posted_at", -1))
    counts = _counts(conn, [r["id"] for r in open_roles])
    by_dept: dict[str, list[dict]] = {}
    for r in open_roles:
        by_dept.setdefault(r["department"], []).append(_shape_public(r, counts.get(r["id"], 0)))
    return [{"department": d, "roles": by_dept[d]} for d in options.DEPARTMENTS if d in by_dept]


def public_role(conn, role_id: int) -> dict:
    row = conn["job_roles"].find_one({"_id": role_id, "status": "open"})
    if not row:
        raise HTTPException(404, "That role isn't open.")
    counts = _counts(conn, [role_id])
    return _shape_public(row, counts.get(role_id, 0))


def apply(conn, role_id: int, body: dict, ip: str) -> None:
    if body.get("website"):                       # honeypot: real applicants never see this field
        return
    row = conn["job_roles"].find_one({"_id": role_id, "status": "open"})
    if not row:
        raise HTTPException(404, "That role isn't open anymore.")
    name = v.text("name", body.get("name", ""), True, "your name")
    email = v.email("email", body.get("email", ""))
    phone = (body.get("phone") or "").strip()
    if phone:
        phone = v.phone("phone", phone)
    portfolio = v.url("portfolio", body.get("portfolio") or "")
    note = (body.get("note") or "").strip()[:2000]

    if conn["job_applications"].find_one({"role_id": role_id, "email": email}, collation=db.CASE_INSENSITIVE):
        raise HTTPException(409, f"{email} already applied to this role.")

    aid = db.next_id(conn, "job_applications")
    conn["job_applications"].insert_one({
        "_id": aid, "id": aid, "role_id": role_id, "name": name, "email": email, "phone": phone,
        "portfolio": portfolio, "note": note, "applied_at": db.now_iso(), "ip": ip, "is_demo": False})


# ── Managing roles (careers.manage) ─────────────────────────────────────────

def _shape_admin(row: dict, applicant_count: int) -> dict:
    # The 10-applicant threshold is a public-page courtesy, not something to
    # hide from the person who posted the role.
    return _shape_public(row, applicant_count) | {"status": row["status"], "closed_at": row.get("closed_at"),
                                                  "applicant_count": applicant_count}


def admin_list(conn) -> list[dict]:
    rows = list(conn["job_roles"].find().sort("posted_at", -1))
    counts = _counts(conn, [r["id"] for r in rows])
    return [_shape_admin(r, counts.get(r["id"], 0)) for r in rows]


def create_role(conn, a: dict, body: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    department = body.get("department", "")
    if department not in options.DEPARTMENTS:
        raise HTTPException(400, "Pick a department from the list.")
    employment_type = body.get("employment_type", "")
    if employment_type not in options.EMPLOYMENT_TYPES:
        raise HTTPException(400, "Pick an employment type from the list.")
    title = v.text("title", body.get("title", ""), True, "a title")
    summary = v.text("summary", body.get("summary", ""), True, "a one-line summary")
    description = (body.get("description") or "").strip()[:6000]
    location = (body.get("location") or "Remote").strip()[:80]

    now = db.now_iso()
    rid = db.next_id(conn, "job_roles")
    conn["job_roles"].insert_one({
        "_id": rid, "id": rid, "title": title, "department": department, "employment_type": employment_type,
        "location": location, "summary": summary, "description": description, "status": "open",
        "posted_at": now, "closed_at": None, "created_by": a["id"], "is_demo": False})
    audit.record(conn, a, "careers.role_posted", title, department, a["ip"])
    return _shape_admin(conn["job_roles"].find_one({"_id": rid}), 0)


def update_role(conn, a: dict, role_id: int, body: dict) -> dict:
    """Edit a posted role in place. It's live the moment this saves — there's
    no separate publish step, the way changing the Handbook has none."""
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = conn["job_roles"].find_one({"_id": role_id})
    if not row:
        raise HTTPException(404, "No role with that id.")
    department = body.get("department", "")
    if department not in options.DEPARTMENTS:
        raise HTTPException(400, "Pick a department from the list.")
    employment_type = body.get("employment_type", "")
    if employment_type not in options.EMPLOYMENT_TYPES:
        raise HTTPException(400, "Pick an employment type from the list.")
    title = v.text("title", body.get("title", ""), True, "a title")
    summary = v.text("summary", body.get("summary", ""), True, "a one-line summary")
    description = (body.get("description") or "").strip()[:6000]
    location = (body.get("location") or "Remote").strip()[:80]

    conn["job_roles"].update_one({"_id": role_id}, {"$set": {
        "title": title, "department": department, "employment_type": employment_type, "location": location,
        "summary": summary, "description": description}})
    audit.record(conn, a, "careers.role_edited", title, department, a["ip"])
    counts = _counts(conn, [role_id])
    return _shape_admin(conn["job_roles"].find_one({"_id": role_id}), counts.get(role_id, 0))


def set_status(conn, a: dict, role_id: int, status: str) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if status not in ("open", "closed"):
        raise HTTPException(400, "Unknown status.")
    row = conn["job_roles"].find_one({"_id": role_id})
    if not row:
        raise HTTPException(404, "No role with that id.")
    conn["job_roles"].update_one({"_id": role_id}, {"$set": {
        "status": status, "closed_at": db.now_iso() if status == "closed" else None}})
    audit.record(conn, a, f"careers.role_{status}", row["title"], "", a["ip"])
    counts = _counts(conn, [role_id])
    return _shape_admin(conn["job_roles"].find_one({"_id": role_id}), counts.get(role_id, 0))


def applicants(conn, a: dict, role_id: int) -> dict:
    row = conn["job_roles"].find_one({"_id": role_id})
    if not row:
        raise HTTPException(404, "No role with that id.")
    rows = list(conn["job_applications"].find({"role_id": role_id}).sort("applied_at", -1))
    return {"role": _shape_admin(row, len(rows)),
            "items": [{"id": r["id"], "name": r["name"], "email": r["email"], "phone": r["phone"],
                      "portfolio": r["portfolio"], "note": r["note"], "applied_at": r["applied_at"],
                      "is_demo": bool(r.get("is_demo", False))} for r in rows]}
