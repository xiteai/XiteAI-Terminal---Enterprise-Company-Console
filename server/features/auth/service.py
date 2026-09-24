"""Signing in, and the 'who am I' payload the console boots from."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ...access import catalog, levels, perms, shaping
from ...core import audit, clock, config, db, notify, settings
from ...security import lockout, mfa, passwords, sessions
from ..demo import seed as demo
from ..people import cards
from ..products import service as products

BAD = "That email and password don't match."


class NeedCode(Exception):
    def __init__(self, message: str):
        self.message = message

    def response(self) -> JSONResponse:
        return JSONResponse({"detail": self.message, "need_code": True}, status_code=401)


def sign_in(conn, email_raw: str, password: str, code: str, ip: str, user_agent: str) -> tuple[dict, str]:
    email = config.work_email(email_raw)
    if lockout.locked(conn, email, ip):
        raise HTTPException(429, f"Too many attempts. Try again in {config.LOCKOUT_WINDOW_MIN} minutes.")
    row = db.strip(conn["staff"].find_one({"email": email, "is_demo": False}, collation=db.CASE_INSENSITIVE))
    if not row:
        passwords.burn_time(password)
        lockout.record(conn, email, ip, False)
        raise HTTPException(401, BAD)
    if not passwords.verify_password(password, row["password_hash"]):
        lockout.record(conn, email, ip, False)
        audit.record(conn, row, "auth.failed", email, "wrong password", ip)
        raise HTTPException(401, BAD)
    if row["status"] == "deactivated":
        raise HTTPException(403, "This account has been deactivated. Speak to your manager or HR.")
    with_code = mfa.enrolled(row)
    if with_code:
        if not code:
            raise NeedCode("Enter the 6-digit code from your authenticator app.")
        if not mfa.check(row, code):
            lockout.record(conn, email, ip, False)
            raise NeedCode("That code didn't work. Codes change every 30 seconds.")
    lockout.record(conn, email, ip, True)
    token = sessions.create(conn, row["id"], user_agent, ip, mfa=with_code)
    conn["staff"].update_one({"_id": row["id"]}, {"$set": {"last_login_at": db.now_iso()}})
    audit.record(conn, row, "auth.login", email, "", ip)
    return row, token


def _approvable_pending(conn, a: dict) -> int:
    if "people.approve" not in a["perms"]:
        return 0
    return sum(1 for r in conn["staff"].find({"status": "pending", **settings.demo_filter(conn)}, {"level": 1})
               if levels.outranks(a["eff_level"], r["level"]))


def _waiting(conn, a: dict) -> dict:
    """What a pending or declined person sees instead of the console."""
    approver_levels = [levels.LABEL[k] for k in levels.KEYS if k != "founder"     # the founder is named separately
                       and levels.outranks(k, a["level"]) and "people.approve" in perms.effective(conn, k)]
    founder = conn["staff"].find_one({"level": "founder", "status": "active"}, {"display_name": 1})
    decider = conn["staff"].find_one({"_id": a["decided_by"]}, {"display_name": 1, "level": 1}) \
        if a["decided_by"] else None
    return {
        "requested_level": a["level"],
        "requested_label": levels.LABEL[a["level"]],
        "requested_at": a["created_at"],
        "approver_levels": approver_levels,
        "founder_name": founder["display_name"] if founder else "the Founder",
        "decided_at": a["decided_at"],
        "decision_note": a["decision_note"],
        "decided_by": (f"{decider['display_name']} ({levels.LABEL[decider['level']]})" if decider else None),
    }


def _unread_count(conn, a: dict) -> int:
    return conn["notifications"].count_documents({**notify.visible_filter(conn, a["id"]), "read_at": None})


def me(conn, a: dict) -> dict:
    eff = a["eff_level"]
    user = cards.card(a)
    user.update({"status": a["status"], "must_change_pw": bool(a["must_change_pw"]), "source": a["source"],
                 "is_founder": a["level"] == "founder"})
    out = {
        "user": user,
        "level": eff,
        "level_label": levels.LABEL[eff],
        "previewing": a["previewing"],
        "perms": sorted(a["perms"]),
        "customer_visibility": shaping.describe(a["perms"]),
        "levels": levels.as_list(),
        "perm_labels": {k: label for _, group in catalog.CATALOG for k, label, _ in group},
        "product": {"name": config.PRODUCT, "full": config.PRODUCT_FULL, "company": config.COMPANY,
                    "latest_version": config.LATEST_VERSION},
        "email_domain": config.EMAIL_DOMAIN,
        "founder_totp": bool(config.FOUNDER_TOTP_SECRET),
        "authenticator": {"on": mfa.enrolled(a), "from_env": mfa.from_env(a), "this_session": bool(a.get("mfa"))},
        "tz_label": clock.LABEL,
    }
    if a["status"] == "active":
        out["counts"] = {"unread": _unread_count(conn, a), "pending_requests": _approvable_pending(conn, a)}
        out["show_demo"] = settings.show_demo(conn)
        out["has_demo"] = demo.present(conn)
        out["products"] = [products.card(r) for r in conn["products"].find(settings.demo_filter(conn))
                           .sort([("is_demo", 1), ("created_at", 1)])]
    else:
        out["waiting"] = _waiting(conn, a)
    return out
