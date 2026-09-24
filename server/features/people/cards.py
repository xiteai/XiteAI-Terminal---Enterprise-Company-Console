"""How a team member is shown: a card for the directory, and the full profile
(everything asked at sign-up) for people who hold people.profiles."""
from __future__ import annotations

import json

from ...access import levels


def initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"


def card(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "preferred_name": row["preferred_name"] or row["display_name"].split()[0],
        "initials": initials(row["display_name"]),
        "level": row["level"],
        "level_label": levels.LABEL[row["level"]],
        "title": row["title"],
        "department": row["department"],
        "employment_type": row["employment_type"],
        "start_date": row["start_date"],
        "reports_to": row["reports_to"],
        "status": row["status"],
        "is_demo": bool(row["is_demo"]),
    }


def full(row: dict) -> dict:
    out = card(row)
    try:
        profile = json.loads(row["profile_json"] or "{}")
    except ValueError:
        profile = {}
    out.update({
        "profile": profile,
        "requested_level": row["requested_level"],
        "requested_label": levels.LABEL.get(row["requested_level"], ""),
        "created_at": row["created_at"],
        "decided_at": row["decided_at"],
        "decision_note": row["decision_note"],
        "last_login_at": row["last_login_at"],
        "source": row["source"],
    })
    return out
