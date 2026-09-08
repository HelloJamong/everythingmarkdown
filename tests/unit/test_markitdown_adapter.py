import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from markitdown import (
    FailedConversionAttempt,
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)
from markitdown import converters

from everythingmarkdown.markitdown_adapter import MarkItDownAdapter
from everythingmarkdown.models import ConversionError, ErrorCode


class AdapterTests(unittest.TestCase):
    def test_single_converter_registration_and_markdown_api(self):
        expected = {
            ".pdf": converters.PdfConverter,
            ".docx": converters.DocxConverter,
            ".pptx": converters.PptxConverter,
            ".xlsx": converters.XlsxConverter,
            ".html": converters.HtmlConverter,
            ".csv": converters.CsvConverter,
            ".txt": converters.PlainTextConverter,
        }
        for extension, converter in expected.items():
            with self.subTest(extension=extension), patch("markitdown.MarkItDown") as factory:
                factory.return_value.convert_local.return_value = SimpleNamespace(markdown="본문")
                path = Path("한글 report.v2" + extension.upper())
                self.assertEqual("본문", MarkItDownAdapter().convert(path))
                factory.assert_called_once_with(enable_builtins=False, enable_plugins=False)
                factory.return_value.register_converter.assert_called_once()
                self.assertIsInstance(factory.return_value.register_converter.call_args.args[0], converter)
                factory.return_value.convert_local.assert_called_once_with(str(path))
                factory.return_value.convert.assert_not_called()

    def test_requests_create_independent_engines(self):
        with patch("markitdown.MarkItDown") as factory:
            factory.return_value.convert_local.return_value = SimpleNamespace(markdown="text")
            adapter = MarkItDownAdapter()
            adapter.convert(Path("a.txt"))
            adapter.convert(Path("b.txt"))
        self.assertEqual(2, factory.call_count)

    def test_missing_import_is_safe_dependency_error(self):
        with patch.dict(sys.modules, {"markitdown": None}), self.assertRaises(ConversionError) as error:
            MarkItDownAdapter().convert(Path("test.txt"))
        self.assertEqual(ErrorCode.MISSING_DEPENDENCY, error.exception.code)

    def test_unsupported_extension_does_not_create_engine(self):
        with patch("markitdown.MarkItDown") as factory, self.assertRaises(ConversionError) as error:
            MarkItDownAdapter().convert(Path("test.zip"))
        self.assertEqual(ErrorCode.UNSUPPORTED_FORMAT, error.exception.code)
        factory.assert_not_called()

    def test_parser_errors_are_sanitized(self):
        cases = [
            (MissingDependencyException("secret document"), ErrorCode.MISSING_DEPENDENCY),
            (ImportError("secret document"), ErrorCode.MISSING_DEPENDENCY),
            (UnsupportedFormatException("secret document"), ErrorCode.CONVERSION_FAILED),
            (RuntimeError("secret document"), ErrorCode.CONVERSION_FAILED),
            (FileConversionException("secret document"), ErrorCode.CONVERSION_FAILED),
        ]
        for cause, code in cases:
            with self.subTest(cause=type(cause)), patch("markitdown.MarkItDown") as factory:
                factory.return_value.convert_local.side_effect = cause
                with self.assertRaises(ConversionError) as error:
                    MarkItDownAdapter().convert(Path("test.txt"))
                self.assertEqual(code, error.exception.code)
                self.assertNotIn("secret document", str(error.exception))
                self.assertTrue(error.exception.__suppress_context__)

    def test_wrapped_missing_dependency_is_identified(self):
        dependency_error = MissingDependencyException("private dependency message")
        attempt = FailedConversionAttempt(None, (type(dependency_error), dependency_error, None))
        with patch("markitdown.MarkItDown") as factory:
            factory.return_value.convert_local.side_effect = FileConversionException(attempts=[attempt])
            with self.assertRaises(ConversionError) as error:
                MarkItDownAdapter().convert(Path("test.pdf"))
        self.assertEqual(ErrorCode.MISSING_DEPENDENCY, error.exception.code)
        self.assertNotIn("private dependency message", str(error.exception))

    def test_wrapped_parser_failure_remains_conversion_error(self):
        parser_error = ValueError("secret document")
        attempts = [
            FailedConversionAttempt(None),
            FailedConversionAttempt(None, (ValueError, parser_error, None)),
        ]
        with patch("markitdown.MarkItDown") as factory:
            factory.return_value.convert_local.side_effect = FileConversionException(attempts=attempts)
            with self.assertRaises(ConversionError) as error:
                MarkItDownAdapter().convert(Path("test.pdf"))
        self.assertEqual(ErrorCode.CONVERSION_FAILED, error.exception.code)

    def test_empty_or_invalid_engine_results(self):
        for value in ("", "\r\n\t ", None, b"bytes"):
            with self.subTest(value=value), patch("markitdown.MarkItDown") as factory:
                factory.return_value.convert_local.return_value = SimpleNamespace(markdown=value)
                with self.assertRaises(ConversionError) as error:
                    MarkItDownAdapter().convert(Path("test.txt"))
                expected = ErrorCode.EMPTY_RESULT if isinstance(value, str) else ErrorCode.CONVERSION_FAILED
                self.assertEqual(expected, error.exception.code)


if __name__ == "__main__":
    unittest.main()
