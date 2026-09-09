import hashlib
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from everythingmarkdown import ConversionError, ConversionRequest, ConversionService, ErrorCode
from everythingmarkdown.gui import ConversionController
from everythingmarkdown.markitdown_adapter import SUPPORTED_EXTENSIONS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


class ConversionIntegrationTests(unittest.TestCase):
    def test_seven_formats_save_utf8_in_launch_directory_without_network(self):
        attempts = []

        def deny(*args, **kwargs):
            attempts.append("network attempt")
            raise AssertionError("Unexpected network access")

        originals = {p: hashlib.sha256(p.read_bytes()).digest() for p in FIXTURES.glob("sample.*")}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(socket.socket, "connect", deny), \
             patch.object(socket.socket, "connect_ex", deny), \
             patch.object(socket, "getaddrinfo", deny):
            for extension in SUPPORTED_EXTENSIONS:
                with self.subTest(extension=extension):
                    launch = Path(directory) / extension[1:]
                    launch.mkdir()
                    result = ConversionService().convert(
                        ConversionRequest(FIXTURES / f"sample{extension}", launch)
                    )
                    self.assertEqual(launch / "convert_result" / "sample.md", result.output_path)
                    data = result.output_path.read_bytes()
                    self.assertIn("EverythingMarkdown P0 sample", data.decode("utf-8"))
                    self.assertNotIn(b"\r", data)
                    self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
                    self.assertEqual((), result.warnings)
        self.assertEqual([], attempts)
        self.assertEqual(originals, {p: hashlib.sha256(p.read_bytes()).digest() for p in originals})

    def test_same_stem_different_formats_preserve_first_result(self):
        with tempfile.TemporaryDirectory() as directory:
            service = ConversionService()
            launch = Path(directory)
            result = service.convert(ConversionRequest(FIXTURES / "sample.pdf", launch))
            original = result.output_path.read_bytes()
            with self.assertRaises(ConversionError) as error:
                service.convert(ConversionRequest(FIXTURES / "sample.docx", launch))
            self.assertEqual(ErrorCode.OUTPUT_CONFLICT, error.exception.code)
            self.assertEqual(original, result.output_path.read_bytes())

    def test_corrupt_pdf_is_safe_conversion_error(self):
        with tempfile.TemporaryDirectory() as directory:
            launch = Path(directory)
            source = launch / "damaged.pdf"
            source.write_bytes(b"%PDF-1.4\nprivate document text, no PDF structure")
            with self.assertRaises(ConversionError) as error:
                ConversionService().convert(ConversionRequest(source, launch))
            self.assertEqual(ErrorCode.CONVERSION_FAILED, error.exception.code)
            self.assertNotIn("private document", str(error.exception))
            self.assertFalse((launch / "convert_result" / "damaged.md").exists())

    def test_text_free_pdf_fails_without_claiming_ocr(self):
        # A13: a PDF whose page carries no extractable text must fail as EMPTY_RESULT,
        # never a silently empty or fabricated .md.
        blank_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << >> >>endobj\n"
            b"4 0 obj<< /Length 0 >>\nstream\n\nendstream endobj\n"
            b"trailer<< /Root 1 0 R >>\n%%EOF\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            launch = Path(directory)
            source = launch / "scan.pdf"
            source.write_bytes(blank_pdf)
            with self.assertRaises(ConversionError) as error:
                ConversionService().convert(ConversionRequest(source, launch))
            self.assertIn(
                error.exception.code, {ErrorCode.EMPTY_RESULT, ErrorCode.CONVERSION_FAILED}
            )
            self.assertFalse((launch / "convert_result" / "scan.md").exists())

    def test_empty_text_is_not_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            launch = Path(directory)
            source = launch / "empty.txt"
            source.write_text(" \n\t", encoding="utf-8")
            with self.assertRaises(ConversionError) as error:
                ConversionService().convert(ConversionRequest(source, launch))
            self.assertEqual(ErrorCode.EMPTY_RESULT, error.exception.code)
            self.assertFalse((launch / "convert_result" / "empty.md").exists())

    def test_gui_and_cli_produce_identical_result_for_same_input(self):
        # A02: the same fixture + launch dir, converted through the GUI controller and
        # through the CLI subprocess, must leave the launch dir in the same state -
        # same files at the same relative paths with identical bytes, nothing extra.
        source = FIXTURES / "sample.docx"

        with tempfile.TemporaryDirectory() as gui_dir:
            launch = Path(gui_dir)
            jobs: list = []
            controller = ConversionController(launch, Mock(), run_async=jobs.append)
            controller.select_file(str(source))
            controller.convert()
            for job in jobs:
                job()
            self.assertFalse(controller.poll())
            gui_tree = _tree(launch)

        with tempfile.TemporaryDirectory() as cli_dir:
            launch = Path(cli_dir)
            completed = subprocess.run(
                [sys.executable, "-m", "everythingmarkdown", str(source)],
                cwd=launch, input="", text=True, capture_output=True, timeout=60,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            cli_tree = _tree(launch)

        self.assertEqual({"convert_result/sample.md"}, set(gui_tree))
        self.assertEqual(gui_tree, cli_tree)

    def test_html_external_references_do_not_fetch(self):
        attempts = []

        def deny(*args, **kwargs):
            attempts.append("network attempt")
            raise AssertionError("Unexpected network access")

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(socket.socket, "connect", deny), \
             patch.object(socket.socket, "connect_ex", deny), \
             patch.object(socket, "getaddrinfo", deny):
            launch = Path(directory)
            source = launch / "external.html"
            source.write_text(
                '<html><head><link rel="stylesheet" href="https://example.invalid/style.css"></head>'
                '<body><h1>Local content</h1><img src="https://example.invalid/image.png">'
                '<script src="https://example.invalid/app.js"></script></body></html>',
                encoding="utf-8",
            )
            result = ConversionService().convert(ConversionRequest(source, launch))
            self.assertIn("Local content", result.output_path.read_text(encoding="utf-8"))
        self.assertEqual([], attempts)


if __name__ == "__main__":
    unittest.main()
