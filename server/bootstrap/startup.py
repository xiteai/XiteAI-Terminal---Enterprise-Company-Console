"""What happens once, when the server starts."""
from __future__ import annotations

from ..core import config, db, schema, settings
from ..features.checkin import batcher as checkin_batcher
from ..features.code import service as code
from ..features.demo import seed as demo
from ..features.products import service as products
from ..security import sessions
from . import env_accounts, freshness


def run() -> None:
    freshness.build()              # pin this server's build before it answers anyone
    db.wait_until_ready()          # a network blip at start is a wait, not a crash
    schema.init()
    with db.connect() as conn:
        env_accounts.sync(conn)
        products.ensure_defaults(conn)
        sessions.purge_expired(conn)
        # Demo data comes back unless someone deliberately removed it; hiding it is the switch.
        if config.DEMO_DATA and not demo.present(conn) and settings.get(conn, "demo_deleted") != "1":
            demo.load(conn)
    code.resume_stuck_clones()
    code.start_sync_loop()
    checkin_batcher.start()
