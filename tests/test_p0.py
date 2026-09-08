import contextlib
import hashlib
import io
import json
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from everythingmarkdown import p0

FIXTURES = Path(__file__).parent / "fixtures"


class P0Tests(unittest.TestCase):
    def test_seven_real_formats_without_python_socket_attempts(self):
        attempts = []

        def deny(*args, **kwargs):
            attempts.append("network attempt")
            raise AssertionError("Network access during conversion")

        with patch.object(socket.socket, "connect", deny), \
             patch.object(socket.socket, "connect_ex", deny), \
             patch.object(socket, "getaddrinfo", deny):
            for extension in p0.CONVERTERS:
                with self.subTest(extension=extension):
                    path = FIXTURES / f"sample{extension}"
                    before = hashlib.sha256(path.read_bytes()).digest()
                    result = p0.convert_sample(path)
                    self.assertIn(p0.FIXTURE_MARKER, result)
                    if extension in (".txt", ".html"):
                        self.assertIn("한글 확인", result)
                    self.assertEqual(before, hashlib.sha256(path.read_bytes()).digest())
        self.assertEqual([], attempts)

    def test_registers_only_selected_converter(self):
        for extension, converter in p0.CONVERTERS.items():
            with self.subTest(extension=extension), patch.object(p0, "MarkItDown") as factory:
                factory.return_value.convert_local.return_value = SimpleNamespace(markdown="sample")
                path = FIXTURES / f"sample{extension}"
                self.assertEqual("sample", p0.convert_sample(path))
                factory.assert_called_once_with(enable_builtins=False, enable_plugins=False)
                factory.return_value.register_converter.assert_called_once()
                actual = factory.return_value.register_converter.call_args.args[0]
                self.assertIsInstance(actual, converter)
                factory.return_value.convert_local.assert_called_once_with(str(path))

    def test_disguised_zip_rejected_before_engine(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(p0, "MarkItDown") as factory:
            for extension in p0.CONVERTERS:
                path = Path(directory) / f"fake{extension}"
                with ZipFile(path, "w") as archive:
                    archive.writestr("payload.txt", "sample")
                with self.subTest(extension=extension), self.assertRaises(ValueError):
                    p0.convert_sample(path)
            factory.assert_not_called()

    def test_nonzip_office_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for extension in p0.OOXML_PARTS:
                path = Path(directory) / f"fake{extension}"
                path.write_text("not office", encoding="utf-8")
                with self.subTest(extension=extension), self.assertRaises(ValueError):
                    p0.convert_sample(path)

    def test_invalid_paths(self):
        for path in (FIXTURES, FIXTURES / "missing.txt", Path("https://example.com/file.txt"), FIXTURES / "README.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                p0.convert_sample(path)

    def test_size_limit(self):
        with patch.object(p0, "MAX_BYTES", 1), self.assertRaises(ValueError):
            p0.convert_sample(FIXTURES / "sample.txt")

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "link.txt"
            try:
                path.symlink_to((FIXTURES / "sample.txt").resolve())
            except OSError as error:
                self.skipTest(f"Symlinks unavailable: {error}")
            with self.assertRaises(ValueError):
                p0.convert_sample(path)

    def test_uppercase_unicode_space_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "한글 sample.v2.TXT"
            shutil.copyfile(FIXTURES / "sample.txt", path)
            self.assertIn(p0.FIXTURE_MARKER, p0.convert_sample(path))

    def test_empty_engine_result_rejected(self):
        with patch.object(p0, "MarkItDown") as factory:
            factory.return_value.convert_local.return_value = SimpleNamespace(markdown=" \n")
            with self.assertRaises(ValueError):
                p0.convert_sample(FIXTURES / "sample.txt")

    def test_cli_fixture_report(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, p0.main(["--fixtures", str(FIXTURES)]))
        report = json.loads(output.getvalue())
        self.assertEqual(7, len(report["results"]))
        self.assertEqual(str(Path.cwd()), report["cwd"])
        self.assertNotIn(p0.FIXTURE_MARKER, output.getvalue())

    def test_cli_non_tty_does_not_wait(self):
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.input") as read, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            p0.main([])
        self.assertEqual(2, error.exception.code)
        read.assert_not_called()

    def test_cli_interactive_path(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value=f'"{FIXTURES / "sample.txt"}"'), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(0, p0.main([]))
        self.assertIn("Sample file path:", errors.getvalue())
        self.assertEqual(1, len(json.loads(output.getvalue())["results"]))

    def test_cli_cancellation(self):
        for signal in (EOFError, KeyboardInterrupt):
            with self.subTest(signal=signal), patch("sys.stdin.isatty", return_value=True), \
                 patch("builtins.input", side_effect=signal), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(130, p0.main([]))

    def test_cli_empty_input(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value=""), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            p0.main([])
        self.assertEqual(2, error.exception.code)

    def test_cli_does_not_leak_document_exception(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(p0, "convert_sample", side_effect=RuntimeError("secret document")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(3, p0.main([str(FIXTURES / "sample.txt")]))
        self.assertEqual("", output.getvalue())
        self.assertNotIn("secret document", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
