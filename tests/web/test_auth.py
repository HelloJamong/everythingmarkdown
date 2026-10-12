import os
import time
import unittest
from unittest.mock import patch

from fastapi import Depends
from fastapi.testclient import TestClient

from everythingmarkdown.web import auth
from everythingmarkdown.web.app import create_app
from everythingmarkdown.web.config import EXAMPLE_PASSWORD, ConfigError, Settings, load_settings

PASSWORD = "correct horse battery"
BASE = "https://testserver"


def client_for(app=None) -> TestClient:
    app = app if app is not None else create_app(Settings(password=PASSWORD))
    client = TestClient(app, base_url=BASE, follow_redirects=False)
    client.headers["origin"] = BASE
    return client


def logged_in(client: TestClient) -> TestClient:
    response = client.post("/login", data={"password": PASSWORD})
    assert response.status_code == 303, response.status_code
    return client


class ConfigTests(unittest.TestCase):
    def test_rejects_missing_empty_example_and_short_passwords(self):
        for env in ({}, {"APP_PASSWORD": ""}, {"APP_PASSWORD": "   "},
                    {"APP_PASSWORD": EXAMPLE_PASSWORD}, {"APP_PASSWORD": "short-11ch"}):
            with self.subTest(env=env), self.assertRaises(ConfigError):
                load_settings(env)

    def test_cookie_secure_defaults_on_and_rejects_typos(self):
        self.assertTrue(load_settings({"APP_PASSWORD": PASSWORD}).cookie_secure)
        self.assertFalse(load_settings({"APP_PASSWORD": PASSWORD, "COOKIE_SECURE": "false"}).cookie_secure)
        with self.assertRaises(ConfigError):
            load_settings({"APP_PASSWORD": PASSWORD, "COOKIE_SECURE": "no"})

    def test_app_refuses_to_start_without_password(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigError):
            create_app()


class LoginTests(unittest.TestCase):
    def test_unauthenticated_page_redirects_to_login(self):
        response = client_for().get("/")
        self.assertEqual(303, response.status_code)
        self.assertEqual("/login", response.headers["location"])

    def test_wrong_password_is_rejected_without_session(self):
        client = client_for()
        response = client.post("/login", data={"password": PASSWORD + "x"})
        self.assertEqual(401, response.status_code)
        self.assertNotIn(PASSWORD, response.text)
        self.assertEqual(303, client.get("/").status_code)

    def test_correct_password_logs_in_with_hardened_cookie(self):
        client = client_for()
        response = client.post("/login", data={"password": PASSWORD})
        self.assertEqual("/", response.headers["location"])
        cookie = response.headers["set-cookie"].lower()
        for flag in ("emd_session=", "httponly", "samesite=lax", "secure", "max-age=28800"):
            self.assertIn(flag, cookie)
        self.assertNotIn(PASSWORD.lower(), cookie)
        self.assertEqual(200, client.get("/").status_code)

    def test_cookie_secure_false_drops_secure_flag(self):
        client = client_for(create_app(Settings(password=PASSWORD, cookie_secure=False)))
        cookie = client.post("/login", data={"password": PASSWORD}).headers["set-cookie"].lower()
        self.assertNotIn("secure", cookie)

    def test_logout_ends_session(self):
        client = logged_in(client_for())
        self.assertEqual(303, client.post("/logout").status_code)
        self.assertEqual(303, client.get("/").status_code)

    def test_cookie_from_previous_start_is_rejected(self):
        old = logged_in(client_for())
        restarted = client_for()
        restarted.cookies = old.cookies
        self.assertEqual(303, restarted.get("/").status_code)

    def test_tampered_cookie_is_rejected(self):
        client = logged_in(client_for())
        value = client.cookies["emd_session"]
        client.cookies.set("emd_session", value[:-2] + ("aa" if value[-2:] != "aa" else "bb"))
        self.assertEqual(303, client.get("/").status_code)

    def test_session_expires_eight_hours_after_login_even_if_active(self):
        client = client_for()
        with patch.object(auth, "time") as fake_time:
            fake_time.time.return_value = time.time() - auth.SESSION_MAX_AGE - 1
            logged_in(client)
        response = client.get("/")
        self.assertEqual("/login?expired", response.headers["location"])
        self.assertIn("만료", client.get("/login?expired").text)

    def test_api_dependency_returns_401_without_login(self):
        app = create_app(Settings(password=PASSWORD))
        app.get("/api/probe", dependencies=[Depends(auth.require_login)])(lambda: {"ok": True})
        client = client_for(app)
        self.assertEqual(401, client.get("/api/probe").status_code)
        self.assertEqual(200, logged_in(client).get("/api/probe").status_code)

    def test_healthz_needs_no_login(self):
        self.assertEqual({"status": "ok"}, client_for().get("/healthz").json())


class OriginTests(unittest.TestCase):
    def test_state_changing_requests_need_same_origin(self):
        client = client_for()
        for headers in ({"origin": "https://evil.example"}, {"origin": "null"}):
            with self.subTest(headers=headers):
                self.assertEqual(403, client.post("/login", data={"password": PASSWORD}, headers=headers).status_code)
        del client.headers["origin"]
        self.assertEqual(403, client.post("/login", data={"password": PASSWORD}).status_code)
        same_site_referer = {"referer": BASE + "/login"}
        self.assertEqual(303, client.post("/login", data={"password": PASSWORD}, headers=same_site_referer).status_code)


class RateLimitTests(unittest.TestCase):
    def test_five_failures_per_minute_block_even_the_right_password(self):
        client = client_for()
        for _ in range(5):
            self.assertEqual(401, client.post("/login", data={"password": "wrong-password"}).status_code)
        self.assertEqual(429, client.post("/login", data={"password": PASSWORD}).status_code)

    def test_window_expires(self):
        now = [0.0]
        limiter = auth.LoginLimiter(clock=lambda: now[0])
        for _ in range(5):
            limiter.fail("1.2.3.4")
        self.assertTrue(limiter.blocked("1.2.3.4"))
        self.assertFalse(limiter.blocked("5.6.7.8"))
        now[0] = 61.0
        self.assertFalse(limiter.blocked("1.2.3.4"))


if __name__ == "__main__":
    unittest.main()
