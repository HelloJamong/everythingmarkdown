"""App factory. Run: uvicorn --factory everythingmarkdown.web.app:create_app --proxy-headers"""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ..markitdown_adapter import SUPPORTED_EXTENSIONS
from . import auth, logs, routes
from .config import Settings, load_settings
from .jobs import Jobs

REPO_URL = "https://github.com/HelloJamong/everythingmarkdown"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings(os.environ)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Unwritable LOG_DIR/DATA_DIR raises here, so the server refuses to start.
        logs.setup(settings.log_dir, settings.log_max_bytes, settings.log_backup_count)
        app.state.jobs = Jobs(settings)
        app.state.jobs.start()
        yield
        app.state.jobs.stop()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.limiter = auth.LoginLimiter()
    # Fresh key per start: a restart or APP_PASSWORD change logs every session out.
    app.add_middleware(
        SessionMiddleware,
        secret_key=secrets.token_urlsafe(32),
        session_cookie="emd_session",
        max_age=auth.SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.cookie_secure,
    )
    app.middleware("http")(auth.check_origin)
    app.middleware("http")(logs.access_middleware)  # outermost: also logs 403s from check_origin
    app.include_router(auth.router)
    app.include_router(routes.router)
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    @app.get("/")
    def index(request: Request) -> Response:
        state = auth.session_state(request)
        if state != "ok":
            return RedirectResponse("/login?expired" if state == "expired" else "/login", status_code=303)
        return auth.templates.TemplateResponse(request, "index.html", _screen(settings))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _days(seconds: int) -> str:
    return f"{seconds // 86400}일 보관"


def _screen(settings: Settings) -> dict[str, Any]:
    """Limits and retention shown next to the upload box."""
    temp_minutes = settings.temp_result_ttl // 60
    return {
        "version": version("everythingmarkdown"),
        "repo_url": REPO_URL,
        "accept": ",".join(SUPPORTED_EXTENSIONS),
        "formats": ", ".join(ext[1:].upper() for ext in SUPPORTED_EXTENSIONS),
        "max_bytes": settings.max_file_bytes,
        "max_mib": settings.max_file_bytes // (1024 * 1024),
        "temp_minutes": temp_minutes,
        "upload_policy": "변환 후 바로 삭제" if settings.upload_ttl is None else _days(settings.upload_ttl),
        "markdown_policy": (f"다운로드 후 삭제 (받지 않으면 {temp_minutes}분 뒤)"
                            if settings.markdown_ttl is None else _days(settings.markdown_ttl)),
    }
