"""Web P6 gap tests for acceptance criteria not already covered (IDs A01~A25 of the web acceptance criteria)."""

import hashlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from everythingmarkdown.web import logs
from everythingmarkdown.web.app import create_app
from everythingmarkdown.web.config import Settings
from everythingmarkdown.web.jobs import Jobs

from .test_jobs import BASE, PASSWORD, Service, fixture

JOB = "a" * 32


def bare_jobs(root: Path, **overrides) -> Jobs:
    return Jobs(Settings(password=PASSWORD, data_dir=root, log_dir=root / "logs", **overrides))


class AcceptanceTests(unittest.TestCase):
    def test_a05_kept_original_is_byte_identical(self):
        with Service(upload_ttl=86400) as service:
            for ext in (".pdf", ".docx", ".xlsx"):
                job = service.convert(f"x{ext}", fixture(ext))
                stored = service.jobs.upload_dir(job["id"]) / f"input{ext}"
                self.assertEqual(hashlib.sha256(fixture(ext)).digest(), hashlib.sha256(stored.read_bytes()).digest())

    def test_a07_size_boundary_and_missing_length(self):
        with Service(max_file_bytes=100) as service:
            self.assertEqual(202, service.upload("edge.txt", b"x" * 100).status_code)
            self.assertEqual(413, service.upload("over.txt", b"x" * 101).status_code)
            chunked = service.client.post(
                "/api/jobs", content=iter([b"--b\r\n"]),
                headers={"content-type": "multipart/form-data; boundary=b"},
            )
            self.assertEqual(411, chunked.status_code)

    def test_a17_password_change_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = {"data_dir": Path(tmp) / "data", "log_dir": Path(tmp) / "logs"}
            new_password = "a brand new password"

            def client(password):
                c = TestClient(create_app(Settings(password=password, **dirs)), base_url=BASE, follow_redirects=False)
                c.headers["origin"] = BASE
                return c

            with client(PASSWORD) as old:
                self.assertEqual(303, old.post("/login", data={"password": PASSWORD}).status_code)
                with client(new_password) as new:
                    new.cookies = old.cookies
                    self.assertEqual(401, new.get("/api/jobs").status_code)
                    self.assertEqual(401, new.post("/login", data={"password": PASSWORD}).status_code)
                    self.assertEqual(303, new.post("/login", data={"password": new_password}).status_code)
            stored = b"".join(p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file())
            for secret in (PASSWORD, new_password):
                self.assertNotIn(secret.encode(), stored)

    def test_a19_expiry_boundary_and_idempotent_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = bare_jobs(Path(tmp), markdown_ttl=86400)
            jobs.reserve(JOB, "a.txt", ".txt", 1)
            jobs._finish(JOB, "succeeded", None)
            jobs.markdown_path(JOB).parent.mkdir(parents=True)
            jobs.markdown_path(JOB).write_text("x")
            jobs._exec("UPDATE jobs SET markdown_expires_at = ? WHERE id = ?", (time.time() + 60, JOB))
            jobs.cleanup()
            self.assertTrue(jobs.markdown_path(JOB).exists())
            jobs._exec("UPDATE jobs SET markdown_expires_at = ? WHERE id = ?", (time.time(), JOB))
            jobs.cleanup()
            jobs.cleanup()  # a second pass over the same state is harmless
            self.assertFalse(jobs.markdown_path(JOB).exists())

    def test_a19_startup_runs_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = bare_jobs(Path(tmp), upload_ttl=86400)
            jobs.reserve(JOB, "a.txt", ".txt", 1)
            jobs._finish(JOB, "failed", "CONVERSION_FAILED")
            jobs.upload_dir(JOB).mkdir()
            jobs._exec("UPDATE jobs SET upload_expires_at = 0 WHERE id = ?", (JOB,))
            restarted = bare_jobs(Path(tmp), upload_ttl=86400)
            restarted.start()
            restarted.stop()
            self.assertFalse(restarted.upload_dir(JOB).exists())
            self.assertIsNone(restarted.get(JOB))  # both files gone and finished: row pruned

    def test_a21_policy_is_snapshotted_per_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare_jobs(Path(tmp), markdown_ttl=86400).reserve(JOB, "a.txt", ".txt", 1)
            changed = bare_jobs(Path(tmp), markdown_ttl=7 * 86400, upload_ttl=86400)
            job = changed.get(JOB)
            self.assertEqual((86400, None), (job["markdown_ttl"], job["upload_expires_at"]))

    def test_a23_logs_rotate_by_size_and_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs.setup(Path(tmp), max_bytes=300, backup_count=2)
            for i in range(50):
                logs.audit("rotation_probe", n=i)
            names = sorted(p.name for p in Path(tmp).iterdir() if p.name.startswith("audit"))
            self.assertEqual(["audit.log", "audit.log.1", "audit.log.2"], names)
            for line in (Path(tmp) / "audit.log").read_text().splitlines():
                json.loads(line)

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_a24_delete_failure_is_logged_and_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs.setup(Path(tmp) / "logs", 1 << 20, 1)
            jobs = bare_jobs(Path(tmp), upload_ttl=86400)
            jobs.reserve(JOB, "a.txt", ".txt", 1)
            jobs._finish(JOB, "failed", "CONVERSION_FAILED")
            (jobs.upload_dir(JOB) / "nested").mkdir(parents=True)
            (jobs.upload_dir(JOB) / "nested" / "input.txt").write_text("x")
            jobs._exec("UPDATE jobs SET upload_expires_at = 0 WHERE id = ?", (JOB,))
            os.chmod(jobs.upload_dir(JOB) / "nested", 0o500)
            try:
                jobs.cleanup()
                self.assertEqual(0, jobs.get(JOB)["upload_gone"])
                self.assertIn("file_delete_failed", (Path(tmp) / "logs" / "audit.log").read_text())
            finally:
                os.chmod(jobs.upload_dir(JOB) / "nested", 0o700)
            jobs.cleanup()
            self.assertIsNone(jobs.get(JOB))

    def test_a25_restart_removes_unrecorded_results_and_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = bare_jobs(Path(tmp), upload_ttl=86400, markdown_ttl=86400)
            jobs.reserve(JOB, "a.txt", ".txt", 1)
            jobs._exec("UPDATE jobs SET state = 'running' WHERE id = ?", (JOB,))
            jobs.upload_dir(JOB).mkdir()
            jobs.markdown_path(JOB).parent.mkdir(parents=True)
            jobs.markdown_path(JOB).write_text("published, DB not updated")
            for kind in ("uploads", "markdown"):
                (Path(tmp) / kind / ("f" * 32)).mkdir()
            bare_jobs(Path(tmp), upload_ttl=86400).recover()
            self.assertFalse(jobs.markdown_path(JOB).exists())
            self.assertTrue(jobs.upload_dir(JOB).exists())  # kept original follows its own policy
            for kind in ("uploads", "markdown"):
                self.assertFalse((Path(tmp) / kind / ("f" * 32)).exists())
            self.assertEqual("interrupted", jobs.get(JOB)["state"])


if __name__ == "__main__":
    unittest.main()
