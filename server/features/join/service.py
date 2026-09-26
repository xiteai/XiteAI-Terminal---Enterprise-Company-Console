"""A new team member asks to join. The account is created as 'pending', they
are signed straight in to a waiting page, and everyone who can approve their
level gets one notification."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ...access import levels, perms
from ...core import audit, config, db, notify
from ...security import passwords, sessions
from . import validate as v
from .schemas import JoinBody


def email_available(conn, local: str) -> bool:
    email = f"{v.local_part(local)}@{config.EMAIL_DOMAIN}"
    return not conn["staff"].find_one({"email": email}, {"_id": 1}, collation=db.CASE_INSENSITIVE)


def _grad_year(value: str) -> str:
    year = v.small_int("graduation_year", value, 1950, 2040)
    if not year:
        raise v.FieldError("graduation_year", "Add the year you graduated.")
    return year


def _profile(b: JoinBody) -> dict:
    return {
        "dob": v.dob(b.dob),
        "gender": b.gender if b.gender in ("Woman", "Man", "Non-binary", "Prefer not to say") else "",
        "phone": v.phone("phone", b.phone),
        "personal_email": v.email("personal_email", b.personal_email),
        "city": v.text("city", b.city, True, "your city"),
        "address": b.address.strip(),
        "emergency": {
            "name": v.text("emergency_name", b.emergency_name, True, "an emergency contact"),
            "relation": v.text("emergency_relation", b.emergency_relation, True, "how you know them"),
            "phone": v.phone("emergency_phone", b.emergency_phone),
        },
        "education": {
            "qualification": v.text("qualification", b.qualification, True, "your highest qualification"),
            "institution": v.text("institution", b.institution, True, "where you studied"),
            "graduation_year": _grad_year(b.graduation_year),
        },
        "experience": {
            "years": v.small_int("experience_years", b.experience_years, 0, 60),
            "previous_company": b.previous_company.strip(),
        },
        "skills": [s.strip() for s in b.skills.split(",") if s.strip()][:25],
        "links": {"linkedin": v.url("linkedin", b.linkedin), "portfolio": v.url("portfolio", b.portfolio)},
        "about": b.about.strip(),
        "consent": {"accurate": True, "storage": True, "at": db.now_iso()},
    }


def submit(conn, b: JoinBody, ip: str, user_agent: str) -> tuple[int, str]:
    if b.website:
        raise HTTPException(400, "Something went wrong. Please try again.")
    local = v.local_part(b.local)
    problem = passwords.problem(b.password)
    if problem:
        raise v.FieldError("password", problem)
    level = v.level(b.level)
    if not (b.agree_accurate and b.agree_storage):
        raise v.FieldError("agree", "Tick both boxes to send your request.")
    profile = _profile(b)
    photo = v.photo(b.photo)
    department, employment = v.department(b.department), v.employment_type(b.employment_type)
    start = v.iso_date("start_date", b.start_date, False)
    email = f"{local}@{config.EMAIL_DOMAIN}"

    since = db.iso(datetime.now(timezone.utc) - timedelta(hours=1))
    if conn["staff"].count_documents({"signup_ip": ip, "created_at": {"$gte": since}}) >= config.JOIN_REQUESTS_PER_HOUR:
        raise HTTPException(429, "A few requests came from here already. Please try again in an hour.")

    with db.tx(conn) as tconn:
        if tconn["staff"].find_one({"email": email}, {"_id": 1}, collation=db.CASE_INSENSITIVE):
            raise v.FieldError("local", f"{email} is taken. Try another.")
        now = db.now_iso()
        staff_id = db.next_id(tconn, "staff")
        tconn["staff"].insert_one({
            **levels.new_staff_defaults(), "_id": staff_id, "id": staff_id, "email": email,
            "display_name": b.full_name.strip(), "preferred_name": b.preferred_name.strip(), "level": level,
            "requested_level": level, "title": b.title.strip(), "department": department,
            "employment_type": employment, "start_date": start, "password_hash": passwords.hash_password(b.password),
            "status": "pending", "source": "signup", "profile_json": json.dumps(profile), "avatar_url": photo,
            "created_at": now, "signup_ip": ip,
        })
        me = {"id": staff_id, "display_name": b.full_name.strip(), "level": level}
        audit.record(tconn, me, "join.requested", email, f"{levels.LABEL[level]} · {b.title.strip()}", ip)
        notify.send(tconn, perms.holders(tconn, "people.approve", above=level), "join.request",
                    f"{b.full_name.strip()} wants to join as {levels.LABEL[level]}",
                    f"{b.title.strip()} · {department}", f"/console/people/requests/{staff_id}", staff_id)
        token = sessions.create(tconn, staff_id, user_agent, ip)
    return staff_id, token
