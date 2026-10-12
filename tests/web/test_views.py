import unittest

from .test_jobs import PASSWORD, Service


class ViewTests(unittest.TestCase):
    def test_login_page_uses_local_assets_only(self):
        with Service() as service:
            service.client.post("/logout")
            page = service.client.get("/login").text
            for asset in ('href="/static/app.css"', 'href="/static/logo.ico"', 'src="/static/logo.ico"'):
                self.assertIn(asset, page)
            self.assertNotIn("https://", page)  # no web fonts or CDNs

    def test_static_assets_are_served(self):
        with Service() as service:
            for path, kind in (("/static/app.css", "text/css"), ("/static/app.js", "javascript"),
                               ("/static/logo.ico", "image")):
                response = service.client.get(path)
                self.assertEqual(200, response.status_code, path)
                self.assertIn(kind, response.headers["content-type"])

    def test_screen_states_limits_and_default_policy(self):
        with Service() as service:
            page = service.client.get("/").text
            self.assertIn('accept=".pdf,.docx,.pptx,.xlsx,.html,.csv,.txt"', page)
            self.assertIn("PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT", page)
            self.assertIn("최대 25 MiB", page)
            self.assertIn("변환 후 바로 삭제", page)
            self.assertIn("다운로드 후 삭제 (받지 않으면 60분 뒤)", page)
            self.assertIn('src="/static/app.js"', page)
            self.assertNotIn(PASSWORD, page)

    def test_topbar_shows_repo_link_then_version_then_logout(self):
        from importlib.metadata import version
        with Service() as service:
            page = service.client.get("/").text
            repo = page.index('href="https://github.com/HelloJamong/everythingmarkdown"')
            ver = page.index(f'<span class="version" title="현재 버전">{version("everythingmarkdown")}</span>')
            logout = page.index('action="/logout"')
            self.assertLess(repo, ver)
            self.assertLess(ver, logout)
            self.assertIn('rel="noopener noreferrer"', page)

    def test_screen_states_keep_days(self):
        with Service(upload_ttl=3 * 86400, markdown_ttl=7 * 86400) as service:
            page = service.client.get("/").text
            self.assertIn("<dd>3일 보관</dd>", page)
            self.assertIn("<dd>7일 보관</dd>", page)


if __name__ == "__main__":
    unittest.main()
