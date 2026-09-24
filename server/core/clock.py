"""The console's display clock: days and hours are bucketed in this offset
(IST by default, TC_DISPLAY_UTC_OFFSET in .env), not in UTC."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import config, db


def _parse_offset(text: str) -> timedelta:
    sign = -1 if text.startswith("-") else 1
    hours, _, minutes = text.lstrip("+-").partition(":")
    try:
        return sign * timedelta(hours=int(hours or 0), minutes=int(minutes or 0))
    except ValueError:
        return timedelta(hours=5, minutes=30)


OFFSET = _parse_offset(config.DISPLAY_UTC_OFFSET)
LABEL = config.DISPLAY_TZ_LABEL


def local(ts: str) -> datetime:
    """A stored UTC timestamp as naive display-clock time."""
    return (db.parse_iso(ts) + OFFSET).replace(tzinfo=None)


def today():
    return (datetime.now(timezone.utc) + OFFSET).date()
