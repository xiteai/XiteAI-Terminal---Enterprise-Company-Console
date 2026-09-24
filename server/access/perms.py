"""What a level can do right now: its defaults, adjusted by the founder's
switches in the Access grid (the level_permissions collection)."""
from __future__ import annotations

from . import catalog, levels


def effective(conn, level: str) -> set[str]:
    if level == "founder":
        return set(catalog.KEYS) | catalog.FOUNDER_ONLY
    perms = set(catalog.DEFAULTS.get(level, set()))
    for r in conn["level_permissions"].find({"level": level}):
        if r["perm"] in catalog.KEYS:
            (perms.add if r["allowed"] else perms.discard)(r["perm"])
    return perms


def over(actor_level: str, actor_perms: set[str], perm: str, target_level: str) -> bool:
    """A people power over someone: the permission AND a higher level. Never the founder."""
    return target_level != "founder" and perm in actor_perms and levels.outranks(actor_level, target_level)


def holders(conn, perm: str, above: str) -> list[int]:
    """Active people (not demo) who hold `perm` and outrank `above`: who can act on that level."""
    out = []
    cache: dict[str, set[str]] = {}
    for r in conn["staff"].find({"status": "active", "is_demo": False}, {"id": 1, "level": 1}):
        lv = r["level"]
        if lv not in cache:
            cache[lv] = effective(conn, lv)
        if perm in cache[lv] and levels.outranks(lv, above):
            out.append(r["id"])
    return out
