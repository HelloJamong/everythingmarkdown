"""AUTH_ENABLED=false: no login, each browser only reaches its own jobs."""

import sqlite3
import stat
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from everythingmarkdown.web.app import create_app
from everythingmarkdown.web.config import ConfigError, Settings, load_settings
from everythingmarkdown.web.jobs import Jobs

BASE = "https://testserver"


def browser(app) -> TestClient:
    client = TestClient(app, base_url=BASE, follow_redirects=False)
    client.headers["origin"] = BASE
    return client


def wait(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


class AnonymousConfigTests(unittest.TestCase):
    def test_auth_can_be_disabled_without_password(self):
        settings = load_settings({"AUTH_ENABLED": "false"})
        self.assertFalse(settings.auth_enabled)
        self.assertEqual("", settings.password)
        self.assertTrue(load_settings({"APP_PASSWORD": "correct horse battery"}).auth_enabled)
        for bad in ({"AUTH_ENABLED": "no"}, {"AUTH_ENABLED": "false", "MAX_ACTIVE_JOBS": "0"},
                    {"AUTH_ENABLED": "false", "CONVERSION_WORKERS": "-1"}):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                load_settings(bad)
        tuned = load_settings({"AUTH_ENABLED": "false", "MAX_ACTIVE_JOBS": "10", "CONVERSION_WORKERS": "2"})
        self.assertEqual((10, 2), (tuned.max_active_jobs, tuned.conversion_workers))


class AnonymousModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.settings = Settings(password="", auth_enabled=False, data_dir=root / "data", log_dir=root / "logs")

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_login_screen_and_no_logout(self):
        with browser(create_app(self.settings)) as a:
            page = a.get("/")
            self.assertEqual(200, page.status_code)
            self.assertNotIn('action="/logout"', page.text)
            self.assertIn("max-age=2592000", page.headers["set-cookie"].lower())
            self.assertEqual("/", a.get("/login").headers["location"])
            self.assertEqual("/", a.post("/login", data={"password": "x"}).headers["location"])
            self.assertIn("auth_disabled", (self.settings.log_dir / "audit.log").read_text())

    def test_browsers_only_see_their_own_jobs(self):
        app = create_app(self.settings)
        with browser(app) as a, browser(app) as b:
            job = a.post("/api/jobs", files={"file": ("mine.txt", b"private text")}).json()
            self.assertEqual("succeeded", wait(a, job["id"])["state"])
            self.assertEqual(["mine.txt"], [j["name"] for j in a.get("/api/jobs").json()])
            self.assertEqual([], b.get("/api/jobs").json())
            for method, path in (("GET", ""), ("GET", "/preview"), ("GET", "/download"), ("DELETE", "")):
                with self.subTest(method=method, path=path):
                    self.assertEqual(404, b.request(method, f"/api/jobs/{job['id']}{path}").status_code)
            self.assertIn("private text", a.get(f"/api/jobs/{job['id']}/preview").text)

    def test_browser_keeps_its_jobs_after_restart(self):
        with browser(create_app(self.settings)) as a:
            job = a.post("/api/jobs", files={"file": ("keep.txt", b"kept")}).json()
            wait(a, job["id"])
            cookies = a.cookies
        key = self.settings.data_dir / ".session_key"
        self.assertEqual(0o600, stat.S_IMODE(key.stat().st_mode))
        with browser(create_app(self.settings)) as restarted:
            restarted.cookies = cookies
            self.assertEqual([job["id"]], [j["id"] for j in restarted.get("/api/jobs").json()])

    def test_more_conversion_workers_start_more_runners(self):
        jobs = Jobs(Settings(password="", auth_enabled=False, data_dir=self.settings.data_dir,
                             conversion_workers=3))
        jobs.start()
        try:
            self.assertEqual(4, len(jobs._threads))  # 3 runners + cleanup
        finally:
            jobs.stop()
        self.assertTrue(all(not t.is_alive() for t in jobs._threads))


class SchemaMigrationTests(unittest.TestCase):
    def test_26_1_database_gains_owner_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(Path(tmp) / "app.db")
            db.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, name TEXT NOT NULL, ext TEXT NOT NULL,"
                       " size INTEGER NOT NULL, state TEXT NOT NULL, error TEXT, created_at REAL NOT NULL,"
                       " finished_at REAL, upload_expires_at REAL, upload_gone INTEGER NOT NULL DEFAULT 0,"
                       " markdown_keep INTEGER NOT NULL, markdown_ttl INTEGER NOT NULL,"
                       " markdown_expires_at REAL, markdown_gone INTEGER NOT NULL DEFAULT 0)")
            db.execute("INSERT INTO jobs (id, name, ext, size, state, created_at, markdown_keep, markdown_ttl)"
                       " VALUES (?, 'a.txt', '.txt', 1, 'succeeded', 0, 1, 1)", ("a" * 32,))
            db.execute("PRAGMA user_version = 1")
            db.commit()
            db.close()
            jobs = Jobs(Settings(password="x" * 12, data_dir=Path(tmp)))
            self.assertEqual("", jobs.get("a" * 32)["owner"])
            self.assertEqual(["a" * 32], [j["id"] for j in jobs.recent()])
            self.assertEqual(2, jobs._db.execute("PRAGMA user_version").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
