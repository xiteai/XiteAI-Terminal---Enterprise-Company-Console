from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from ...core import db
from ...web.deps import require
from ..installs import store as installs_store
from ..products import service as products
from . import loader

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.get("")
def releases(product: str = products.DEFAULT, a: dict = Depends(require("releases"))):
    since = db.iso(datetime.now(timezone.utc) - timedelta(days=30))
    with db.connect() as conn:
        prod = products.get(conn, product)
        act = installs_store.rows(
            "SELECT app_version, update_state FROM installs WHERE product_id = ? AND last_seen >= ?"
            + installs_store.demo_sql(conn), (prod["id"], since))
    counts = Counter(r["app_version"] for r in act)
    failed = Counter(r["app_version"] for r in act if r["update_state"] == "failed")
    # Only XOS1 has a notes folder today; any other product lists the versions its installs report.
    rels = loader.load() if prod["slug"] == products.DEFAULT else []
    known = {r["version"] for r in rels}
    rels += [loader.blank(v) for v in counts if v and v not in known]
    rels.sort(key=lambda r: loader.version_key(r["version"]), reverse=True)
    for r in rels:
        r["installs"] = counts.get(r["version"], 0)
        r["share"] = round(counts.get(r["version"], 0) / len(act), 4) if act else None
        r["update_failed"] = failed.get(r["version"], 0)
        r["is_latest"] = r["version"] == prod["latest_version"]
    return {"active_installs": len(act), "latest_version": prod["latest_version"], "releases": rels}
