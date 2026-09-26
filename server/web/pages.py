"""The pages. The UI is one React app (dashboard/, built into dashboard/dist);
every page path serves its index.html and React picks the screen. The server
still decides the redirects, so a signed-out visitor never sees console chrome."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import (FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse,
                               Response)

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


@router.get("/careers", include_in_schema=False)
@router.get("/careers/{rest:path}", include_in_schema=False)
def careers():
    return _app()


@router.get("/robots.txt", include_in_schema=False)
def robots():
    """Crawlers get the public side and nothing else. The console is behind a
    sign-in anyway — this just stops them wasting their time and ours."""
    base = config.PUBLIC_BASE_URL.rstrip("/")
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /$\n"
        "Allow: /careers\n"
        "Disallow: /console\n"
        "Disallow: /login\n"
        "Disallow: /join\n"
        "Disallow: /api/\n"
        f"\nSitemap: {base}/sitemap.xml\n")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    """The public pages, plus every role that's actually open right now — so a
    new posting can be found the day it goes up rather than whenever someone
    remembers to update a static file."""
    base = config.PUBLIC_BASE_URL.rstrip("/")
    urls = [(f"{base}/", "weekly", "1.0"), (f"{base}/careers", "daily", "0.8")]
    try:
        with db.connect() as conn:
            for row in conn["job_roles"].find({"status": "open"}, {"id": 1}):
                urls.append((f"{base}/careers/{row['id']}", "weekly", "0.6"))
    except Exception:                    # noqa: BLE001 — a sitemap must not 500 the site
        pass
    body = "".join(
        f"<url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for loc, freq, pri in urls)
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
        media_type="application/xml")


@router.get("/download", include_in_schema=False)
def download(request: Request):
    """Count the click, then send them on to the file.

    The download link used to point straight at GitHub, so nothing here ever
    knew a download happened — the Overview could show installs but never how
    many people tried. This records one row and redirects; the visitor sees a
    redirect they'd never notice.

    The address is hashed with the server's own secret before it's stored, so
    repeat downloads from one person can be told apart from a hundred people
    without ever keeping anybody's address."""
    import hashlib

    from ..features.installs import store as installs_store
    from ..features.products import service as products
    from ..security import vault as secret_vault

    try:
        ip = request.client.host if request.client else ""
        salted = hashlib.sha256(ip.encode() + secret_vault._key()).hexdigest()[:32] if ip else ""
        with db.connect() as conn:
            pid = products.get_id(conn, products.DEFAULT) or 0
        installs_store.run(
            "INSERT INTO downloads (product_id, at, ip_hash, country, referer) VALUES (?,?,?,?,?)",
            (pid, db.now_iso(), salted, request.headers.get("CF-IPCountry", "")[:8],
             (request.headers.get("referer") or "")[:200]))
    except Exception:                    # noqa: BLE001 — a counter must never block a download
        pass
    return RedirectResponse(config.DOWNLOAD_URL, 302)


@router.get("/login", include_in_schema=False)
@router.get("/join", include_in_schema=False)
def team_entry(request: Request):
    return RedirectResponse("/console", 303) if _signed_in(request) else _app()


@router.get("/console", include_in_schema=False)
@router.get("/console/{rest:path}", include_in_schema=False)
def console(request: Request, rest: str = ""):
    return _app() if _signed_in(request) else RedirectResponse("/login", 303)
