import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from threading import Barrier
from unittest.mock import Mock, patch

from everythingmarkdown import (
    ConversionError,
    ConversionRequest,
    ConversionResult,
    ConversionService,
    ErrorCode,
)


class ServiceEdgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "sample.txt"
        self.source.write_text("original", encoding="utf-8")
        self.output = self.root / "convert_result" / "sample.md"
        self.request = ConversionRequest(self.source, self.root)
        self.adapter = Mock()
        self.adapter.convert.return_value = "converted"

    def test_two_concurrent_requests_only_one_succeeds(self):
        barrier = Barrier(2)

        class SynchronizedAdapter:
            def convert(self, path):
                barrier.wait(timeout=5)
                return "whole result"

        service = ConversionService(SynchronizedAdapter())

        def run():
            try:
                return service.convert(self.request)
            except ConversionError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(1, sum(isinstance(item, ConversionResult) for item in results))
        errors = [item for item in results if isinstance(item, ConversionError)]
        self.assertEqual([ErrorCode.OUTPUT_CONFLICT], [error.code for error in errors])
        self.assertEqual("whole result", self.output.read_text(encoding="utf-8"))

    def test_failed_write_never_deletes_replacement_file(self):
        original_open = Path.open

        class ReplacingWriter:
            def __init__(self, path):
                self.path = path
                self.stream = original_open(path, "x", encoding="utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def fileno(self):
                return self.stream.fileno()

            def write(self, value):
                self.stream.write("partial")
                self.stream.close()
                self.path.rename(self.path.with_suffix(".moved"))
                self.path.write_text("unrelated replacement", encoding="utf-8")
                raise OSError("disk error")

        def open_file(path, *args, **kwargs):
            if args and args[0] == "x":
                return ReplacingWriter(path)
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_file), self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.WRITE_FAILED, error.exception.code)
        self.assertTrue(error.exception.warnings)
        self.assertEqual(self.output, error.exception.path)
        self.assertEqual("unrelated replacement", self.output.read_text(encoding="utf-8"))

    def test_input_read_permission_error_is_sanitized(self):
        with patch.object(Path, "open", side_effect=PermissionError("secret")), \
             self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.INVALID_INPUT, error.exception.code)
        self.assertNotIn("secret", str(error.exception))
        self.adapter.convert.assert_not_called()

    def test_output_preflight_permission_failure_avoids_engine(self):
        with patch("everythingmarkdown.service.os.access", return_value=False), \
             self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.OUTPUT_UNWRITABLE, error.exception.code)
        self.adapter.convert.assert_not_called()

    def test_missing_launch_directory_is_not_created_or_redirected(self):
        missing = self.root / "absent"
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(ConversionRequest(self.source, missing))
        self.assertEqual(ErrorCode.OUTPUT_UNWRITABLE, error.exception.code)
        self.assertFalse(missing.exists())
        self.adapter.convert.assert_not_called()

    def test_broken_input_symlink_is_invalid_not_followed(self):
        link = self.root / "broken.txt"
        try:
            link.symlink_to(self.root / "absent.txt")
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(ConversionRequest(link, self.root))
        self.assertEqual(ErrorCode.INVALID_INPUT, error.exception.code)
        self.assertTrue(link.is_symlink())

    def test_broken_output_directory_link_is_rejected(self):
        directory = self.output.parent
        try:
            directory.symlink_to(self.root / "absent", target_is_directory=True)
        except OSError as error:
            self.skipTest(str(error))
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.OUTPUT_UNWRITABLE, error.exception.code)
        self.assertTrue(directory.is_symlink())

    def test_urls_are_rejected_before_adapter(self):
        for url in ("https://example.invalid/a.txt", "file:///tmp/a.txt", "data:text/plain,hello"):
            with self.subTest(url=url), self.assertRaises(ConversionError) as error:
                ConversionService(self.adapter).convert(ConversionRequest(Path(url), self.root))
            self.assertEqual(ErrorCode.INVALID_INPUT, error.exception.code)
        self.adapter.convert.assert_not_called()

    def test_non_string_adapter_result_is_not_written(self):
        self.adapter.convert.return_value = None
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.CONVERSION_FAILED, error.exception.code)
        self.assertFalse(self.output.exists())

    def test_dependency_error_survives_service_boundary(self):
        self.adapter.convert.side_effect = ConversionError(ErrorCode.MISSING_DEPENDENCY, path=self.source)
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.MISSING_DEPENDENCY, error.exception.code)
        self.assertFalse(self.output.exists())

    def test_conversion_cancelled_without_output(self):
        self.adapter.convert.side_effect = KeyboardInterrupt()
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.CANCELLED, error.exception.code)
        self.assertFalse(self.output.exists())

    def test_unencodable_text_is_cleaned_up(self):
        self.adapter.convert.return_value = "bad surrogate \ud800"
        with self.assertRaises(ConversionError) as error:
            ConversionService(self.adapter).convert(self.request)
        self.assertEqual(ErrorCode.WRITE_FAILED, error.exception.code)
        self.assertFalse(self.output.exists())

    def test_all_error_codes_have_stable_exit_status(self):
        statuses = [2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 130]
        self.assertEqual(statuses, [ConversionError(code).exit_code for code in ErrorCode])

    def test_models_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.request.launch_dir = self.root / "changed"
        result = ConversionResult(self.output)
        with self.assertRaises(FrozenInstanceError):
            result.output_path = self.root / "changed"


if __name__ == "__main__":
    unittest.main()
