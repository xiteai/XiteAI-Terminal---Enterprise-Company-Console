"""Demo finance: six months of revenue and cost, modelled rather than made up.

Everything below is computed from a subscriber count per tier, so the numbers
agree with each other — revenue is what those subscribers pay, and the AI bill
is what those same subscribers cost to serve. Change a count and both move
together, which is the point: a demo P&L that doesn't add up teaches the
wrong instincts.

THE PRICES ARE THE REAL ONES (per month, INR):
    XiteAI Chat   ₹599
    XOS1 Prime    ₹1,299    3 model calls a turn
    XOS1 Premium  ₹2,399    4 model calls a turn
    XOS1 Pro      ₹29,999   everything

THE FREE MONTH IS A REAL COST. Every new user gets a month free, and on Prime
only — not Premium, not Pro. Those people still burn inference, so the trial
cohort appears in `ai_api` with no revenue beside it. Leaving it out would
flatter the margin and hide the one number that actually decides whether the
free month is affordable.

SERVING COST IS A BLEND, NOT A HEAVY USER. A heavy Prime user bills about
$6-8 a month (measured). Most users are not heavy ones, so charging the heavy
figure to every subscriber would overstate the bill by roughly double and
make the margin look worse than it is. The figures below are blended averages
across a realistic spread of light, normal and heavy use.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ...core import db

USD = 83                       # ₹ per $, for turning measured dollar bills into paise
MONTHS = 6

PRICE = {"prime": 1299_00, "premium": 2399_00, "pro": 29999_00, "chat": 599_00}   # paise
SERVE = {"prime": 4.0 * USD * 100, "premium": 9.0 * USD * 100,                      # paise/user/month, blended
         "pro": 30.0 * USD * 100, "chat": 0.9 * USD * 100}
# Trial users skew heavy — a free month is when people try everything — so
# they are costed above the blended Prime average rather than at it.
SERVE_TRIAL = 6.0 * USD * 100

# Paying subscribers at the end of each month, oldest first. Strong but not
# absurd growth for a product people keep: roughly 45% month on month, easing.
OS1_PAID = [
    {"prime": 180, "premium": 40, "pro": 2},
    {"prime": 320, "premium": 75, "pro": 3},
    {"prime": 520, "premium": 130, "pro": 5},
    {"prime": 820, "premium": 210, "pro": 7},
    {"prime": 1250, "premium": 330, "pro": 10},
    {"prime": 1850, "premium": 480, "pro": 14},
]
# On their free month: they cost money and pay nothing. Sized as the intake
# that becomes next month's paying Prime users, at a ~55% conversion.
OS1_TRIAL = [260, 380, 560, 800, 1100, 1450]
CHAT_PAID = [400, 780, 1250, 1800, 2450, 3200]

# The rest of running a company, in paise per month, oldest first.
INFRA = [45_000_00, 52_000_00, 61_000_00, 74_000_00, 92_000_00, 115_000_00]
SALARIES = [420_000_00, 420_000_00, 560_000_00, 560_000_00, 720_000_00, 720_000_00]
MARKETING = [60_000_00, 95_000_00, 140_000_00, 180_000_00, 240_000_00, 310_000_00]
VENDOR = [18_000_00, 18_000_00, 24_000_00, 24_000_00, 31_000_00, 31_000_00]


def _month_start(now: datetime, back: int):
    first = now.replace(day=1).date()
    for _ in range(back):
        first = (first - timedelta(days=1)).replace(day=1)
    return first


def seed(conn, rng: random.Random, now: datetime, product_id: int, founder_id: int | None,
         plan: str = "os1") -> int:
    if not founder_id:
        return 0
    n = 0
    for i in range(MONTHS):
        back = MONTHS - 1 - i
        first = _month_start(now, back)
        on = (first + timedelta(days=rng.randint(1, 6))).isoformat()

        if plan == "os1":
            paid = OS1_PAID[i]
            for tier in ("prime", "premium", "pro"):
                amount = paid[tier] * PRICE[tier]
                _add(conn, product_id, "revenue", "subscription", amount, on, founder_id,
                     f"{paid[tier]} {tier.capitalize()} subscribers")
                n += 1
            serving = sum(paid[t] * SERVE[t] for t in ("prime", "premium", "pro"))
            trial = OS1_TRIAL[i] * SERVE_TRIAL
            _add(conn, product_id, "cost", "ai_api", int(serving), on, founder_id, "Inference, paying users")
            _add(conn, product_id, "cost", "ai_api", int(trial), on, founder_id,
                 f"Inference, {OS1_TRIAL[i]} users on their free month")
            n += 2
        else:
            users = CHAT_PAID[i]
            _add(conn, product_id, "revenue", "subscription", users * PRICE["chat"], on, founder_id,
                 f"{users} Chat subscribers")
            _add(conn, product_id, "cost", "ai_api", int(users * SERVE["chat"]), on, founder_id, "Inference")
            n += 2

        share = 1.0 if plan == "os1" else 0.35        # Chat carries a smaller slice of the overheads
        for category, table in (("infra", INFRA), ("salaries", SALARIES),
                                ("marketing", MARKETING), ("vendor", VENDOR)):
            _add(conn, product_id, "cost", category, int(table[i] * share), on, founder_id, "")
            n += 1
    return n


def _add(conn, product_id, kind, category, amount_paise, occurred_on, founder_id, note):
    eid = db.next_id(conn, "finance_entries")
    conn["finance_entries"].insert_one({
        "_id": eid, "id": eid, "product_id": product_id, "kind": kind, "category": category,
        "amount_paise": int(amount_paise), "occurred_on": occurred_on, "note": note,
        "created_by": founder_id, "created_at": db.now_iso(), "is_demo": True})


def purge(conn) -> int:
    return conn["finance_entries"].delete_many({"is_demo": True}).deleted_count
