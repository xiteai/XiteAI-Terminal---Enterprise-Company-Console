"""The pages. The UI is one React app (dashboard/, built into dashboard/dist);
every page path serves its index.html and React picks the screen. The server
still decides the redirects, so a signed-out visitor never sees console chrome."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from ..core import config, db
from ..security import sessions
from .deps import COOKIE

router = APIRouter()
_INDEX = config.DASHBOARD_DIR / "dist" / "index.html"
_NOT_BUILT = ("<!doctype html><meta charset=utf-8><title>XiteAI Terminal</title>"
              "<body style='font-family:system-ui;padding:48px;background:#fff;color:#111113'>"
              "<h2>The dashboard UI isn't built yet</h2><p>Run <code>npm install</code> and "
              "<code>npm run build</code> inside <code>dashboard/</code>, then reload.</p>")


def _signed_in(request: Request) -> bool:
    with db.connect() as conn:
        return sessions.lookup(conn, request.cookies.get(COOKIE)) is not None


def _app():
    if not _INDEX.exists():
        return HTMLResponse(_NOT_BUILT, status_code=503)
    return FileResponse(_INDEX, headers={"Cache-Control": "no-cache"})


@router.get("/favicon.png", include_in_schema=False)
@router.get("/apple-touch-icon.png", include_in_schema=False)
def icon(request: Request):
    path = config.DASHBOARD_DIR / "dist" / request.url.path.lstrip("/")
    return FileResponse(path) if path.exists() else HTMLResponse("", status_code=404)


@router.get("/", include_in_schema=False)
def customer_panel():
    return _app()


@router.get("/login", include_in_schema=False)
@router.get("/join", include_in_schema=False)
def team_entry(request: Request):
    return RedirectResponse("/console", 303) if _signed_in(request) else _app()


@router.get("/console", include_in_schema=False)
@router.get("/console/{rest:path}", include_in_schema=False)
def console(request: Request, rest: str = ""):
    return _app() if _signed_in(request) else RedirectResponse("/login", 303)
