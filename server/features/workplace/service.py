"""The rules behind the Workplace.

Who may decide what is the whole point here, so it is stated once, in `decide`:
you need the permission for that kind of request, you must outrank the person
who filed it, and you can never decide your own. Everything else — balances,
caps, overlaps — is checked when the request is filed, so a pending request is
always one that was legal to file."""
from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import HTTPException

from ...access import levels, perms
from ...core import audit, config, db, notify
from . import store

# ── What can be filed ─────────────────────────────────────────────────────────

LEAVE_TYPES = {"annual": "Annual leave", "sick": "Sick leave", "casual": "Casual leave",
               "maternity": "Maternity leave", "paternity": "Paternity leave", "bereavement": "Bereavement leave",
               "comp_off": "Compensatory off", "unpaid": "Unpaid leave"}
# A year's allowance. Unpaid leave has none: that is the point of it. Maternity
# follows the Maternity Benefit Act (26 weeks for the first two children);
# comp-off isn't capped here since it's earned per instance, not accrued yearly.
ENTITLEMENT = {"annual": config.LEAVE_DAYS_ANNUAL, "sick": config.LEAVE_DAYS_SICK,
               "casual": config.LEAVE_DAYS_CASUAL, "maternity": 182, "paternity": config.LEAVE_DAYS_PATERNITY,
               "bereavement": config.LEAVE_DAYS_BEREAVEMENT, "comp_off": None, "unpaid": None}
# Annual leave is planned, so it cannot start in the past. The rest can: you
# do not file sick leave before you are ill.
PLANNED_AHEAD = {"annual"}
BACKDATE_DAYS = 30
MAX_SPAN_DAYS = {"maternity": 200, "unpaid": 365}          # everything else defaults to 90

EXPENSE_CATEGORIES = {"travel": "Travel", "meals": "Meals", "software": "Software", "hardware": "Hardware",
                      "training": "Training", "other": "Other"}
ASSET_ITEMS = {"laptop": "Laptop", "monitor": "Monitor", "phone": "Phone", "desk": "Desk and chair",
               "peripherals": "Keyboard, mouse, headset", "other": "Other"}
ASSET_ACTIONS = {"new": "New", "replacement": "Replacement"}

TICKET_CATEGORIES = {"laptop": "Laptop or desktop", "access": "Access and accounts", "software": "Software",
                     "network": "Network and VPN", "other": "Something else"}
TICKET_STATUS = {"open": 0, "in_progress": 1, "resolved": 2, "closed": 3}
TICKET_PRIORITY = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

KINDS = ("leave", "expense", "asset")
# One permission per kind. Holding it is half of being allowed to decide; the
# other half is outranking whoever filed it.
DECIDE_PERM = {"leave": "leave.approve", "expense": "expenses.approve", "asset": "assets.approve"}
KIND_LABEL = {"leave": "leave", "expense": "expense claim", "asset": "asset request"}


# ── People (they live in MongoDB; only their ids are in our tables) ────────────

def _people(conn, ids) -> dict[int, dict]:
    wanted = sorted({i for i in ids if i})
    if not wanted:
        return {}
    found = conn["staff"].find({"id": {"$in": wanted}},
                               {"id": 1, "display_name": 1, "title": 1, "level": 1, "department": 1})
    return {r["id"]: {"id": r["id"], "name": r["display_name"], "title": r.get("title", ""),
                      "level": r["level"], "department": r.get("department", "")} for r in found}


def _person(conn, staff_id: int) -> dict:
    who = _people(conn, [staff_id]).get(staff_id)
    if not who:
        raise HTTPException(404, "That person is no longer on the team.")
    return who


# ── Dates and money ───────────────────────────────────────────────────────────

def _day(value: str, what: str) -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        raise HTTPException(400, f"{what} isn't a real date.") from None


def _rupees_to_paise(amount) -> int:
    try:
        paise = int(round(float(amount) * 100))
    except (TypeError, ValueError):
        raise HTTPException(400, "That amount isn't a number.") from None
    if paise <= 0:
        raise HTTPException(400, "An expense has to be for more than nothing.")
    if paise > config.EXPENSE_MAX_RUPEES * 100:
        raise HTTPException(400, f"A single claim can't be over ₹{config.EXPENSE_MAX_RUPEES:,}. Split it, or talk to finance.")
    return paise


