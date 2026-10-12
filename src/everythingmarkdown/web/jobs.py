"""Job store (SQLite), single conversion runner (child process), and retention cleanup.

Layout under DATA_DIR: uploads/<id>/input<ext>, markdown/<id>/input.md, .work/<id>/, app.db.
"""

import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from ..models import ErrorCode
from . import logs
from .config import Settings

ACTIVE_STATES = ("queued", "running")
TIMEOUT_ERROR = "TIMEOUT"
INTERRUPTED_ERROR = "INTERRUPTED"
SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,              -- normalized display name, never logged
    ext TEXT NOT NULL,
    size INTEGER NOT NULL,
    state TEXT NOT NULL,
    error TEXT,
    created_at REAL NOT NULL,
    finished_at REAL,
    upload_expires_at REAL,          -- NULL: keep N, removed once the child exits
    upload_gone INTEGER NOT NULL DEFAULT 0,
    markdown_keep INTEGER NOT NULL,  -- snapshot of MARKDOWN_KEEP; N also deletes after first download
    markdown_ttl INTEGER NOT NULL,   -- retention or temp TTL, counted from success
    markdown_expires_at REAL,
    markdown_gone INTEGER NOT NULL DEFAULT 0
)
"""


class Jobs:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.data_dir
        for name in ("uploads", "markdown", ".work"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        # ponytail: one connection behind one lock; plenty for a single-user service.
        self._db = sqlite3.connect(self.root / "app.db", check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise RuntimeError(f"unsupported app.db schema version {version}")
        self._db.execute(SCHEMA)
        self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # Paths ---------------------------------------------------------------
    def upload_dir(self, job_id: str) -> Path:
        return self.root / "uploads" / job_id

    def markdown_path(self, job_id: str) -> Path:
        return self.root / "markdown" / job_id / "input.md"

    def work_dir(self, job_id: str) -> Path:
        return self.root / ".work" / job_id

    # Store ---------------------------------------------------------------
    def _exec(self, sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._db.execute(sql, args).fetchall()]

    def get(self, job_id: str) -> dict[str, Any] | None:
        rows = self._exec("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return rows[0] if rows else None

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._exec("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))

    def reserve(self, job_id: str, name: str, ext: str, size: int) -> bool:
        """Insert a queued job unless running+queued already hit the limit."""
        now = time.time()
        s = self.settings
        with self._lock:
            placeholders = ",".join("?" * len(ACTIVE_STATES))
            active = self._db.execute(
                f"SELECT COUNT(*) FROM jobs WHERE state IN ({placeholders})", ACTIVE_STATES
            ).fetchone()[0]
            if active >= s.max_active_jobs:
                return False
            self._db.execute(
                "INSERT INTO jobs (id, name, ext, size, state, created_at, upload_expires_at,"
                " markdown_keep, markdown_ttl) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?)",
                (job_id, name, ext, size, now,
                 None if s.upload_ttl is None else now + s.upload_ttl,
                 int(s.markdown_ttl is not None),
                 s.temp_result_ttl if s.markdown_ttl is None else s.markdown_ttl),
            )
        return True

    def _finish(self, job_id: str, state: str, error: str | None) -> None:
        now = time.time()
        if state == "succeeded":
            self._exec(
                "UPDATE jobs SET state = ?, finished_at = ?, markdown_expires_at = ? + markdown_ttl"
                " WHERE id = ?", (state, now, now, job_id))
        else:
            self._exec("UPDATE jobs SET state = ?, error = ?, finished_at = ?, markdown_gone = 1"
                       " WHERE id = ?", (state, error, now, job_id))

    # Files ---------------------------------------------------------------
    def remove_upload(self, job_id: str) -> bool:
        return self._remove(self.upload_dir(job_id), job_id, "upload")

    def remove_markdown(self, job_id: str) -> bool:
        return self._remove(self.markdown_path(job_id).parent, job_id, "markdown")

    def _remove(self, directory: Path, job_id: str, kind: str) -> bool:
        try:
            shutil.rmtree(directory)
        except FileNotFoundError:
            pass
        except OSError:
            logs.audit("file_delete_failed", job_id=job_id, kind=kind)
            return False  # stays not-gone, so the next cleanup retries
        self._exec(f"UPDATE jobs SET {kind}_gone = 1 WHERE id = ?", (job_id,))
        return True

    def delete(self, job_id: str) -> bool:
        if not (self.remove_upload(job_id) and self.remove_markdown(job_id)):
            return False
        self._exec("DELETE FROM jobs WHERE id = ?", (job_id,))
        return True

    # Runner --------------------------------------------------------------
    def start(self) -> None:
        self.recover()
        self.cleanup()
        for target in (self._run_loop, self._cleanup_loop):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)
        logs.audit("server_started")

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(None)
        for thread in self._threads:
            thread.join(timeout=self.settings.conversion_timeout + 5)
        logs.audit("server_stopped")

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def recover(self) -> None:
        """Jobs cut off by a restart become interrupted; their partial work is discarded."""
        stale = self._exec("SELECT id FROM jobs WHERE state IN ('queued', 'running')")
        for row in stale:
            self._finish(row["id"], "interrupted", INTERRUPTED_ERROR)
            logs.audit("job_interrupted", job_id=row["id"])
        shutil.rmtree(self.root / ".work", ignore_errors=True)
        (self.root / ".work").mkdir(exist_ok=True)
        for row in self._exec("SELECT id FROM jobs WHERE upload_expires_at IS NULL AND upload_gone = 0"
                              " AND state NOT IN ('queued', 'running')"):
            self.remove_upload(row["id"])

    def _run_loop(self) -> None:
        while (job_id := self._queue.get()) is not None:
            self._convert(job_id)

    def _convert(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None or job["state"] != "queued":
            return
        self._exec("UPDATE jobs SET state = 'running' WHERE id = ?", (job_id,))
        logs.audit("conversion_started", job_id=job_id)
        work = self.work_dir(job_id)
        work.mkdir()
        source = self.upload_dir(job_id) / f"input{job['ext']}"
        # Secrets stay out of the child; it only needs to import and convert.
        env = {k: v for k, v in os.environ.items() if k != "APP_PASSWORD"}
        error: str | None
        try:
            done = subprocess.run(
                [sys.executable, "-m", "everythingmarkdown.web.worker", str(source), str(work)],
                capture_output=True, text=True, timeout=self.settings.conversion_timeout, env=env,
            )
        except subprocess.TimeoutExpired:  # run() has already killed and reaped the child
            state, error = "timed_out", TIMEOUT_ERROR
        else:
            state, error = self._publish(job_id, work, done)
        shutil.rmtree(work, ignore_errors=True)
        self._finish(job_id, state, error)
        logs.audit(f"conversion_{state}", job_id=job_id, error=error)
        if job["upload_expires_at"] is None:
            self.remove_upload(job_id)

    def _publish(
        self, job_id: str, work: Path, done: subprocess.CompletedProcess[str]
    ) -> tuple[str, str | None]:
        if done.returncode != 0:
            code = done.stdout.strip()
            return "failed", code if code in ErrorCode.__members__ else ErrorCode.CONVERSION_FAILED.value
        target = self.markdown_path(job_id)
        try:
            target.parent.mkdir(parents=True)  # fresh job dir, so nothing is ever overwritten
            os.rename(work / "convert_result" / "input.md", target)
        except OSError:
            return "failed", ErrorCode.WRITE_FAILED.value
        return "succeeded", None

    # Cleanup -------------------------------------------------------------
    def cleanup(self) -> None:
        now = time.time()
        for row in self._exec("SELECT id FROM jobs WHERE upload_gone = 0 AND upload_expires_at <= ?", (now,)):
            if self.remove_upload(row["id"]):
                logs.audit("upload_expired", job_id=row["id"])
        expired = "SELECT id FROM jobs WHERE markdown_gone = 0 AND markdown_expires_at <= ?"
        for row in self._exec(expired, (now,)):
            if self.remove_markdown(row["id"]):
                logs.audit("markdown_expired", job_id=row["id"])
        self._exec("DELETE FROM jobs WHERE upload_gone = 1 AND markdown_gone = 1"
                   " AND state NOT IN ('queued', 'running')")

    def _cleanup_loop(self) -> None:
        while not self._stop.wait(self.settings.cleanup_interval):
            self.cleanup()
