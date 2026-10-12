"""Job API: upload, status, preview, download, delete. Every route requires login (when enabled)
and only ever reaches the caller's own jobs: another owner's job is indistinguishable from a missing one."""

import re
import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.background import BackgroundTask
from starlette.datastructures import UploadFile

from ..markitdown_adapter import SUPPORTED_EXTENSIONS
from ..models import ConversionError, ErrorCode
from . import logs
from .auth import current_owner, require_login
from .jobs import INTERRUPTED_ERROR, TIMEOUT_ERROR, Jobs

PREVIEW_BYTES = 64 * 1024
CHUNK = 1024 * 1024
_JOB_ID = re.compile(r"[0-9a-f]{32}")
_MESSAGES = {
    TIMEOUT_ERROR: "변환 시간이 초과되었습니다.",
    INTERRUPTED_ERROR: "서버 재시작으로 변환이 중단되었습니다. 다시 업로드해 주세요.",
}

router = APIRouter(prefix="/api/jobs", dependencies=[Depends(require_login)])


def _jobs(request: Request) -> Jobs:
    jobs: Jobs = request.app.state.jobs
    return jobs


def _message(error: str | None) -> str | None:
    if error is None:
        return None
    if error in _MESSAGES:
        return _MESSAGES[error]
    return str(ConversionError(ErrorCode(error)))


def _result_available(job: dict[str, Any]) -> bool:
    return (job["state"] == "succeeded" and not job["markdown_gone"]
            and time.time() < job["markdown_expires_at"])


def _view(job: dict[str, Any]) -> dict[str, Any]:
    if job["state"] != "succeeded":
        result = "none"
    else:
        result = "available" if _result_available(job) else "expired"
    return {
        "id": job["id"], "name": job["name"], "size": job["size"], "state": job["state"],
        "error": job["error"], "message": _message(job["error"]),
        "result": result, "result_expires_at": job["markdown_expires_at"],
        "delete_after_download": not job["markdown_keep"],
        "upload_kept": not job["upload_gone"],
        "created_at": job["created_at"], "finished_at": job["finished_at"],
    }


def _get(request: Request, job_id: str) -> dict[str, Any]:
    job = _jobs(request).get(job_id) if _JOB_ID.fullmatch(job_id) else None
    if job is None or job["owner"] != current_owner(request):
        raise HTTPException(status_code=404)
    return job


def _display_name(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[-120:] or "document"


def _reject(request: Request, status: int, reason: str) -> JSONResponse:
    logs.audit("upload_rejected", request_id=request.state.request_id, reason=reason)
    return JSONResponse({"error": reason}, status_code=status)


@router.post("", status_code=202)
async def upload(request: Request) -> Response:
    settings = request.app.state.settings
    # uvicorn never delivers more body than Content-Length, so checking it bounds parsing.
    length = request.headers.get("content-length")
    if length is None or not length.isdigit():
        return _reject(request, 411, "LENGTH_REQUIRED")
    if int(length) > settings.max_request_bytes:
        return _reject(request, 413, "TOO_LARGE")
    form = await request.form(max_files=1, max_fields=1)
    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            return _reject(request, 400, "NO_FILE")
        name = _display_name(upload.filename)
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in SUPPORTED_EXTENSIONS:
            return _reject(request, 415, "UNSUPPORTED_FORMAT")
        jobs = _jobs(request)
        job_id = secrets.token_hex(16)
        directory = jobs.upload_dir(job_id)
        directory.mkdir()
        size = 0
        with (directory / f"input{ext}").open("xb") as target:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > settings.max_file_bytes:
                    break
                target.write(chunk)
        if size > settings.max_file_bytes:
            jobs.remove_upload(job_id)
            return _reject(request, 413, "TOO_LARGE")
        if not jobs.reserve(job_id, name, ext, size, owner=current_owner(request)):
            jobs.remove_upload(job_id)
            return _reject(request, 429, "QUEUE_FULL")
    finally:
        await form.close()
    logs.audit("upload_accepted", request_id=request.state.request_id, job_id=job_id, ext=ext, size=size)
    jobs.enqueue(job_id)
    return JSONResponse(_view(jobs.get(job_id) or {}), status_code=202)


@router.get("")
def list_jobs(request: Request) -> list[dict[str, Any]]:
    return [_view(job) for job in _jobs(request).recent(current_owner(request))]


@router.get("/{job_id}")
def status(request: Request, job_id: str) -> dict[str, Any]:
    return _view(_get(request, job_id))


def _available(request: Request, job_id: str) -> dict[str, Any]:
    job = _get(request, job_id)
    if job["state"] != "succeeded":
        raise HTTPException(status_code=409)
    if not _result_available(job):
        raise HTTPException(status_code=410)
    return job


@router.get("/{job_id}/preview")
def preview(request: Request, job_id: str) -> Response:
    _available(request, job_id)
    path = _jobs(request).markdown_path(job_id)
    with path.open("rb") as source:
        data = source.read(PREVIEW_BYTES + 1)
    truncated = len(data) > PREVIEW_BYTES
    text = data[:PREVIEW_BYTES].decode("utf-8", errors="ignore")
    return PlainTextResponse(text, headers={"X-Truncated": "1" if truncated else "0"})


@router.get("/{job_id}/download")
def download(request: Request, job_id: str) -> Response:
    job = _available(request, job_id)
    jobs = _jobs(request)
    logs.audit("download_started", request_id=request.state.request_id, job_id=job_id)

    def sent() -> None:
        # Runs only after the body was fully sent; an aborted transfer keeps the file until its TTL.
        logs.audit("download_sent", job_id=job_id)
        if not job["markdown_keep"]:
            jobs.remove_markdown(job_id)

    # ponytail: a second concurrent download of a keep-N result may race the delete and fail;
    # add per-job transfer refcounts if that ever matters.
    return FileResponse(
        jobs.markdown_path(job_id), media_type="text/markdown; charset=utf-8",
        filename=job["name"].rsplit(".", 1)[0] + ".md", background=BackgroundTask(sent),
    )


@router.delete("/{job_id}", status_code=204)
def delete(request: Request, job_id: str) -> Response:
    job = _get(request, job_id)
    if job["state"] in ("queued", "running"):
        raise HTTPException(status_code=409)
    if not _jobs(request).delete(job_id):
        raise HTTPException(status_code=500)
    logs.audit("job_deleted", request_id=request.state.request_id, job_id=job_id)
    return Response(status_code=204)
