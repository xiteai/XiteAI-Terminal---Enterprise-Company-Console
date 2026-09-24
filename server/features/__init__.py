"""One folder per feature. Each has routes.py (the HTTP surface) and, where
there's real logic, service.py; the registry below is the only place that
knows the full list."""
from __future__ import annotations

from importlib import import_module

FEATURES = ["auth", "join", "people", "requests", "access_grid", "notifications", "products", "settings", "overview", "installs",
            "releases", "support", "audit_log", "account", "demo", "public", "checkin", "ai_keys", "code"]


def routers() -> list:
    return [import_module(f"{__name__}.{name}.routes").router for name in FEATURES]
