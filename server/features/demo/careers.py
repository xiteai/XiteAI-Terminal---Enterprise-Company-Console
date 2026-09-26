"""Demo roles, open on the public Careers board. A small, curated set spread
across a few teams — not one in every department — so the board reads as
real openings someone chose to post, not filler. A couple carry enough demo
applicants to clear the "shown past 10" threshold, a couple don't, so both
states of that rule are visible."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ...core import db

# title, department, employment_type, location, summary, description, days ago posted, demo applicants
ROLES = [
    ("Senior Systems Engineer, On-Device Runtime", "Engineering", "Full-time", "Bengaluru, India",
     "Own the layer between XOS1 and the machine it runs on.",
     "What you'd do\n"
     "- Work on the boundary where a model meets real hardware: memory, scheduling, power.\n"
     "- Make XOS1 fast and quiet on an ordinary laptop, not a data center.\n"
     "- Ship weekly, on a small team where you own what you build end to end.\n\n"
     "What we're looking for\n"
     "- Several years writing systems-level code — C++, Rust, or similarly close to the machine.\n"
     "- You've debugged something at 2am by reading a stack trace, not a dashboard.",
     14, 14),
    ("ML Engineer, On-Device Inference", "Data & AI", "Full-time", "Bengaluru, India",
     "Get a full model running fast and privately, entirely on-device.",
     "What you'd do\n"
     "- Quantize, prune and optimize models to run within a laptop's real constraints.\n"
     "- Work directly with the runtime team — this isn't research thrown over a wall.\n\n"
     "What we're looking for\n"
     "- Hands-on experience shipping ML that runs somewhere other than a GPU cluster.\n"
     "- You care as much about latency and memory as you do about accuracy.",
     9, 7),
    ("UI/UX Designer", "Design", "Full-time", "Remote (India)",
     "Design how XOS1 feels — including the parts people never think about.",
     "What you'd do\n"
     "- Shape the console, the onboarding flow and the moments where XOS1 asks for trust.\n"
     "- Work closely with engineering; a design that can't ship isn't a design yet here.\n\n"
     "What we're looking for\n"
     "- A portfolio that shows real shipped product, not only concepts.\n"
     "- An eye for restraint — XOS1's whole feel is quiet, not loud.",
     4, 3),
    ("Product Manager, Platform", "Product", "Full-time", "Bengaluru, India",
     "Decide what XOS1 does next, grounded in what people actually use today.",
     "What you'd do\n"
     "- Work from real check-in data and support tickets, not a roadmap written once a year.\n"
     "- Sit close to engineering and design; this is a hands-on PM role, not a coordination one.\n\n"
     "What we're looking for\n"
     "- A few years shaping a product people actually depend on.\n"
     "- Comfortable saying no to most ideas so the few that ship are right.",
     20, 11),
]


def seed(conn, rng: random.Random, now: datetime, founder_id: int | None) -> int:
    if not founder_id:
        return 0
    n = 0
    for title, dept, emp, loc, summary, description, days_ago, applicants in ROLES:
        posted = (now - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        rid = db.next_id(conn, "job_roles")
        conn["job_roles"].insert_one({
            "_id": rid, "id": rid, "title": title, "department": dept, "employment_type": emp, "location": loc,
            "summary": summary, "description": description, "status": "open", "posted_at": posted,
            "closed_at": None, "created_by": founder_id, "is_demo": True})
        n += 1
        for i in range(applicants):
            applied = (now - timedelta(days=rng.randint(0, days_ago))).replace(microsecond=0).isoformat()
            aid = db.next_id(conn, "job_applications")
            conn["job_applications"].insert_one({
                "_id": aid, "id": aid, "role_id": rid, "name": f"Demo Applicant {i + 1}",
                "email": f"demo.applicant{rid}.{i + 1}@example.com", "phone": "", "portfolio": "",
                "note": "", "applied_at": applied, "ip": "", "is_demo": True})
            n += 1
    return n


def purge(conn) -> int:
    demo_roles = conn["job_roles"].distinct("id", {"is_demo": True})
    apps = conn["job_applications"].delete_many({"role_id": {"$in": demo_roles}}).deleted_count if demo_roles else 0
    roles = conn["job_roles"].delete_many({"is_demo": True}).deleted_count
    return apps + roles
