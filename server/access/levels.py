"""The seven levels of the company, ranked. A level only ever acts on the levels
below it; nobody acts on the founder."""
from __future__ import annotations

LEVELS = [  # key, label, rank
    ("founder", "Founder", 100),
    ("vp", "Vice President", 80),
    ("director", "Director", 60),
    ("hr", "HR", 50),
    ("manager", "Manager", 40),
    ("employee", "Employee", 20),
    ("intern", "Intern", 10),
]
KEYS = [k for k, _, _ in LEVELS]
LABEL = {k: label for k, label, _ in LEVELS}
RANK = {k: rank for k, _, rank in LEVELS}
JOINABLE = [k for k in KEYS if k != "founder"]


def outranks(a: str, b: str) -> bool:
    return RANK.get(a, 0) > RANK.get(b, 0)


def below(level: str) -> list[str]:
    return [k for k in KEYS if outranks(level, k)]


def as_list() -> list[dict]:
    return [{"key": k, "label": label, "rank": rank} for k, label, rank in LEVELS]


def new_staff_defaults() -> dict:
    """Every field a `staff` document needs, beyond the ones each caller sets
    itself (id, email, display_name, level, ...). MongoDB has no column
    DEFAULT: a document that leaves one of these out just doesn't have it, so
    every place that creates a staff row starts from this, then overrides."""
    return {
        "preferred_name": "", "department": "", "employment_type": "", "start_date": "", "reports_to": None,
        "status": "pending", "source": "signup", "profile_json": "{}", "signup_ip": "", "decided_by": None,
        "decided_at": None, "decision_note": "", "last_login_at": None, "must_change_pw": False,
        "totp_secret": "", "totp_pending": "", "code_paused": False, "is_demo": False,
    }
