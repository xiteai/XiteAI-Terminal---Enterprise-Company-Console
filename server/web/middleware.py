"""Headers every response carries, and the cross-site request guard.

The guard: every state-changing call to the console API must carry `X-TC: 1`.
A browser won't let another site add a custom header without a CORS
preflight this server never grants, so a forged form post from elsewhere is
refused even though the session cookie would ride along (it's SameSite=Strict
too; this is the second lock)."""
from __future__ import annotations

import mimetypes

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
_WRITE = {"POST", "PUT", "PATCH", "DELETE"}
_OPEN_API = ("/api/public/", "/api/v1/")    # callable by installs and plain forms
# Code changes carry at most one file of text; anything bigger is refused
# before it's read (JSON escaping can double text, hence the margin).
_CODE_BODY_MAX = 2 * 1024 * 1024 + 64 * 1024


def fix_mimetypes() -> None:
    """Windows' registry can map .js to text/plain, which browsers refuse to run as a module."""
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and request.method in _WRITE and not path.startswith(_OPEN_API):
            if request.headers.get("X-TC") != "1":
                return JSONResponse({"detail": "This request is missing its console header."}, status_code=403)
            if path.startswith("/api/code/"):
                size = request.headers.get("content-length")
                if size is None and request.headers.get("transfer-encoding"):
                    return JSONResponse({"detail": "Send the size of what you're uploading."}, status_code=411)
                if size is not None and (not size.isdigit() or int(size) > _CODE_BODY_MAX):
                    return JSONResponse({"detail": "That's too big. The codebase takes code and text only, "
                                                   "up to 1 MB per file."}, status_code=413)
        response = await call_next(request)
        h = response.headers
        h["Content-Security-Policy"] = CSP
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        if path.startswith("/api/"):
            h["Cache-Control"] = "no-store"
        return response