# ── Shaping ───────────────────────────────────────────────────────────────────

def shape(row: dict, who: dict | None = None, decider: dict | None = None) -> dict:
    out = {"id": row["id"], "kind": row["kind"], "status": row["status"], "title": row["title"],
           "note": row["note"], "created_at": row["created_at"], "decided_at": row["decided_at"],
           "decision_note": row["decision_note"], "staff": who, "decided_by": decider,
           "is_demo": bool(row["is_demo"])}
    if row["kind"] == "leave":
        out |= {"leave_type": row["leave_type"], "leave_label": LEAVE_TYPES.get(row["leave_type"], row["leave_type"]),
                "start_date": row["start_date"], "end_date": row["end_date"], "days": row["days"],
                "dates": json.loads(row["dates_json"] or "[]")}
    elif row["kind"] == "expense":
        out |= {"category": row["category"], "category_label": EXPENSE_CATEGORIES.get(row["category"], row["category"]),
                "amount_paise": row["amount_paise"], "spent_on": row["spent_on"]}
    else:
        out |= {"category": row["category"], "category_label": ASSET_ITEMS.get(row["category"], row["category"]),
                "quantity": row["quantity"], "asset_action": row["asset_action"],
                "action_label": ASSET_ACTIONS.get(row["asset_action"], row["asset_action"]),
                "fine_paise": row["fine_paise"]}
    return out


def _shape_all(conn, rows: list[dict]) -> list[dict]:
    people = _people(conn, [r["staff_id"] for r in rows] + [r["decided_by"] for r in rows])
    return [shape(r, people.get(r["staff_id"]), people.get(r["decided_by"])) for r in rows]


# ── Filing ────────────────────────────────────────────────────────────────────

def _holiday_dates(conn) -> set[str]:
    return {r["date"] for r in store.rows(f"SELECT date FROM work_holidays WHERE 1=1{store.demo_sql(conn)}")}


def _check_leave(conn, a: dict, body: dict) -> dict:
    kind = (body.get("leave_type") or "").strip()
    if kind not in LEAVE_TYPES:
        raise HTTPException(400, "Pick a kind of leave.")
    raw = body.get("dates") or []
    if not isinstance(raw, list) or not raw:
        raise HTTPException(400, "Pick at least one day on the calendar.")
    try:
        picked = sorted({date.fromisoformat(str(d).strip()) for d in raw})
    except ValueError:
        raise HTTPException(400, "One of those dates isn't real.") from None

    holidays = _holiday_dates(conn)
    for d in picked:
        if d.weekday() >= 5:
            raise HTTPException(400, f"{d.strftime('%d %b')} is a weekend — nothing to take off.")
        if d.isoformat() in holidays:
            raise HTTPException(400, f"{d.strftime('%d %b')} is already a holiday.")

    start, end = picked[0], picked[-1]
    span_cap = MAX_SPAN_DAYS.get(kind, 90)
    if (end - start).days > span_cap:
        raise HTTPException(400, f"That spans more than {span_cap} days. File it in parts.")
    today = date.today()
    if kind in PLANNED_AHEAD and start < today:
        raise HTTPException(400, "Annual leave has to be asked for before it starts.")
    if start < today - timedelta(days=BACKDATE_DAYS):
        raise HTTPException(400, f"That's more than {BACKDATE_DAYS} days ago. Ask HR to record it.")
    if start > today + timedelta(days=365):
        raise HTTPException(400, "That's more than a year away.")

    existing = store.rows(
        "SELECT dates_json FROM work_requests WHERE staff_id = ? AND kind = 'leave' "
        "AND status IN ('pending','approved') AND start_date <= ? AND end_date >= ?",
        (a["id"], end.isoformat(), start.isoformat()))
    taken_days = {d for r in existing for d in json.loads(r["dates_json"] or "[]")}
    clash = {d.isoformat() for d in picked} & taken_days
    if clash:
        raise HTTPException(409, f"You already have leave booked on {sorted(clash)[0]}.")

    days = len(picked)
    allowed = ENTITLEMENT[kind]
    if allowed is not None:
        left = allowed - _days_taken(a["id"], kind, start.year)
        if days > left:
            raise HTTPException(400, f"That's {days} days and you have {left:g} left of your {LEAVE_TYPES[kind].lower()}.")

    span = f"{start.strftime('%d %b')} – {end.strftime('%d %b')}" if start != end else start.strftime("%d %b")
    return {"leave_type": kind, "start_date": start.isoformat(), "end_date": end.isoformat(),
            "dates_json": json.dumps([d.isoformat() for d in picked]), "days": days,
            "title": f"{LEAVE_TYPES[kind]}, {days} day{'s' if days != 1 else ''} ({span})"}


