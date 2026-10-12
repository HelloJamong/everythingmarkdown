"""JSON Lines audit/access logs under LOG_DIR.

Never log passwords, cookies, bodies, document text, or original file names; jobs are tracked by ID.
"""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import Request, Response

audit_log = logging.getLogger("everythingmarkdown.audit")
access_log = logging.getLogger("everythingmarkdown.access")


def setup(log_dir: Path, max_bytes: int, backup_count: int) -> None:
    """Point both loggers at rotating files. Raises OSError if LOG_DIR is unwritable (refuse start).

    ponytail: size rotation only; date rotation and the 30-day cap on rotated files are not done.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    for logger, name in ((audit_log, "audit.log"), (access_log, "access.log")):
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        handler = RotatingFileHandler(
            log_dir / name, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


def _line(event: str, fields: dict[str, Any]) -> str:
    record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "event": event, **fields}
    return json.dumps(record, ensure_ascii=False)  # json escapes newlines, so no log forging


def audit(event: str, **fields: Any) -> None:
    audit_log.info(_line(event, fields))


def client_ip(request: Request) -> str:
    # uvicorn --proxy-headers rewrites client from trusted X-Forwarded-For.
    return request.client.host if request.client else "unknown"


async def access_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request.state.request_id = uuid.uuid4().hex
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        access_log.info(_line("http_request", {
            "request_id": request.state.request_id,
            "ip": client_ip(request),
            "method": request.method,
            # Route template only; raw paths and queries may carry arbitrary strings.
            "path": getattr(route, "path", "unmatched"),
            "status": status,
            "ms": round((time.monotonic() - started) * 1000),
        }))
