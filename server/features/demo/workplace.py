"""Demo Workplace data: what the team has filed, and what payroll has issued.

Some requests are left pending on purpose, so whoever can decide them has
something waiting when they open Approvals."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

import json

from ...core import db
from ..workplace import store

# kind, days ago filed, leave_type/category, note, and the numbers each kind needs.
# Leave's "days" is a list of offsets from today — not always contiguous, so
# the demo shows the calendar handling a real alternate-day request too.
REQUESTS = [
    ("leave", 3, "annual", "Sister's wedding.", {"days": [18, 19, 20]}),
    ("leave", 9, "sick", "Food poisoning, saw a doctor.", {"days": [-8]}),
    ("leave", 1, "casual", "Half the week, working from my hometown.", {"days": [6, 8, 10]}),
    ("leave", 21, "annual", "Two weeks in Kerala.", {"days": list(range(30, 41))}),
    ("expense", 2, "travel", "Client visit, Bengaluru — flights and cab.", {"amount": 1848050}),
    ("expense", 5, "meals", "Team dinner after the 2.4 release.", {"amount": 742600}),
    ("expense", 12, "software", "Figma seat, annual.", {"amount": 1200000}),
    ("expense", 30, "training", "Kubernetes course.", {"amount": 3500000}),
    ("asset", 4, "monitor", "Second screen for review work.", {"quantity": 1, "action": "new"}),
    ("asset", 8, "laptop", "Current one won't hold a charge past an hour.", {"quantity": 1, "action": "new"}),
    ("asset", 16, "peripherals", "Keyboard and headset for the new desk.", {"quantity": 2, "action": "new"}),
    ("asset", 6, "laptop", "Dropped it — screen's cracked. Replacing, not repairing.", {"quantity": 1, "action": "replacement"}),
]
# Which of the above are still waiting: the rest get decided below.
PENDING = {0, 2, 4, 8, 10, 11}

# Fixed-date national holidays. Festival dates move every year and aren't
# guessed here — HR adds the real ones once the reference doc is in.
HOLIDAYS = [("01-26", "Republic Day"), ("08-15", "Independence Day"), ("10-02", "Gandhi Jayanti"),
            ("12-25", "Christmas")]

TICKETS = [
    ("laptop", "high", "Laptop won't wake from sleep", "Happens after the lid's been shut overnight. Hard reboot is the only way back.", 1, "open"),
    ("access", "urgent", "Locked out of the staging console", "Password reset email never arrives. Tried twice.", 0, "open"),
    ("software", "normal", "Figma crashes on the design file", "Only that one file. Others are fine.", 4, "in_progress"),
    ("network", "normal", "VPN drops every twenty minutes", "Started Monday. Others on my floor see it too.", 6, "in_progress"),
    ("other", "low", "Second monitor arm is loose", "Slowly droops through the day.", 11, "resolved"),
    ("laptop", "normal", "Fan runs constantly", "Even with nothing open.", 20, "closed"),
]

# A month's pay, in paise, by level. Deductions are a flat ~18%.
PAY = {"founder": 45000000, "vp": 32000000, "director": 26000000, "hr": 18000000,
       "manager": 20000000, "employee": 13000000, "intern": 4000000}
MONTHS = 6


def seed(conn, rng: random.Random, now: datetime, ids: dict[str, int]) -> int:
    """`ids` is the demo team, by name. Payslips go to everyone active, demo or
    not: a payslip nobody can see doesn't demonstrate anything."""
    people = list(ids.values())
    if not people:
        return 0
    deciders = [i for i in conn["staff"].distinct("id", {"status": "active", "level": {"$in": ["founder", "vp"]}})]
    today = now.date()
    filed = 0

    for n, (kind, days_ago, category, note, extra) in enumerate(REQUESTS):
        staff_id = people[n % len(people)]
        created = (now - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        row = {"leave_type": "", "start_date": "", "end_date": "", "dates_json": "[]", "days": 0,
               "category": "", "amount_paise": 0, "spent_on": "", "quantity": 0, "asset_action": "new"}
        fine_paise = 0
        if kind == "leave":
            # Demo dates are pre-authored for narrative, so inserted directly
            # rather than through the weekday/holiday rules a real filing gets.
            picked = sorted(today + timedelta(days=off) for off in extra["days"])
            row |= {"leave_type": category, "start_date": picked[0].isoformat(), "end_date": picked[-1].isoformat(),
                    "dates_json": json.dumps([d.isoformat() for d in picked]), "days": len(picked)}
            title = f"{category.capitalize()} leave, {len(picked)} day{'s' if len(picked) != 1 else ''}"
        elif kind == "expense":
            row |= {"category": category, "amount_paise": extra["amount"],
                    "spent_on": (today - timedelta(days=days_ago + 1)).isoformat()}
            title = f"{category.capitalize()}, ₹{extra['amount'] / 100:,.2f}"
        else:
            quantity, action = extra["quantity"], extra["action"]
            row |= {"category": category, "quantity": quantity, "asset_action": action}
            label = category.capitalize() + (f" × {quantity}" if quantity > 1 else "")
            title = f"{label} (Replacement)" if action == "replacement" else label
            if action == "replacement" and n not in PENDING:
                fine_paise = 150000                          # a token charge for the cracked screen

        decided = n not in PENDING
        status = ("approved" if rng.random() > 0.25 else "declined") if decided else "pending"
        store.run(
            "INSERT INTO work_requests (kind, staff_id, status, title, note, leave_type, start_date, end_date, "
            "dates_json, days, category, amount_paise, spent_on, quantity, asset_action, fine_paise, created_at, "
            "decided_by, decided_at, decision_note, is_demo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (kind, staff_id, status, title, note, row["leave_type"], row["start_date"], row["end_date"],
             row["dates_json"], row["days"], row["category"], row["amount_paise"], row["spent_on"],
             row["quantity"], row["asset_action"], fine_paise, created,
             (rng.choice(deciders) if deciders else None) if decided else None,
             (now - timedelta(days=max(0, days_ago - 1))).replace(microsecond=0).isoformat() if decided else None,
             "" if status != "declined" else "Not this quarter — let's revisit."))
        filed += 1

    year = today.year
    for md, label in HOLIDAYS:
        store.run("INSERT OR IGNORE INTO work_holidays (date, label, is_demo) VALUES (?,?,1)",
                  (f"{year}-{md}", label))

    for n, (category, priority, subject, body, days_ago, status) in enumerate(TICKETS):
        at = (now - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        with store.tx() as t:
            tid = t.run("INSERT INTO work_tickets (ref, staff_id, category, subject, body, status, priority, "
                        "created_at, updated_at, is_demo) VALUES ('',?,?,?,?,?,?,?,?,1)",
                        (people[n % len(people)], category, subject, body, status, priority, at, at)).lastrowid
            t.run("UPDATE work_tickets SET ref = ? WHERE id = ?", (f"WT-{tid:04d}", tid))
            if status != "open" and deciders:
                t.run("UPDATE work_tickets SET assignee_id = ? WHERE id = ?", (rng.choice(deciders), tid))
                t.run("INSERT INTO work_ticket_notes (ticket_id, staff_id, body, at) VALUES (?,?,?,?)",
                      (tid, rng.choice(deciders), "Taking a look — can you try it once more and tell me what you see?",
                       (now - timedelta(days=max(0, days_ago - 1))).replace(microsecond=0).isoformat()))
        filed += 1

    issued = 0
    for r in conn["staff"].find({"status": "active"}, {"id": 1, "level": 1}):
        gross = PAY.get(r["level"], PAY["employee"])
        for back in range(MONTHS):
            first = (now.replace(day=1) - timedelta(days=back * 30)).date().replace(day=1)
            deductions = int(gross * 0.18)
            store.run("INSERT OR IGNORE INTO work_payslips (staff_id, period, gross_paise, deductions_paise, "
                      "net_paise, issued_at, is_demo) VALUES (?,?,?,?,?,?,1)",
                      (r["id"], first.strftime("%Y-%m"), gross, deductions, gross - deductions,
                       db.iso(datetime.combine(first, now.time()).replace(tzinfo=now.tzinfo))))
            issued += 1
    return filed + issued


def purge() -> dict:
    return {"workplace": sum(store.run(f"DELETE FROM {table} WHERE is_demo = 1").rowcount
                             for table in ("work_requests", "work_tickets", "work_payslips", "work_holidays"))}


def present() -> bool:
    return bool(store.scalar("SELECT 1 FROM work_requests WHERE is_demo = 1 LIMIT 1"))