def _check_expense(conn, a: dict, body: dict) -> dict:
    category = (body.get("category") or "").strip()
    if category not in EXPENSE_CATEGORIES:
        raise HTTPException(400, "Pick what the money went on.")
    paise = _rupees_to_paise(body.get("amount"))
    spent = _day(body.get("spent_on"), "The date it was spent")
    today = date.today()
    if spent > today:
        raise HTTPException(400, "That date is in the future.")
    if spent < today - timedelta(days=180):
        raise HTTPException(400, "Claims close after six months.")
    return {"category": category, "amount_paise": paise, "spent_on": spent.isoformat(),
            "title": f"{EXPENSE_CATEGORIES[category]}, ₹{paise / 100:,.2f}"}


def _check_asset(conn, a: dict, body: dict) -> dict:
    category = (body.get("category") or "").strip()
    if category not in ASSET_ITEMS:
        raise HTTPException(400, "Pick what you need.")
    action = (body.get("asset_action") or "new").strip()
    if action not in ASSET_ACTIONS:
        raise HTTPException(400, "Pick whether this is new or a replacement.")
    try:
        quantity = int(body.get("quantity") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "How many isn't a number.") from None
    if not 1 <= quantity <= 10:
        raise HTTPException(400, "Ask for between one and ten. More than that needs a conversation.")
    label = ASSET_ITEMS[category] + (f" × {quantity}" if quantity > 1 else "")
    return {"category": category, "quantity": quantity, "asset_action": action,
            "title": f"{label} ({ASSET_ACTIONS[action]})" if action == "replacement" else label}


_CHECK = {"leave": _check_leave, "expense": _check_expense, "asset": _check_asset}


def file_request(conn, a: dict, kind: str, body: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if kind not in KINDS:
        raise HTTPException(404, "There's nothing to file of that kind.")
    note = (body.get("note") or "").strip()[:2000]
    if kind != "leave" and not note:
        raise HTTPException(400, "Say what this is for.")
    fields = _CHECK[kind](conn, a, body)

    # Nobody outranks the founder, so there is no one left to ask: filing is
    # the decision. Everyone else's goes to whoever above them can decide it.
    self_approve = a["eff_level"] == "founder"
    now = db.now_iso()
    req_id = store.run(
        "INSERT INTO work_requests (kind, staff_id, status, title, note, leave_type, start_date, end_date, "
        "dates_json, days, category, amount_paise, spent_on, quantity, asset_action, created_at, decided_by, "
        "decided_at, decision_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (kind, a["id"], "approved" if self_approve else "pending", fields["title"], note,
         fields.get("leave_type", ""), fields.get("start_date", ""), fields.get("end_date", ""),
         fields.get("dates_json", "[]"), fields.get("days", 0), fields.get("category", ""),
         fields.get("amount_paise", 0), fields.get("spent_on", ""), fields.get("quantity", 0),
         fields.get("asset_action", "new"), now, a["id"] if self_approve else None,
         now if self_approve else None, "Filed by the founder." if self_approve else "")).lastrowid

    if not self_approve:
        deciders = perms.holders(conn, DECIDE_PERM[kind], above=a["eff_level"])
        notify.send(conn, [i for i in deciders if i != a["id"]], f"workplace.{kind}",
                    f"{a['display_name']} filed {KIND_LABEL[kind]}", fields["title"],
                    "/console/workplace/approvals", req_id)
    audit.record(conn, a, f"workplace.{kind}_filed", fields["title"], note[:120], a["ip"])
    return shape(store.one("SELECT * FROM work_requests WHERE id = ?", (req_id,)), _person(conn, a["id"]))


