"""Field rules for the sign-up form. Each returns the clean value or raises a
400 whose message the form shows next to the field it names."""
from __future__ import annotations

import re
from datetime import date

from fastapi import HTTPException

from ...access import levels
from ...access.shaping import age_from_dob
from . import options

LOCAL = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,30}[a-z0-9])?$")
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
PHONE = re.compile(r"^\+?[0-9 ()-]{7,20}$")


class FieldError(HTTPException):
    def __init__(self, field: str, message: str):
        super().__init__(400, {"field": field, "message": message})


def local_part(value: str) -> str:
    v = (value or "").strip().lower()
    if not LOCAL.match(v) or ".." in v:
        raise FieldError("local", "Use letters, numbers, dots, dashes or underscores, like priya.sharma.")
    return v


def one_of(field: str, value: str, allowed: list[str], what: str) -> str:
    if value not in allowed:
        raise FieldError(field, f"Pick {what} from the list.")
    return value


def level(value: str) -> str:
    if value not in levels.JOINABLE:
        raise FieldError("level", "Pick the level you're joining at.")
    return value


def iso_date(field: str, value: str, required: bool) -> str:
    v = (value or "").strip()
    if not v and not required:
        return ""
    try:
        return date.fromisoformat(v).isoformat()
    except ValueError:
        raise FieldError(field, "Use a real date.")


def dob(value: str) -> str:
    v = iso_date("dob", value, True)
    age = age_from_dob(v)
    if age is None or age < 16 or age > 90:
        raise FieldError("dob", "That date of birth doesn't look right.")
    return v


def phone(field: str, value: str) -> str:
    v = (value or "").strip()
    if not PHONE.match(v) or sum(c.isdigit() for c in v) < 7:
        raise FieldError(field, "Enter a phone number with its country code, like +91 98765 43210.")
    return v


def email(field: str, value: str) -> str:
    v = (value or "").strip()
    if not EMAIL.match(v):
        raise FieldError(field, "That email address doesn't look right.")
    return v


def url(field: str, value: str) -> str:
    v = (value or "").strip()
    if v and not re.match(r"^https?://\S+\.\S+", v):
        raise FieldError(field, "Paste the full link, starting with https://")
    return v


def small_int(field: str, value: str, lo: int, hi: int) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if not v.isdigit() or not lo <= int(v) <= hi:
        raise FieldError(field, f"Enter a number between {lo} and {hi}.")
    return v


def text(field: str, value: str, required: bool, what: str) -> str:
    v = (value or "").strip()
    if required and len(v) < 2:
        raise FieldError(field, f"Add {what}.")
    return v


_PHOTO_RE = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,")
PHOTO_MAX_CHARS = 400_000          # a resized, compressed thumbnail comfortably fits


def photo(value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise FieldError("photo", "A photo is required to join.")
    if not _PHOTO_RE.match(v):
        raise FieldError("photo", "That doesn't look like a photo. Try again.")
    if len(v) > PHOTO_MAX_CHARS:
        raise FieldError("photo", "That photo is too large. Try a smaller one.")
    return v


def department(value: str) -> str:
    return one_of("department", value, options.DEPARTMENTS, "a department")


def employment_type(value: str) -> str:
    return one_of("employment_type", value, options.EMPLOYMENT_TYPES, "how you're employed")
