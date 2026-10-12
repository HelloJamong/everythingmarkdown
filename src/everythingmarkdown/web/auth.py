"""Single-password login (.env APP_PASSWORD): signed cookie, Origin check, in-memory rate limit."""

import hmac
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from . import logs

SESSION_MAX_AGE = 8 * 60 * 60
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
router = APIRouter()


def _audit(event: str, request: Request) -> None:
    logs.audit(event, ip=logs.client_ip(request), request_id=getattr(request.state, "request_id", None))


class LoginLimiter:
    """Failed logins per client IP in a sliding window.

    ponytail: per-process dict, fine for one uvicorn worker; entries of IPs that never retry
    stay until restart. Move to SQLite if this ever runs multi-worker.
    """

    def __init__(self, limit: int = 5, window: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self._failures: dict[str, list[float]] = {}

    def blocked(self, ip: str) -> bool:
        cutoff = self.clock() - self.window
        recent = [t for t in self._failures.get(ip, []) if t > cutoff]
        if recent:
            self._failures[ip] = recent
        else:
            self._failures.pop(ip, None)
        return len(recent) >= self.limit

    def fail(self, ip: str) -> None:
        self._failures.setdefault(ip, []).append(self.clock())

    def clear(self, ip: str) -> None:
        self._failures.pop(ip, None)


def session_state(request: Request) -> str:
    """'ok', 'expired', or 'none'. SessionMiddleware re-signs on every response, so the
    absolute 8-hour limit is enforced from the login time stored in the cookie."""
    logged_in_at = request.session.get("at")
    if not isinstance(logged_in_at, int):
        return "none"
    if time.time() - logged_in_at >= SESSION_MAX_AGE:
        request.session.clear()
        return "expired"
    return "ok"


def require_login(request: Request) -> None:
    if session_state(request) != "ok":
        raise HTTPException(status_code=401)


async def check_origin(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Reject state-changing requests whose Origin (or Referer) host differs from Host."""
    if request.method in UNSAFE_METHODS:
        source = request.headers.get("origin") or request.headers.get("referer") or ""
        host = request.headers.get("host", "")
        if not host or urlsplit(source).netloc != host:
            _audit("origin_rejected", request)
            return Response(status_code=403)
    return await call_next(request)


@router.get("/login")
def login_page(request: Request, expired: str | None = None) -> Response:
    if session_state(request) == "ok":
        return RedirectResponse("/", status_code=303)
    notice = "로그인이 만료되었습니다. 다시 로그인하세요." if expired is not None else None
    return templates.TemplateResponse(request, "login.html", {"notice": notice})


@router.post("/login")
def login(request: Request, password: str = Form("")) -> Response:
    ip = logs.client_ip(request)
    limiter: LoginLimiter = request.app.state.limiter
    if limiter.blocked(ip):
        _audit("login_rate_limited", request)
        return templates.TemplateResponse(
            request, "login.html", {"error": "시도가 너무 많습니다. 1분 뒤 다시 시도하세요."}, status_code=429
        )
    expected: str = request.app.state.settings.password
    if not hmac.compare_digest(password.encode(), expected.encode()):
        limiter.fail(ip)
        _audit("login_failed", request)
        return templates.TemplateResponse(
            request, "login.html", {"error": "비밀번호가 맞지 않습니다."}, status_code=401
        )
    limiter.clear(ip)
    request.session.clear()
    request.session["at"] = int(time.time())
    _audit("login_succeeded", request)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request) -> Response:
    request.session.clear()
    _audit("logout", request)
    return RedirectResponse("/login", status_code=303)
