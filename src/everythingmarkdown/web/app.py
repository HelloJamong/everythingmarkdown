"""App factory. Run: uvicorn --factory everythingmarkdown.web.app:create_app --proxy-headers"""

import logging
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from . import auth
from .config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings(os.environ)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limiter = auth.LoginLimiter()
    # ponytail: auth events go to stderr (docker logs); /logs JSON Lines files arrive in web P3.
    if not auth.audit.handlers:
        auth.audit.addHandler(logging.StreamHandler())
        auth.audit.setLevel(logging.INFO)
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
    app.include_router(auth.router)

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
