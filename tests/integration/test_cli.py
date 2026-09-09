import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from everythingmarkdown.markitdown_adapter import SUPPORTED_EXTENSIONS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class CliIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    def run_cli(self, args, *, cwd=None, console=False):
        if console:
            name = "everythingmarkdown.exe" if os.name == "nt" else "everythingmarkdown"
            command = [str(Path(sys.executable).parent / name)]
        else:
            command = [sys.executable, "-m", "everythingmarkdown"]
        return subprocess.run(
            [*command, *map(str, args)], cwd=cwd or self.root, env=self.env,
            input="", text=True, encoding="utf-8", capture_output=True, timeout=15,
        )

    def test_module_converts_seven_formats_in_separate_cwds(self):
        for extension in SUPPORTED_EXTENSIONS:
            with self.subTest(extension=extension):
                cwd = self.root / extension[1:]
                cwd.mkdir()
                result = self.run_cli([FIXTURES / f"sample{extension}"], cwd=cwd)
                output = cwd / "convert_result" / "sample.md"
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(str(output) + "\n", result.stdout)
                self.assertEqual("", result.stderr)
                self.assertIn("EverythingMarkdown P0 sample", output.read_text(encoding="utf-8"))

    def test_installed_console_entry_point_matches_module(self):
        source = self.root / "한글 sample.v2.TXT"
        source.write_text("한글 본문\n", encoding="utf-8")
        result = self.run_cli([source.name], console=True)
        output = self.root / "convert_result" / "한글 sample.v2.md"
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(str(output) + "\n", result.stdout)
        self.assertEqual("한글 본문\n", output.read_text(encoding="utf-8"))
        self.assertEqual("", result.stderr)

    def test_collision_returns_four_and_preserves_result(self):
        source = FIXTURES / "sample.txt"
        first = self.run_cli([source])
        self.assertEqual(0, first.returncode, first.stderr)
        output = Path(first.stdout.strip())
        original = output.read_bytes()
        second = self.run_cli([source])
        self.assertEqual(4, second.returncode)
        self.assertEqual("", second.stdout)
        self.assertIn("OUTPUT_CONFLICT", second.stderr)
        self.assertEqual(original, output.read_bytes())

    def test_missing_input_returns_two(self):
        result = self.run_cli(["missing.txt"])
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("NOT_FOUND", result.stderr)

    def test_empty_document_returns_three(self):
        source = self.root / "empty.txt"
        source.write_text(" \n", encoding="utf-8")
        result = self.run_cli([source])
        self.assertEqual(3, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("EMPTY_RESULT", result.stderr)

    def test_no_argument_with_piped_stdin_does_not_wait(self):
        result = self.run_cli([])
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertNotIn("변환할 파일 경로:", result.stderr)

    def test_help_and_version_work_without_conversion(self):
        for argument in ("--help", "--version"):
            with self.subTest(argument=argument):
                result = self.run_cli([argument])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("", result.stderr)
                self.assertTrue(result.stdout)
        self.assertFalse((self.root / "convert_result").exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux PTY smoke; target OS tests deferred")
    def test_real_tty_input_converts_quoted_unicode_path(self):
        import pty

        source = self.root / "한글 문서.txt"
        source.write_text("local content", encoding="utf-8")
        master, slave = pty.openpty()
        try:
            with subprocess.Popen(
                [sys.executable, "-m", "everythingmarkdown"], cwd=self.root, env=self.env,
                stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as process:
                os.close(slave)
                slave = None
                os.write(master, f'"{source.name}"\n'.encode())
                try:
                    stdout, stderr = process.communicate(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    self.fail("TTY CLI did not finish")
                self.assertEqual(0, process.returncode, stderr.decode("utf-8"))
                output = self.root / "convert_result" / "한글 문서.md"
                self.assertEqual(str(output) + "\n", stdout.decode("utf-8"))
                self.assertIn("변환할 파일 경로:", stderr.decode("utf-8"))
                self.assertEqual("local content", output.read_text(encoding="utf-8"))
        finally:
            os.close(master)
            if slave is not None:
                os.close(slave)


if __name__ == "__main__":
    unittest.main()
