import json
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from everythingmarkdown.markitdown_adapter import SUPPORTED_EXTENSIONS
from everythingmarkdown.web.app import create_app
from everythingmarkdown.web.config import ConfigError, Settings, load_settings
from everythingmarkdown.web.jobs import Jobs

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PASSWORD = "correct horse battery"
BASE = "https://testserver"


class Service:
    """A started app on temp data/log dirs, logged in."""

    def __init__(self, **overrides):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.settings = Settings(password=PASSWORD, data_dir=root / "data", log_dir=root / "logs", **overrides)
        self.client = TestClient(create_app(self.settings), base_url=BASE, follow_redirects=False)
        self.client.headers["origin"] = BASE

    def __enter__(self):
        self.client.__enter__()
        assert self.client.post("/login", data={"password": PASSWORD}).status_code == 303
        return self

    def __exit__(self, *exc):
        self.client.__exit__(*exc)
        self._tmp.cleanup()

    @property
    def jobs(self) -> Jobs:
        return self.client.app.state.jobs

    def upload(self, name: str, data: bytes):
        return self.client.post("/api/jobs", files={"file": (name, data)})

    def convert(self, name: str, data: bytes) -> dict:
        response = self.upload(name, data)
        assert response.status_code == 202, (response.status_code, response.text)
        return self.wait(response.json()["id"])

    def wait(self, job_id: str) -> dict:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            job = self.client.get(f"/api/jobs/{job_id}").json()
            if job["state"] not in ("queued", "running"):
                return job
            time.sleep(0.1)
        raise AssertionError("job did not finish")

    def log(self, name: str) -> list[dict]:
        text = (self.settings.log_dir / name).read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines()]


def fixture(ext: str) -> bytes:
    return (FIXTURES / f"sample{ext}").read_bytes()


class RetentionConfigTests(unittest.TestCase):
    def test_keep_flags_and_days(self):
        base = {"APP_PASSWORD": PASSWORD}
        settings = load_settings(base)
        self.assertIsNone(settings.upload_ttl)
        self.assertIsNone(settings.markdown_ttl)
        settings = load_settings({**base, "UPLOAD_KEEP": " y ", "UPLOAD_RETENTION_DAYS": "7"})
        self.assertEqual(7 * 86400, settings.upload_ttl)
        for bad in ({"UPLOAD_KEEP": "yes"}, {"MARKDOWN_KEEP": "Y"},
                    {"MARKDOWN_KEEP": "Y", "MARKDOWN_RETENTION_DAYS": "0"},
                    {"MARKDOWN_KEEP": "Y", "MARKDOWN_RETENTION_DAYS": "1.5"},
                    {"MARKDOWN_KEEP": "Y", "MARKDOWN_RETENTION_DAYS": "-1"},
                    {"CLEANUP_INTERVAL_SECONDS": "0"}):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                load_settings({**base, **bad})


class ConversionFlowTests(unittest.TestCase):
    def test_seven_formats_convert_and_download(self):
        with Service(markdown_ttl=3600) as service:
            for ext in SUPPORTED_EXTENSIONS:
                with self.subTest(ext=ext):
                    job = service.convert(f"회의록{ext}", fixture(ext))
                    self.assertEqual("succeeded", job["state"], job)
                    self.assertEqual("available", job["result"])
                    preview = service.client.get(f"/api/jobs/{job['id']}/preview")
                    self.assertIn("EverythingMarkdown P0 sample", preview.text)
                    self.assertEqual("0", preview.headers["x-truncated"])
                    download = service.client.get(f"/api/jobs/{job['id']}/download")
                    self.assertEqual(200, download.status_code)
                    self.assertIn("attachment", download.headers["content-disposition"])
                    self.assertNotIn(b"\r", download.content)

    def test_same_name_uploads_are_independent_and_names_cannot_escape(self):
        with Service() as service:
            first = service.convert("../../notes.txt", b"first upload")
            second = service.convert("C:\\x\\notes.txt", b"second upload")
            self.assertEqual(["notes.txt", "notes.txt"], [first["name"], second["name"]])
            self.assertNotEqual(first["id"], second["id"])
            for job, text in ((first, "first"), (second, "second")):
                self.assertIn(text, service.client.get(f"/api/jobs/{job['id']}/preview").text)
            root = service.settings.data_dir
            self.assertEqual({"uploads", "markdown", ".work", "app.db"}, {p.name for p in root.iterdir()})

    def test_corrupt_document_fails_safely(self):
        with Service() as service:
            job = service.convert("broken.pdf", b"%PDF-1.4\nsecret words, no structure")
            self.assertEqual(("failed", "CONVERSION_FAILED", "none"), (job["state"], job["error"], job["result"]))
            self.assertNotIn("secret", job["message"])
            self.assertEqual(409, service.client.get(f"/api/jobs/{job['id']}/download").status_code)

    def test_stuck_conversion_times_out_and_the_next_job_still_runs(self):
        with Service(conversion_timeout=0.05) as service:
            job = service.convert("sample.txt", b"hello")
            self.assertEqual(("timed_out", "TIMEOUT"), (job["state"], job["error"]))
            self.assertEqual([], list((service.settings.data_dir / ".work").iterdir()))
        with Service() as service:
            self.assertEqual("succeeded", service.convert("sample.txt", b"hello")["state"])


