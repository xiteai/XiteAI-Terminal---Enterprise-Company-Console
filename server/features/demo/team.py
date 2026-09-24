"""A demo team so the org chart, approvals and profiles have something to
show. Every demo person has an unusable password: they can never sign in."""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from ...access import levels
from ...core import config, db, notify
from ...security import passwords
from . import data as d


def _profile(rng: random.Random, name: str, department: str, now: datetime) -> dict:
    first = name.split()[0]
    age = rng.randint(21, 38)
    grad = now.year - (age - 22)
    return {
        "dob": (now - timedelta(days=age * 365.25 + rng.randint(0, 364))).date().isoformat(),
        "gender": rng.choice(["Woman", "Man", "Prefer not to say"]),
        "phone": f"+91 9{rng.randint(100000000, 999999999)}",
        "personal_email": f"{name.lower().replace(' ', '.')}@example.com",
        "city": rng.choice(d.CITIES),
        "address": f"{rng.randint(11, 480)}, Sector {rng.randint(10, 150)}",
        "emergency": {"name": f"{rng.choice(d.FIRST)} {name.split()[-1]}", "relation": rng.choice(["Parent", "Sibling",
                      "Spouse or partner"]), "phone": f"+91 9{rng.randint(100000000, 999999999)}"},
        "education": {"qualification": rng.choice(["Bachelor's degree", "Master's degree"]),
                      "institution": rng.choice(d.COLLEGES), "graduation_year": str(grad)},
        "experience": {"years": str(max(0, age - 22)), "previous_company": rng.choice(
            ["", "Zoho", "Flipkart", "Razorpay", "Freshworks", "Swiggy", "Infosys"])},
        "skills": rng.sample(d.SKILLS.get(department, ["Communication"]), k=min(3, len(d.SKILLS.get(department, [1])))),
        "links": {"linkedin": f"https://example.com/in/{first.lower()}", "portfolio": ""},
        "about": f"Hi, I'm {first}. Looking forward to building XOS1 with everyone.",
        "consent": {"accurate": True, "storage": True, "at": now.isoformat()},
    }


def seed(conn, rng: random.Random, now: datetime, founder_id: int | None) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name, level, dept, title, boss, status, days in d.TEAM:
        created = now - timedelta(days=days, hours=rng.randint(1, 9))
        email = f"{name.lower().replace(' ', '.')}@{config.EMAIL_DOMAIN}"
        if conn["staff"].find_one({"email": email}, {"_id": 1}):
            continue
        decided = status != "pending"
        staff_id = db.next_id(conn, "staff")
        conn["staff"].insert_one({
            **levels.new_staff_defaults(), "_id": staff_id, "id": staff_id, "email": email, "display_name": name,
            "level": level, "requested_level": level, "title": title, "department": dept,
            "employment_type": "Intern" if level == "intern" else "Full-time",
            "start_date": (created + timedelta(days=7)).date().isoformat(), "password_hash": passwords.unusable_hash(),
            "reports_to": ids.get(boss, founder_id) if decided else None, "status": status, "source": "signup",
            "profile_json": json.dumps(_profile(rng, name, dept, now)), "created_at": created.isoformat(),
            "decided_by": founder_id if decided else None,
            "decided_at": (created + timedelta(hours=5)).isoformat() if decided else None,
            "decision_note": "Role closed after the content pilot." if status == "deactivated" else "",
            "is_demo": True,
        })
        ids[name] = staff_id
        if status == "pending" and founder_id:
            notify.send(conn, [founder_id], "join.request", f"{name} wants to join as {levels.LABEL[level]}",
                        f"{title} · {dept}", f"/console/people/requests/{staff_id}", staff_id)
    return ids


def assign(conn, now: datetime, founder_id: int | None, products: dict[str, int], ids: dict[str, int]) -> None:
    """Put the demo team on the products they work on: the first name leads."""
    for slug, names in d.PRODUCT_TEAMS.items():
        pid = products.get(slug)
        if not pid:
            continue
        if founder_id:
            key = f"{pid}:{founder_id}"
            conn["product_members"].update_one(
                {"_id": key}, {"$setOnInsert": {"_id": key, "product_id": pid, "staff_id": founder_id, "role": "Owner",
                                                "added_by": None, "added_at": now.isoformat()}}, upsert=True)
        for i, name in enumerate(names):
            if name in ids:
                key = f"{pid}:{ids[name]}"
                conn["product_members"].update_one(
                    {"_id": key}, {"$setOnInsert": {"_id": key, "product_id": pid, "staff_id": ids[name],
                                                    "role": "Lead" if i == 0 else "Member", "added_by": founder_id,
                                                    "added_at": now.isoformat()}}, upsert=True)
