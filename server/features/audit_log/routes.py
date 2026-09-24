"""The audit trail. The founder sees all of it; anyone else with audit.view
sees what their own level and the levels below them did."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends

from ...access import levels
from ...core import db
from ...web.deps import require

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def trail(limit: int = 60, before: int | None = None, q: str = "", a: dict = Depends(require("audit.view"))):
    filt: dict = {}
    if "audit.all" not in a["perms"]:
        below = levels.below(a["eff_level"])
        filt["$or"] = [{"actor_level": {"$in": below}}, {"actor_id": a["id"]}]
    if before:
        filt["id"] = {"$lt": before}
    if q.strip():
        like = {"$regex": re.escape(q.strip()[:80]), "$options": "i"}
        filt.setdefault("$and", []).append(
            {"$or": [{"action": like}, {"target": like}, {"actor_name": like}, {"detail": like}]})
    limit = max(10, min(limit, 200))
    with db.connect() as conn:
        rows = [db.strip(r) for r in conn["audit"].find(filt).sort("id", -1).limit(limit + 1)]
    return {"items": rows[:limit], "more": len(rows) > limit}
