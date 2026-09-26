"""What the Home feed shows: who's celebrating a birthday soon, and what the
company has posted about itself — events (with results, once they've
happened) and news (an achievement, funding, anything worth telling everyone).

Birthdays are never stored anywhere of their own: a person's date of birth
already lives in their profile (asked for once, at sign-up), so the feed
works it out fresh each time rather than keeping a second copy that could
drift from the real one."""
from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import HTTPException

from ...core import audit, db, notify, settings

KINDS = {"news": "News", "achievement": "Achievement", "funding": "Funding", "event": "Event"}
BIRTHDAY_WINDOW_DAYS = 14


def _profile_dob(row: dict) -> str:
    try:
        return (json.loads(row.get("profile_json") or "{}") or {}).get("dob", "")
    except ValueError:
        return ""


def birthdays(conn, within_days: int = BIRTHDAY_WINDOW_DAYS) -> list[dict]:
    today = date.today()
    out = []
    for row in conn["staff"].find({"status": "active", **settings.demo_filter(conn)},
                                  {"id": 1, "display_name": 1, "preferred_name": 1, "department": 1, "title": 1,
                                   "profile_json": 1, "avatar_url": 1}):
        dob = _profile_dob(row)
        if not dob:
            continue
        try:
            born = date.fromisoformat(dob)
        except ValueError:
            continue
        this_year = born.replace(year=today.year)
        if this_year < today:
            this_year = this_year.replace(year=today.year + 1)
        away = (this_year - today).days
        if 0 <= away <= within_days:
            out.append({"id": row["id"], "name": row.get("preferred_name") or row["display_name"].split()[0],
                        "display_name": row["display_name"], "department": row.get("department", ""),
                        "title": row.get("title", ""), "avatar_url": row.get("avatar_url", ""),
                        "date": this_year.isoformat(), "days_away": away, "turns": this_year.year - born.year})
    out.sort(key=lambda b: b["days_away"])
    return out


def _shape(row: dict, people: dict) -> dict:
    return {"id": row["id"], "kind": row["kind"], "title": row["title"], "body": row["body"],
            "event_date": row.get("event_date", ""), "result": row.get("result", ""),
            "posted_at": row["posted_at"], "posted_by": people.get(row["posted_by"]),
            "is_demo": bool(row.get("is_demo", False))}


def _people(conn, ids) -> dict[int, dict]:
    wanted = sorted({i for i in ids if i})
    if not wanted:
        return {}
    return {r["id"]: {"id": r["id"], "name": r["display_name"], "title": r.get("title", "")}
           for r in conn["staff"].find({"id": {"$in": wanted}}, {"id": 1, "display_name": 1, "title": 1})}


def timeline(conn, limit: int = 40) -> dict:
    """Everything posted, newest first, split the way Home reads it: events
    that haven't happened yet, events that have (with their result, if one
    was added), and the rest as news."""
    rows = list(conn["announcements"].find({**settings.demo_filter(conn)}).sort("posted_at", -1).limit(limit))
    people = _people(conn, [r["posted_by"] for r in rows])
    shaped = [_shape(r, people) for r in rows]
    today = date.today().isoformat()
    upcoming = [s for s in shaped if s["kind"] == "event" and s["event_date"] and s["event_date"] >= today]
    results = [s for s in shaped if s["kind"] == "event" and (s["event_date"] < today or not s["event_date"]) and s["result"]]
    news = [s for s in shaped if s["kind"] != "event"]
    upcoming.sort(key=lambda s: s["event_date"])
    return {"upcoming": upcoming, "results": results, "news": news}


def post(conn, a: dict, body: dict) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    kind = (body.get("kind") or "").strip()
    if kind not in KINDS:
        raise HTTPException(400, "Pick what kind of post this is.")
    title = (body.get("title") or "").strip()[:140]
    text = (body.get("body") or "").strip()[:2000]
    if len(title) < 3:
        raise HTTPException(400, "Give it a headline.")
    event_date = (body.get("event_date") or "").strip()
    if kind == "event":
        if not event_date:
            raise HTTPException(400, "Events need a date.")
        try:
            date.fromisoformat(event_date)
        except ValueError:
            raise HTTPException(400, "That date isn't real.") from None
    elif event_date:
        event_date = ""

    now = db.now_iso()
    aid = db.next_id(conn, "announcements")
    conn["announcements"].insert_one({"_id": aid, "id": aid, "kind": kind, "title": title, "body": text,
                                      "event_date": event_date, "result": "", "posted_by": a["id"],
                                      "posted_at": now, "is_demo": False})
    live = conn["staff"].distinct("id", {"status": "active", **settings.demo_filter(conn)})
    notify.send(conn, [i for i in live if i != a["id"]], f"feed.{kind}", title,
                f"Posted by {a['display_name']}", "/console", aid)
    audit.record(conn, a, "feed.posted", title, kind, a["ip"])
    return _shape(conn["announcements"].find_one({"_id": aid}), _people(conn, [a["id"]]))


def add_result(conn, a: dict, post_id: int, result: str) -> dict:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = conn["announcements"].find_one({"_id": post_id})
    if not row:
        raise HTTPException(404, "No post with that id.")
    if row["kind"] != "event":
        raise HTTPException(400, "Only events take a result.")
    result = (result or "").strip()[:2000]
    if not result:
        raise HTTPException(400, "Say what happened.")
    conn["announcements"].update_one({"_id": post_id}, {"$set": {"result": result}})
    audit.record(conn, a, "feed.result_added", row["title"], "", a["ip"])
    return _shape(conn["announcements"].find_one({"_id": post_id}), _people(conn, [row["posted_by"]]))


def remove(conn, a: dict, post_id: int) -> None:
    if a["previewing"]:
        raise HTTPException(403, "Preview is read-only.")
    row = conn["announcements"].find_one({"_id": post_id})
    if not row:
        raise HTTPException(404, "No post with that id.")
    conn["announcements"].delete_one({"_id": post_id})
    notify.clear(conn, f"feed.{row['kind']}", post_id)
    audit.record(conn, a, "feed.removed", row["title"], "", a["ip"])