# ── Deciding ──────────────────────────────────────────────────────────────────

def decide(conn, a: dict, req_id: int, approve: bool, note: str, fine=None) -> dict:
    """The one gate. Everything that can say no about a decision says it here."""
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = store.one("SELECT * FROM work_requests WHERE id = ?", (req_id,))
    if not row:
        raise HTTPException(404, "No request with that number.")
    if row["staff_id"] == a["id"] and a["eff_level"] != "founder":
        raise HTTPException(403, "You can't decide your own request.")
    if row["status"] != "pending":
        who = _people(conn, [row["decided_by"]]).get(row["decided_by"])
        raise HTTPException(409, f"Already {row['status']} by {who['name'] if who else 'someone'}.")
    asker = _person(conn, row["staff_id"])
    if not perms.over(a["eff_level"], a["perms"], DECIDE_PERM[row["kind"]], asker["level"]):
        raise HTTPException(403, "Only someone above that level, with the power to decide, can.")

    fine_paise = 0
    if fine is not None and approve and row["kind"] == "asset" and row["asset_action"] == "replacement":
        fine_paise = _rupees_to_paise(fine) if float(fine) > 0 else 0

    note, now = (note or "").strip()[:500], db.now_iso()
    status = "approved" if approve else "declined"
    changed = store.run("UPDATE work_requests SET status = ?, decided_by = ?, decided_at = ?, decision_note = ?, "
                        "fine_paise = ? WHERE id = ? AND status = 'pending'",
                        (status, a["id"], now, note, fine_paise, req_id)).rowcount
    if not changed:                      # someone else decided it between the read and the write
        raise HTTPException(409, "Someone else just decided this one.")

    notify.clear(conn, f"workplace.{row['kind']}", req_id)
    notify.send(conn, [row["staff_id"]], "workplace.decided",
                f"{a['display_name']} {status} your {KIND_LABEL[row['kind']]}", row["title"],
                f"/console/workplace/{'leave' if row['kind'] == 'leave' else row['kind'] + 's'}", req_id)
    audit.record(conn, a, f"workplace.{row['kind']}_{status}", f"{asker['name']} · {row['title']}", note[:120], a["ip"])
    return shape(store.one("SELECT * FROM work_requests WHERE id = ?", (req_id,)), asker, _person(conn, a["id"]))


def withdraw(conn, a: dict, req_id: int) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = store.one("SELECT * FROM work_requests WHERE id = ?", (req_id,))
    if not row:
        raise HTTPException(404, "No request with that number.")
    if row["staff_id"] != a["id"]:
        raise HTTPException(403, "That isn't yours to withdraw.")
    if row["status"] != "pending":
        raise HTTPException(409, f"That was already {row['status']}.")
    store.run("UPDATE work_requests SET status = 'withdrawn', decided_at = ? WHERE id = ?", (db.now_iso(), req_id))
    notify.clear(conn, f"workplace.{row['kind']}", req_id)
    audit.record(conn, a, f"workplace.{row['kind']}_withdrawn", row["title"], "", a["ip"])
    return shape(store.one("SELECT * FROM work_requests WHERE id = ?", (req_id,)), _person(conn, a["id"]))


# ── Reading ───────────────────────────────────────────────────────────────────

def mine(conn, a: dict, kind: str | None = None) -> list[dict]:
    where, args = ["staff_id = ?"], [a["id"]]
    if kind:
        where.append("kind = ?")
        args.append(kind)
    rows = store.rows(f"SELECT * FROM work_requests WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200", args)
    return _shape_all(conn, rows)


