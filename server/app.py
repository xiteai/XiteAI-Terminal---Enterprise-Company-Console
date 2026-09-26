"""The application: middleware, every feature's routes, the pages, static files."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import features
from .bootstrap import startup
from .core import config
from .web import middleware, pages


@asynccontextmanager
async def lifespan(_app: FastAPI):
    startup.run()
    yield


def create_app() -> FastAPI:
    middleware.fix_mimetypes()
    app = FastAPI(title=config.APP_NAME, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    middleware.install(app)
    for router in features.routers():
        app.include_router(router)
    app.include_router(pages.router)
    # built JS/CSS, the logos, the site's marks, and the self-hosted faces
    for folder in ("assets", "brand", "logo", "fonts"):
        path = config.DASHBOARD_DIR / "dist" / folder
        path.mkdir(parents=True, exist_ok=True)
        app.mount(f"/{folder}", StaticFiles(directory=path), name=folder)
    return app


app = create_app()
