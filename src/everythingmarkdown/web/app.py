"""App factory. Run: uvicorn --factory everythingmarkdown.web.app:create_app --proxy-headers"""

import logging
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
        if not settings.auth_enabled:
            logs.audit("auth_disabled")
            logging.getLogger("uvicorn.error").warning(
                "AUTH_ENABLED=false: no password; every browser on the network can use this service")
        app.state.jobs = Jobs(settings)
        app.state.jobs.start()
        yield
        app.state.jobs.stop()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.limiter = auth.LoginLimiter()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_key(settings),
        session_cookie="emd_session",
        max_age=auth.SESSION_MAX_AGE if settings.auth_enabled else auth.ANON_SESSION_MAX_AGE,
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
        if settings.auth_enabled:
            state = auth.session_state(request)
            if state != "ok":
                return RedirectResponse("/login?expired" if state == "expired" else "/login", status_code=303)
        else:
            auth.current_owner(request)  # hand out the anonymous browser ID on first visit
        return auth.templates.TemplateResponse(request, "index.html", _screen(settings))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _session_key(settings: Settings) -> str:
    """Password mode: fresh key per start, so a restart or password change logs everyone out.
    No-password mode: a key kept in DATA_DIR, so browsers keep reaching their own jobs after a restart."""
    if settings.auth_enabled:
        return secrets.token_urlsafe(32)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / ".session_key"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="ascii").strip()
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        key = secrets.token_urlsafe(32)
        handle.write(key)
    return key


def _days(seconds: int) -> str:
    return f"{seconds // 86400}일 보관"


def _screen(settings: Settings) -> dict[str, Any]:
    """Limits and retention shown next to the upload box."""
    temp_minutes = settings.temp_result_ttl // 60
    return {
        "auth_enabled": settings.auth_enabled,
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
