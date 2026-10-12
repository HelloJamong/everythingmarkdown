import hashlib
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from everythingmarkdown import ConversionError, ConversionRequest, ConversionService, ErrorCode
from everythingmarkdown.markitdown_adapter import SUPPORTED_EXTENSIONS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


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

    def test_same_name_in_different_launch_dirs_is_independent(self):
        # Web jobs each get their own launch_dir (/data/.work/<job_id>) for a shared upload name.
        with tempfile.TemporaryDirectory() as directory:
            service = ConversionService()
            outputs = []
            for job in ("job-a", "job-b"):
                upload = Path(directory) / "uploads" / job / "input.txt"
                upload.parent.mkdir(parents=True)
                upload.write_text(f"content of {job}", encoding="utf-8")
                launch = Path(directory) / ".work" / job
                launch.mkdir(parents=True)
                result = service.convert(ConversionRequest(upload, launch))
                self.assertEqual(launch / "convert_result" / "input.md", result.output_path)
                outputs.append(result.output_path)
            self.assertIn("job-a", outputs[0].read_text(encoding="utf-8"))
            self.assertNotIn("job-b", outputs[0].read_text(encoding="utf-8"))
            self.assertIn("job-b", outputs[1].read_text(encoding="utf-8"))

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