class UploadLimitTests(unittest.TestCase):
    def test_rejections_leave_no_files(self):
        with Service(max_file_bytes=10, max_request_bytes=2000) as service:
            self.assertEqual(415, service.upload("virus.exe", b"MZ").status_code)
            self.assertEqual(413, service.upload("big.txt", b"x" * 11).status_code)
            self.assertEqual(413, service.upload("huge.txt", b"x" * 3000).status_code)
            self.assertEqual(400, service.client.post("/api/jobs", data={"x": "1"}).status_code)
            self.assertEqual([], list((service.settings.data_dir / "uploads").iterdir()))
            reasons = [e["reason"] for e in service.log("audit.log") if e["event"] == "upload_rejected"]
            self.assertEqual(["UNSUPPORTED_FORMAT", "TOO_LARGE", "TOO_LARGE", "NO_FILE"], reasons)

    def test_api_needs_login_and_same_origin(self):
        with Service() as service:
            self.assertEqual(403, service.client.post(
                "/api/jobs", files={"file": ("a.txt", b"a")}, headers={"origin": "https://evil.example"}
            ).status_code)
            service.client.post("/logout")
            self.assertEqual(401, service.client.get("/api/jobs").status_code)
            self.assertEqual(401, service.upload("a.txt", b"a").status_code)

    def test_queue_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Jobs(Settings(password=PASSWORD, data_dir=Path(tmp), max_active_jobs=2))
            self.assertTrue(jobs.reserve("a" * 32, "a.txt", ".txt", 1))
            self.assertTrue(jobs.reserve("b" * 32, "b.txt", ".txt", 1))
            self.assertFalse(jobs.reserve("c" * 32, "c.txt", ".txt", 1))

    def test_unknown_or_malformed_job_ids_are_404(self):
        with Service() as service:
            for job_id in ("0" * 32, "..%2F..%2Fapp.db", "ABC"):
                self.assertEqual(404, service.client.get(f"/api/jobs/{job_id}").status_code)


