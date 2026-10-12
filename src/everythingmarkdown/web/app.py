"""App factory. Run: uvicorn --factory everythingmarkdown.web.app:create_app --proxy-headers"""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from . import auth, logs, routes
from .config import Settings, load_settings
from .jobs import Jobs


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

    @app.get("/")
    def index(request: Request) -> Response:
        state = auth.session_state(request)
        if state != "ok":
            return RedirectResponse("/login?expired" if state == "expired" else "/login", status_code=303)
        # ponytail: placeholder until the web P4 upload screen replaces it.
        return auth.templates.TemplateResponse(request, "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