def awaiting(conn, a: dict, kind: str | None = None) -> list[dict]:
    """Pending requests this viewer could actually decide — not merely see."""
    kinds = [kind] if kind else [k for k in KINDS if DECIDE_PERM[k] in a["perms"]]
    kinds = [k for k in kinds if DECIDE_PERM[k] in a["perms"]]
    if not kinds:
        return []
    marks = ",".join("?" * len(kinds))
    rows = store.rows(f"SELECT * FROM work_requests WHERE status = 'pending' AND kind IN ({marks}) "
                      f"AND staff_id != ?{store.demo_sql(conn)} ORDER BY created_at",
                      [*kinds, a["id"]])
    people = _people(conn, [r["staff_id"] for r in rows])
    out = []
    for r in rows:
        who = people.get(r["staff_id"])
        if who and perms.over(a["eff_level"], a["perms"], DECIDE_PERM[r["kind"]], who["level"]):
            out.append(shape(r, who))
    return out


def _days_taken(staff_id: int, leave_type: str, year: int) -> float:
    """Approved and still-pending leave both hold days: you cannot spend the same day twice."""
    return store.scalar(
        "SELECT COALESCE(SUM(days), 0) FROM work_requests WHERE staff_id = ? AND kind = 'leave' "
        "AND leave_type = ? AND status IN ('pending','approved') AND start_date >= ? AND start_date <= ?",
        (staff_id, leave_type, f"{year}-01-01", f"{year}-12-31")) or 0


def balance(conn, a: dict, year: int | None = None) -> dict:
    year = year or date.today().year
    out = []
    for key, label in LEAVE_TYPES.items():
        taken = _days_taken(a["id"], key, year)
        entitled = ENTITLEMENT[key]
        out.append({"key": key, "label": label, "entitled": entitled, "taken": taken,
                    "left": None if entitled is None else entitled - taken})
    return {"year": year, "types": out}


def summary(conn, a: dict) -> dict:
    """What the Workplace landing needs: what's mine, and what's waiting on me."""
    open_mine = store.rows("SELECT kind, COUNT(*) AS n FROM work_requests WHERE staff_id = ? "
                           "AND status = 'pending' GROUP BY kind", (a["id"],))
    tickets_mine = store.scalar("SELECT COUNT(*) FROM work_tickets WHERE staff_id = ? "
                                "AND status IN ('open','in_progress')", (a["id"],)) or 0
    queue = 0
    if "helpdesk.work" in a["perms"]:
        queue = store.scalar(f"SELECT COUNT(*) FROM work_tickets WHERE status IN ('open','in_progress')"
                             f"{store.demo_sql(conn)}") or 0
    return {"pending": {r["kind"]: r["n"] for r in open_mine}, "awaiting_me": len(awaiting(conn, a)),
            "my_tickets": tickets_mine, "queue": queue, "balance": balance(conn, a),
            "can": can_do(a)}


def can_do(a: dict) -> dict:
    live = not a["previewing"]
    return {"file": live, "decide_leave": "leave.approve" in a["perms"] and live,
            "decide_expense": "expenses.approve" in a["perms"] and live,
            "decide_asset": "assets.approve" in a["perms"] and live,
            "helpdesk_work": "helpdesk.work" in a["perms"] and live,
            "pay_all": "pay.all" in a["perms"]}


# ── Helpdesk ──────────────────────────────────────────────────────────────────