class RetentionTests(unittest.TestCase):
    def test_keep_n_deletes_upload_after_conversion_and_markdown_after_download(self):
        with Service() as service:
            job = service.convert("a.txt", b"temporary")
            self.assertFalse(job["upload_kept"])
            self.assertFalse(service.jobs.upload_dir(job["id"]).exists())
            self.assertTrue(job["delete_after_download"])
            self.assertEqual(200, service.client.get(f"/api/jobs/{job['id']}/download").status_code)
            self.assertFalse(service.jobs.markdown_path(job["id"]).exists())
            self.assertEqual(410, service.client.get(f"/api/jobs/{job['id']}/download").status_code)

    def test_keep_y_keeps_both_and_allows_redownload(self):
        with Service(upload_ttl=86400, markdown_ttl=86400) as service:
            job = service.convert("a.txt", b"kept")
            self.assertTrue(service.jobs.upload_dir(job["id"]).exists())
            for _ in range(2):
                self.assertEqual(200, service.client.get(f"/api/jobs/{job['id']}/download").status_code)

    def test_all_four_keep_combinations_apply_independently(self):
        for upload_keep in (True, False):
            for markdown_keep in (True, False):
                with self.subTest(upload=upload_keep, markdown=markdown_keep), Service(
                    upload_ttl=86400 if upload_keep else None, markdown_ttl=86400 if markdown_keep else None
                ) as service:
                    job = service.convert("a.txt", b"combo")
                    self.assertEqual(upload_keep, service.jobs.upload_dir(job["id"]).exists())
                    service.client.get(f"/api/jobs/{job['id']}/download")
                    self.assertEqual(markdown_keep, service.jobs.markdown_path(job["id"]).exists())

    def test_expiry_is_independent_and_cleanup_prunes_finished_rows(self):
        with Service(upload_ttl=86400, markdown_ttl=86400) as service:
            job = service.convert("a.txt", b"expiring")
            jobs = service.jobs
            jobs._exec("UPDATE jobs SET markdown_expires_at = 0 WHERE id = ?", (job["id"],))
            self.assertEqual("expired", service.client.get(f"/api/jobs/{job['id']}").json()["result"])
            self.assertEqual(410, service.client.get(f"/api/jobs/{job['id']}/preview").status_code)
            jobs.cleanup()
            self.assertFalse(jobs.markdown_path(job["id"]).exists())
            self.assertTrue(jobs.upload_dir(job["id"]).exists())  # the other policy is untouched
            jobs._exec("UPDATE jobs SET upload_expires_at = 0 WHERE id = ?", (job["id"],))
            jobs.cleanup()
            self.assertEqual(404, service.client.get(f"/api/jobs/{job['id']}").status_code)

    def test_manual_delete(self):
        with Service(upload_ttl=86400, markdown_ttl=86400) as service:
            job = service.convert("a.txt", b"delete me")
            self.assertEqual(204, service.client.delete(f"/api/jobs/{job['id']}").status_code)
            self.assertFalse(service.jobs.upload_dir(job["id"]).exists())
            self.assertFalse(service.jobs.markdown_path(job["id"]).parent.exists())
            self.assertEqual(404, service.client.get(f"/api/jobs/{job['id']}").status_code)
            service.jobs.reserve("d" * 32, "d.txt", ".txt", 1)
            self.assertEqual(409, service.client.delete("/api/jobs/" + "d" * 32).status_code)

    def test_restart_marks_unfinished_jobs_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(password=PASSWORD, data_dir=Path(tmp))
            jobs = Jobs(settings)
            jobs.reserve("e" * 32, "e.txt", ".txt", 1)
            jobs.upload_dir("e" * 32).mkdir()
            jobs._exec("UPDATE jobs SET state = 'running' WHERE id = ?", ("e" * 32,))
            (jobs.work_dir("e" * 32) / "convert_result").mkdir(parents=True)
            restarted = Jobs(replace(settings))
            restarted.recover()
            job = restarted.get("e" * 32)
            self.assertEqual(("interrupted", "INTERRUPTED"), (job["state"], job["error"]))
            self.assertEqual([], list((Path(tmp) / ".work").iterdir()))
            self.assertFalse(restarted.upload_dir("e" * 32).exists())


class LoggingTests(unittest.TestCase):
    def test_audit_and_access_logs_track_jobs_without_names_or_content(self):
        with Service() as service:
            job = service.convert("비밀-계약서.txt", b"confidential body")
            service.client.get(f"/api/jobs/{job['id']}/download")
            raw = (service.settings.log_dir / "audit.log").read_text(encoding="utf-8")
            access = (service.settings.log_dir / "access.log").read_text(encoding="utf-8")
            events = [e["event"] for e in service.log("audit.log") if e.get("job_id") == job["id"]]
            self.assertEqual(["upload_accepted", "conversion_started", "conversion_succeeded",
                              "download_started", "download_sent"], events)
            self.assertIn("login_succeeded", raw)
            for secret in ("비밀", "계약서", "confidential", PASSWORD):
                self.assertNotIn(secret, raw + access)
            self.assertIn("/api/jobs/{job_id}", access)
            self.assertNotIn(job["id"], access)

    def test_unwritable_log_dir_refuses_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "file"
            blocker.write_text("x")
            app = create_app(Settings(password=PASSWORD, data_dir=Path(tmp) / "data", log_dir=blocker))
            with self.assertRaises(OSError), TestClient(app):
                pass


if __name__ == "__main__":
    unittest.main()
