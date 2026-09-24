"""Customer data cut down to what the viewer's permissions allow. Done here,
before anything leaves the server."""
from __future__ import annotations

from datetime import date, datetime, timezone


def age_from_dob(dob: str | None, today: date | None = None) -> int | None:
    if not dob:
        return None
    try:
        d = date.fromisoformat(dob)
    except ValueError:
        return None
    today = today or datetime.now(timezone.utc).date()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


BANDS = ["Under 18", "18-24", "25-34", "35-44", "45-54", "55+"]


def age_band(age: int | None) -> str | None:
    if age is None:
        return None
    if age < 18:
        return "Under 18"
    for lo, hi in ((18, 24), (25, 34), (35, 44), (45, 54)):
        if lo <= age <= hi:
            return f"{lo}-{hi}"
    return "55+"


def partial_name(name: str | None) -> str | None:
    if not name:
        return None
    parts = name.split()
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


def person(row: dict, perms: set[str]) -> dict:
    consented = bool(row.get("consent_profile"))
    name, dob = (row.get("user_name"), row.get("user_dob")) if consented else (None, None)
    age = age_from_dob(dob)
    out: dict = {"consented": consented}
    if "cust.name" in perms:
        out["name"] = name
    elif "cust.name_partial" in perms:
        out["name"] = partial_name(name)
    if "cust.dob" in perms:
        out["dob"] = dob
    if "cust.age" in perms:
        out["age"] = age
    if "cust.age" in perms or "cust.age_band" in perms:
        out["age_band"] = age_band(age)
    return out


def install(row: dict, perms: set[str]) -> dict:
    out = {k: row[k] for k in ("id", "code", "status", "first_seen", "last_seen", "app_version", "os_version",
                               "device_type", "update_state", "crash_count_7d", "checkin_count")}
    out["consent_usage"] = bool(row["consent_usage"])
    out["is_demo"] = bool(row["is_demo"])
    out["person"] = person(row, perms)
    if "cust.region" in perms:
        out["region"], out["timezone"] = row["region"], row["timezone"]
    if "cust.fingerprints" in perms:
        out["hardware_hash"], out["key_fingerprint"], out["locale"] = (
            row["hardware_hash"], row["key_fingerprint"], row["locale"])
    return out


def describe(perms: set[str]) -> str:
    """One sentence for the console: what this viewer sees about customers."""
    bits = []
    if "cust.name" in perms:
        bits.append("full names")
    elif "cust.name_partial" in perms:
        bits.append("first names")
    if "cust.dob" in perms:
        bits.append("dates of birth")
    if "cust.age" in perms:
        bits.append("ages")
    elif "cust.age_band" in perms:
        bits.append("age bands")
    if "cust.region" in perms:
        bits.append("regions")
    if "cust.fingerprints" in perms:
        bits.append("machine fingerprints")
    if not bits:
        return "You see installs as codes, with no personal details."
    return "You see customers' " + (", ".join(bits[:-1]) + " and " + bits[-1] if len(bits) > 1 else bits[0]) + "."