def _ticket_shape(row: dict, people: dict) -> dict:
    return {"id": row["id"], "ref": row["ref"], "category": row["category"],
            "category_label": TICKET_CATEGORIES.get(row["category"], row["category"]),
            "subject": row["subject"], "body": row["body"], "status": row["status"],
            "priority": row["priority"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "staff": people.get(row["staff_id"]), "assignee": people.get(row["assignee_id"]),
            "is_demo": bool(row["is_demo"])}


def raise_ticket(conn, a: dict, body: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    category = (body.get("category") or "").strip()
    if category not in TICKET_CATEGORIES:
        raise HTTPException(400, "Pick what this is about.")
    subject = (body.get("subject") or "").strip()[:140]
    detail = (body.get("body") or "").strip()[:4000]
    if len(subject) < 4:
        raise HTTPException(400, "Give it a subject.")
    if not detail:
        raise HTTPException(400, "Say what's happening.")
    priority = (body.get("priority") or "normal").strip()
    if priority not in TICKET_PRIORITY:
        raise HTTPException(400, "Unknown priority.")

    now = db.now_iso()
    with store.tx() as t:
        tid = t.run("INSERT INTO work_tickets (ref, staff_id, category, subject, body, priority, created_at, "
                    "updated_at) VALUES ('',?,?,?,?,?,?,?)",
                    (a["id"], category, subject, detail, priority, now, now)).lastrowid
        t.run("UPDATE work_tickets SET ref = ? WHERE id = ?", (f"WT-{tid:04d}", tid))

    notify.send(conn, [i for i in perms.holders(conn, "helpdesk.work", above="intern") if i != a["id"]],
                "workplace.ticket", f"{a['display_name']} raised a helpdesk ticket", subject,
                f"/console/workplace/helpdesk/{tid}", tid)
    audit.record(conn, a, "workplace.ticket_raised", f"WT-{tid:04d}", subject[:120], a["ip"])
    return _ticket_shape(store.one("SELECT * FROM work_tickets WHERE id = ?", (tid,)), _people(conn, [a["id"]]))


def tickets(conn, a: dict, scope: str, status: str = "") -> list[dict]:
    where, args = [], []
    if scope == "queue":
        if "helpdesk.work" not in a["perms"]:
            raise HTTPException(403, "Your level doesn't work the helpdesk queue.")
    else:
        where.append("staff_id = ?")
        args.append(a["id"])
    if status == "open":
        where.append("status IN ('open','in_progress')")
    elif status in TICKET_STATUS:
        where.append("status = ?")
        args.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else "WHERE 1 = 1"
    rows = store.rows(f"SELECT * FROM work_tickets {clause}{store.demo_sql(conn)} LIMIT 300", args)
    rows.sort(key=lambda r: (TICKET_STATUS[r["status"]] >= 2, TICKET_PRIORITY[r["priority"]], r["updated_at"]))
    people = _people(conn, [r["staff_id"] for r in rows] + [r["assignee_id"] for r in rows])
    return [_ticket_shape(r, people) for r in rows]


def ticket(conn, a: dict, ticket_id: int) -> dict:
    row = store.one("SELECT * FROM work_tickets WHERE id = ?", (ticket_id,))
    if not row:
        raise HTTPException(404, "No ticket with that number.")
    works = "helpdesk.work" in a["perms"]
    if row["staff_id"] != a["id"] and not works:
        raise HTTPException(403, "That ticket isn't yours.")
    notes = store.rows("SELECT * FROM work_ticket_notes WHERE ticket_id = ? ORDER BY at", (ticket_id,))
    people = _people(conn, [row["staff_id"], row["assignee_id"], *[n["staff_id"] for n in notes]])
    return {"ticket": _ticket_shape(row, people),
            "notes": [{"id": n["id"], "body": n["body"], "at": n["at"], "staff": people.get(n["staff_id"])}
                      for n in notes],
            "can": {"reply": not a["previewing"], "work": works and not a["previewing"]}}


def add_note(conn, a: dict, ticket_id: int, body: str) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    body = (body or "").strip()[:4000]
    if not body:
        raise HTTPException(400, "Nothing to add.")
    row = store.one("SELECT * FROM work_tickets WHERE id = ?", (ticket_id,))
    if not row:
        raise HTTPException(404, "No ticket with that number.")
    works = "helpdesk.work" in a["perms"]
    if row["staff_id"] != a["id"] and not works:
        raise HTTPException(403, "That ticket isn't yours.")
    if row["status"] == "closed":
        raise HTTPException(409, "That ticket is closed.")
    now = db.now_iso()
    with store.tx() as t:
        t.run("INSERT INTO work_ticket_notes (ticket_id, staff_id, body, at) VALUES (?,?,?,?)",
              (ticket_id, a["id"], body, now))
        t.run("UPDATE work_tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
    tell = row["assignee_id"] if row["staff_id"] == a["id"] else row["staff_id"]
    notify.send(conn, [tell] if tell and tell != a["id"] else [], "workplace.ticket_note",
                f"{a['display_name']} replied on {row['ref']}", body[:120],
                f"/console/workplace/helpdesk/{ticket_id}", ticket_id)
    return ticket(conn, a, ticket_id)


def update_ticket(conn, a: dict, ticket_id: int, changes: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = store.one("SELECT * FROM work_tickets WHERE id = ?", (ticket_id,))
    if not row:
        raise HTTPException(404, "No ticket with that number.")
    works = "helpdesk.work" in a["perms"]
    # The person who raised it may close it or reopen it; the rest is the queue's.
    if not works:
        if row["staff_id"] != a["id"]:
            raise HTTPException(403, "That ticket isn't yours.")
        if set(changes) - {"status"} or changes.get("status") not in {"closed", "open"}:
            raise HTTPException(403, "You can close your ticket or reopen it, nothing else.")
    if changes.get("assignee_id") is not None:
        who = _person(conn, changes["assignee_id"])
        if "helpdesk.work" not in perms.effective(conn, who["level"]):
            raise HTTPException(400, f"{who['name']} doesn't work the helpdesk queue.")

    sets = ", ".join(f"{k} = ?" for k in changes)
    store.run(f"UPDATE work_tickets SET {sets}, updated_at = ? WHERE id = ?",
              [*changes.values(), db.now_iso(), ticket_id])
    audit.record(conn, a, "workplace.ticket_updated", row["ref"],
                 ", ".join(f"{k}={v}" for k, v in changes.items())[:120], a["ip"])
    return ticket(conn, a, ticket_id)


# ── Holidays ──────────────────────────────────────────────────────────────────
# Only the fixed-date national ones are seeded — festival dates move every
# year and aren't guessed here. Whoever can decide leave keeps this list real.

def holidays(conn, year: int | None = None) -> list[dict]:
    year = year or date.today().year
    rows = store.rows(f"SELECT * FROM work_holidays WHERE date LIKE ?{store.demo_sql(conn)} ORDER BY date",
                      (f"{year}-%",))
    return [{"id": r["id"], "date": r["date"], "label": r["label"], "is_demo": bool(r["is_demo"])} for r in rows]


def add_holiday(conn, a: dict, day: str, label: str) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if "leave.approve" not in a["perms"]:
        raise HTTPException(403, "Your level can't manage holidays.")
    d = _day(day, "That date")
    label = (label or "").strip()[:80]
    if len(label) < 2:
        raise HTTPException(400, "Give the holiday a name.")
    try:
        hid = store.run("INSERT INTO work_holidays (date, label, created_by) VALUES (?,?,?)",
                        (d.isoformat(), label, a["id"])).lastrowid
    except Exception:
        raise HTTPException(409, f"{d.strftime('%d %b')} is already a holiday.") from None
    audit.record(conn, a, "workplace.holiday_added", label, d.isoformat(), a["ip"])
    return {"id": hid, "date": d.isoformat(), "label": label, "is_demo": False}


def remove_holiday(conn, a: dict, holiday_id: int) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    if "leave.approve" not in a["perms"]:
        raise HTTPException(403, "Your level can't manage holidays.")
    row = store.one("SELECT * FROM work_holidays WHERE id = ?", (holiday_id,))
    if not row:
        raise HTTPException(404, "No holiday with that id.")
    store.run("DELETE FROM work_holidays WHERE id = ?", (holiday_id,))
    audit.record(conn, a, "workplace.holiday_removed", row["label"], row["date"], a["ip"])


# ── Pay ───────────────────────────────────────────────────────────────────────

def payslips(conn, a: dict, staff_id: int | None = None) -> dict:
    """Your own, always. Anyone else's only with pay.all, and never above you."""
    target = a["id"]
    if staff_id and staff_id != a["id"]:
        if "pay.all" not in a["perms"]:
            raise HTTPException(403, "Your level can only see your own payslips.")
        who = _person(conn, staff_id)
        if not levels.outranks(a["eff_level"], who["level"]):
            raise HTTPException(403, "Only someone above that level can see their pay.")
        target = staff_id
    rows = store.rows(f"SELECT * FROM work_payslips WHERE staff_id = ?{store.demo_sql(conn)} "
                      f"ORDER BY period DESC LIMIT 36", (target,))
    return {"items": [{"id": r["id"], "period": r["period"], "gross_paise": r["gross_paise"],
                       "deductions_paise": r["deductions_paise"], "net_paise": r["net_paise"],
                       "issued_at": r["issued_at"]} for r in rows],
            "staff": _people(conn, [target]).get(target), "can_see_others": "pay.all" in a["perms"]}
