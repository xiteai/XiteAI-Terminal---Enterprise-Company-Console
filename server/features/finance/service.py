"""Revenue and cost entries, and the P&L rolled up from them. Nothing here is
computed automatically from anywhere else in the console (not from payslips,
not from AI usage) — that's a real integration for another day. Today it's
what finance types in, the way payroll issues a payslip by hand."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException

from ...core import audit, db

REVENUE_CATEGORIES = {"subscription": "Subscriptions", "one_time": "One-time sale", "services": "Services",
                      "other": "Other"}
COST_CATEGORIES = {"infra": "Infrastructure", "ai_api": "AI API usage", "salaries": "Salaries",
                   "marketing": "Marketing", "vendor": "Vendor & tools", "other": "Other"}
CATEGORIES = {"revenue": REVENUE_CATEGORIES, "cost": COST_CATEGORIES}
MAX_PAISE = 500_000_000_00                # ₹50 crore; a guard rail, not a real ceiling


def _people(conn, ids) -> dict[int, dict]:
    wanted = sorted({i for i in ids if i})
    if not wanted:
        return {}
    return {r["id"]: {"id": r["id"], "name": r["display_name"]}
           for r in conn["staff"].find({"id": {"$in": wanted}}, {"id": 1, "display_name": 1})}


def _shape(row: dict, people: dict) -> dict:
    return {"id": row["id"], "kind": row["kind"], "category": row["category"],
            "category_label": CATEGORIES[row["kind"]].get(row["category"], row["category"]),
            "amount_paise": row["amount_paise"], "occurred_on": row["occurred_on"], "note": row["note"],
            "created_by": people.get(row["created_by"]), "created_at": row["created_at"],
            "is_demo": bool(row.get("is_demo", False))}


def entries(conn, product_id: int, kind: str | None = None, limit: int = 300) -> list[dict]:
    filt: dict = {"product_id": product_id}
    if kind:
        filt["kind"] = kind
    rows = list(conn["finance_entries"].find(filt).sort("occurred_on", -1).limit(limit))
    people = _people(conn, [r["created_by"] for r in rows])
    return [_shape(r, people) for r in rows]


def add_entry(conn, a: dict, product_id: int, body: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    kind = (body.get("kind") or "").strip()
    if kind not in CATEGORIES:
        raise HTTPException(400, "Say whether this is revenue or a cost.")
    category = (body.get("category") or "").strip()
    if category not in CATEGORIES[kind]:
        raise HTTPException(400, "Pick a category from the list.")
    try:
        paise = int(round(float(body.get("amount")) * 100))
    except (TypeError, ValueError):
        raise HTTPException(400, "That amount isn't a number.") from None
    if paise <= 0:
        raise HTTPException(400, "An entry has to be for more than nothing.")
    if paise > MAX_PAISE:
        raise HTTPException(400, "That's an implausible amount for one entry. Split it if it's real.")
    try:
        occurred = date.fromisoformat((body.get("occurred_on") or "").strip())
    except ValueError:
        raise HTTPException(400, "That date isn't real.") from None
    if occurred > date.today() + timedelta(days=1):
        raise HTTPException(400, "That date is in the future.")
    note = (body.get("note") or "").strip()[:500]

    now = db.now_iso()
    eid = db.next_id(conn, "finance_entries")
    conn["finance_entries"].insert_one({
        "_id": eid, "id": eid, "product_id": product_id, "kind": kind, "category": category,
        "amount_paise": paise, "occurred_on": occurred.isoformat(), "note": note, "created_by": a["id"],
        "created_at": now, "is_demo": False})
    audit.record(conn, a, f"finance.{kind}_logged", CATEGORIES[kind][category],
                f"₹{paise / 100:,.2f}{f' · {note}' if note else ''}"[:120], a["ip"])
    return _shape(conn["finance_entries"].find_one({"_id": eid}), _people(conn, [a["id"]]))


def remove_entry(conn, a: dict, product_id: int, entry_id: int) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = conn["finance_entries"].find_one({"_id": entry_id, "product_id": product_id})
    if not row:
        raise HTTPException(404, "No entry with that id.")
    conn["finance_entries"].delete_one({"_id": entry_id})
    audit.record(conn, a, f"finance.{row['kind']}_removed", CATEGORIES[row["kind"]].get(row["category"], ""),
                f"₹{row['amount_paise'] / 100:,.2f}", a["ip"])


def summary(conn, product_id: int, months: int = 12) -> dict:
    """Revenue, cost and the gap between them, this month and trended back."""
    since = (date.today().replace(day=1) - timedelta(days=31 * (months - 1))).replace(day=1)
    rows = list(conn["finance_entries"].find({"product_id": product_id, "occurred_on": {"$gte": since.isoformat()}}))

    by_month: dict[str, dict] = {}
    by_category: dict[str, dict[str, int]] = {"revenue": {}, "cost": {}}
    revenue_total = cost_total = 0
    for r in rows:
        period = r["occurred_on"][:7]
        slot = by_month.setdefault(period, {"revenue": 0, "cost": 0})
        slot[r["kind"]] += r["amount_paise"]
        by_category[r["kind"]][r["category"]] = by_category[r["kind"]].get(r["category"], 0) + r["amount_paise"]
        if r["kind"] == "revenue":
            revenue_total += r["amount_paise"]
        else:
            cost_total += r["amount_paise"]

    months_list = []
    cursor = since
    for _ in range(months):
        key = cursor.strftime("%Y-%m")
        slot = by_month.get(key, {"revenue": 0, "cost": 0})
        months_list.append({"period": key, "revenue_paise": slot["revenue"], "cost_paise": slot["cost"],
                            "net_paise": slot["revenue"] - slot["cost"]})
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    net = revenue_total - cost_total
    return {
        "revenue_paise": revenue_total, "cost_paise": cost_total, "net_paise": net,
        "margin": (net / revenue_total) if revenue_total else None,
        "months": months_list,
        "by_category": {kind: [{"category": c, "label": CATEGORIES[kind].get(c, c), "amount_paise": amt}
                               for c, amt in sorted(cats.items(), key=lambda kv: -kv[1])]
                       for kind, cats in by_category.items()},
    }
