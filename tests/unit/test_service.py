import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from everythingmarkdown.models import ConversionError, ConversionRequest, ErrorCode
from everythingmarkdown.service import ConversionService


class ConversionServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.launch_dir = self.root / "launch dir"
        self.input_dir = self.root / "입력 폴더"
        self.cwd = self.root / "current"
        self.launch_dir.mkdir()
        self.input_dir.mkdir()
        self.cwd.mkdir()
        self.adapter = MagicMock()
        self.adapter.convert.return_value = "# converted\ncontent\n"
        self.service = ConversionService(adapter=self.adapter)

    def tearDown(self):
        self.tmp.cleanup()

    def make_file(self, name="sample.txt", content="source"):
        path = self.input_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def make_request(self, input_path):
        return ConversionRequest(input_path=Path(input_path), launch_dir=self.launch_dir)

    def assert_conversion_error(self, code, request):
        with self.assertRaises(ConversionError) as raised:
            self.service.convert(request)
        self.assertEqual(code, raised.exception.code)
        self.assertIsInstance(raised.exception.exit_code, int)
        return raised.exception

    def assert_no_output(self, stem="sample"):
        self.assertFalse((self.launch_dir / "convert_result" / f"{stem}.md").exists())

    def test_relative_input_resolves_against_launch_dir_not_process_cwd(self):
        source = self.launch_dir / "relative.txt"
        source.write_text("source", encoding="utf-8")
        seen_cwd = []

        def convert(path):
            seen_cwd.append(Path.cwd())
            return "# converted\ncontent\n"

        self.adapter.convert.side_effect = convert
        before = Path.cwd()
        try:
            os.chdir(self.cwd)
            result = self.service.convert(ConversionRequest(Path("relative.txt"), self.launch_dir))
            self.assertEqual(self.cwd, Path.cwd())
        finally:
            os.chdir(before)
        self.assertEqual(self.launch_dir / "convert_result" / "relative.md", result.output_path)
        self.assertTrue(result.output_path.exists())
        self.adapter.convert.assert_called_once_with(source)
        self.assertEqual([self.cwd], seen_cwd)

    def test_absolute_input_keeps_launch_dir_as_output_base(self):
        source = self.make_file("outside.txt")
        result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "outside.md", result.output_path)
        self.assertFalse((self.input_dir / "convert_result").exists())

    def test_rejects_relative_launch_dir(self):
        source = self.make_file()
        request = ConversionRequest(source, Path("relative-launch"))
        self.assert_conversion_error(ErrorCode.INVALID_INPUT, request)
        self.adapter.convert.assert_not_called()

    def test_rejects_missing_input(self):
        self.assert_conversion_error(ErrorCode.NOT_FOUND, self.make_request(self.input_dir / "missing.txt"))
        self.adapter.convert.assert_not_called()

    def test_rejects_directory_input(self):
        self.assert_conversion_error(ErrorCode.INVALID_INPUT, self.make_request(self.input_dir))
        self.adapter.convert.assert_not_called()

    def test_rejects_symlink_input(self):
        target = self.make_file("target.txt")
        link = self.input_dir / "link.txt"
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest(f"Symlinks unavailable: {error}")
        self.assert_conversion_error(ErrorCode.INVALID_INPUT, self.make_request(link))
        self.adapter.convert.assert_not_called()

    def test_rejects_unsupported_extension(self):
        source = self.make_file("notes.md")
        self.assert_conversion_error(ErrorCode.UNSUPPORTED_FORMAT, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_rejects_oversize_input(self):
        source = self.make_file("big.txt", "12345")
        with patch("everythingmarkdown.service.MAX_INPUT_BYTES", 4):
            self.assert_conversion_error(ErrorCode.TOO_LARGE, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_accepts_file_at_size_limit(self):
        source = self.make_file("limit.txt", "1234")
        with patch("everythingmarkdown.service.MAX_INPUT_BYTES", 4):
            result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "limit.md", result.output_path)
        self.adapter.convert.assert_called_once_with(source)

    def test_rejects_disguised_zip_for_plain_text_extension(self):
        source = self.input_dir / "fake.txt"
        with ZipFile(source, "w") as archive:
            archive.writestr("payload.txt", "data")
        self.assert_conversion_error(ErrorCode.INVALID_INPUT, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_rejects_office_zip_missing_required_ooxml_parts(self):
        for extension in (".docx", ".pptx", ".xlsx"):
            with self.subTest(extension=extension):
                source = self.input_dir / f"bad{extension}"
                with ZipFile(source, "w") as archive:
                    archive.writestr("[Content_Types].xml", "<Types />")
                self.assert_conversion_error(ErrorCode.INVALID_INPUT, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_accepts_docx_ooxml_zip_structure(self):
        source = self.input_dir / "good.docx"
        with ZipFile(source, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "good.md", result.output_path)
        self.adapter.convert.assert_called_once_with(source)

    def test_accepts_pptx_ooxml_zip_structure(self):
        source = self.input_dir / "good.pptx"
        with ZipFile(source, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("ppt/presentation.xml", "<presentation />")
        result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "good.md", result.output_path)

    def test_accepts_xlsx_ooxml_zip_structure(self):
        source = self.input_dir / "good.xlsx"
        with ZipFile(source, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("xl/workbook.xml", "<workbook />")
        result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "good.md", result.output_path)

    def test_preserves_unicode_spaces_uppercase_and_multidot_stem(self):
        source = self.make_file("한 글 report.v2.TXT")
        result = self.service.convert(self.make_request(source))
        self.assertEqual(self.launch_dir / "convert_result" / "한 글 report.v2.md", result.output_path)
        self.assertTrue(result.output_path.exists())

    def test_creates_convert_result_directory_when_missing(self):
        source = self.make_file()
        result = self.service.convert(self.make_request(source))
        self.assertTrue(result.output_path.is_file())
        self.assertEqual("# converted\ncontent\n", result.output_path.read_text(encoding="utf-8"))

    def test_rejects_when_convert_result_is_file(self):
        source = self.make_file()
        (self.launch_dir / "convert_result").write_text("blocked", encoding="utf-8")
        self.assert_conversion_error(ErrorCode.OUTPUT_UNWRITABLE, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_rejects_when_convert_result_is_symlink(self):
        source = self.make_file()
        target = self.root / "elsewhere"
        target.mkdir()
        try:
            (self.launch_dir / "convert_result").symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symlinks unavailable: {error}")
        self.assert_conversion_error(ErrorCode.OUTPUT_UNWRITABLE, self.make_request(source))
        self.adapter.convert.assert_not_called()

    def test_rejects_existing_output_file_without_overwrite(self):
        source = self.make_file()
        out_dir = self.launch_dir / "convert_result"
        out_dir.mkdir()
        output = out_dir / "sample.md"
        output.write_text("keep me", encoding="utf-8")
        self.assert_conversion_error(ErrorCode.OUTPUT_CONFLICT, self.make_request(source))
        self.assertEqual("keep me", output.read_text(encoding="utf-8"))
        self.adapter.convert.assert_not_called()

    def test_rejects_existing_output_directory(self):
        source = self.make_file()
        output = self.launch_dir / "convert_result" / "sample.md"
        output.mkdir(parents=True)
        self.assert_conversion_error(ErrorCode.OUTPUT_CONFLICT, self.make_request(source))
        self.assertTrue(output.is_dir())
        self.adapter.convert.assert_not_called()

    def test_rejects_existing_output_symlink(self):
        source = self.make_file()
        out_dir = self.launch_dir / "convert_result"
        out_dir.mkdir()
        target = self.root / "target.md"
        target.write_text("target", encoding="utf-8")
        link = out_dir / "sample.md"
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest(f"Symlinks unavailable: {error}")
        self.assert_conversion_error(ErrorCode.OUTPUT_CONFLICT, self.make_request(source))
        self.assertEqual("target", target.read_text(encoding="utf-8"))
        self.adapter.convert.assert_not_called()

    def test_rejects_existing_broken_output_symlink(self):
        source = self.make_file()
        out_dir = self.launch_dir / "convert_result"
        out_dir.mkdir()
        link = out_dir / "sample.md"
        try:
            link.symlink_to(self.root / "missing-target.md")
        except OSError as error:
            self.skipTest(f"Symlinks unavailable: {error}")
        self.assert_conversion_error(ErrorCode.OUTPUT_CONFLICT, self.make_request(source))
        self.assertTrue(link.is_symlink())
        self.adapter.convert.assert_not_called()

    def test_rejects_empty_adapter_result_without_file(self):
        source = self.make_file()
        self.adapter.convert.return_value = " \r\n\t"
        self.assert_conversion_error(ErrorCode.EMPTY_RESULT, self.make_request(source))
        self.assert_no_output()

    def test_sanitizes_adapter_exception_message(self):
        source = self.make_file()
        self.adapter.convert.side_effect = RuntimeError("secret path /tmp/private.docx")
        error = self.assert_conversion_error(ErrorCode.CONVERSION_FAILED, self.make_request(source))
        self.assert_no_output()
        self.assertNotIn("secret path", str(error))
        self.assertNotIn("/tmp/private.docx", str(error))

    def test_writes_utf8_lf_without_bom(self):
        source = self.make_file()
        self.adapter.convert.return_value = "제목\r\nline\rfinal"
        result = self.service.convert(self.make_request(source))
        self.assertEqual(b"\xec\xa0\x9c\xeb\xaa\xa9\nline\nfinal", result.output_path.read_bytes())

    def test_returns_empty_warning_tuple_on_success(self):
        source = self.make_file()
        result = self.service.convert(self.make_request(source))
        self.assertEqual((), result.warnings)

    def test_exclusive_create_handles_race_without_overwrite(self):
        source = self.make_file()
        out_dir = self.launch_dir / "convert_result"
        original_open = Path.open

        def racing_open(path_self, *args, **kwargs):
            if path_self == out_dir / "sample.md" and args and args[0] == "x":
                path_self.write_text("raced", encoding="utf-8")
            return original_open(path_self, *args, **kwargs)

        with patch.object(Path, "open", racing_open):
            self.assert_conversion_error(ErrorCode.OUTPUT_CONFLICT, self.make_request(source))
        self.assertEqual("raced", (out_dir / "sample.md").read_text(encoding="utf-8"))

    def test_open_permission_error_is_output_unwritable(self):
        source = self.make_file()
        original_open = Path.open

        def blocked_open(path_self, *args, **kwargs):
            if path_self.name == "sample.md" and args and args[0] == "x":
                raise PermissionError("blocked")
            return original_open(path_self, *args, **kwargs)

        with patch.object(Path, "open", blocked_open):
            self.assert_conversion_error(ErrorCode.OUTPUT_UNWRITABLE, self.make_request(source))
        self.assert_no_output()

    def test_write_failure_removes_partial_output(self):
        source = self.make_file()
        original_open = Path.open

        class FailingWriter:
            def __init__(self, path):
                self.path = path
                self.file = original_open(path, "x", encoding="utf-8", newline="\n")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.file.close()

            def fileno(self):
                return self.file.fileno()

            def write(self, value):
                self.file.write("partial")
                raise OSError("disk full")

        def failing_open(path_self, *args, **kwargs):
            if path_self.name == "sample.md" and args and args[0] == "x":
                return FailingWriter(path_self)
            return original_open(path_self, *args, **kwargs)

        with patch.object(Path, "open", failing_open):
            self.assert_conversion_error(ErrorCode.WRITE_FAILED, self.make_request(source))
        self.assert_no_output()

    def test_close_failure_removes_partial_output(self):
        source = self.make_file()
        original_open = Path.open

        class CloseFailingWriter:
            def __init__(self, path):
                self.path = path
                self.file = original_open(path, "x", encoding="utf-8", newline="\n")

            def __enter__(self):
                return self.file

            def __exit__(self, exc_type, exc, tb):
                self.file.close()
                raise OSError("close failed")

        def failing_open(path_self, *args, **kwargs):
            if path_self.name == "sample.md" and args and args[0] == "x":
                return CloseFailingWriter(path_self)
            return original_open(path_self, *args, **kwargs)

        with patch.object(Path, "open", failing_open):
            self.assert_conversion_error(ErrorCode.WRITE_FAILED, self.make_request(source))
        self.assert_no_output()

    def test_cleanup_failure_is_reported_as_warning(self):
        source = self.make_file()
        original_open = Path.open
        original_unlink = Path.unlink
        cleanup_attempts = []

        class FailingWriter:
            def __init__(self, path):
                self.file = original_open(path, "x", encoding="utf-8", newline="\n")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.file.close()

            def fileno(self):
                return self.file.fileno()

            def write(self, value):
                self.file.write("partial")
                raise OSError("disk full")

        def failing_open(path_self, *args, **kwargs):
            if path_self.name == "sample.md" and args and args[0] == "x":
                return FailingWriter(path_self)
            return original_open(path_self, *args, **kwargs)

        def failing_unlink(path_self, *args, **kwargs):
            if path_self.name == "sample.md":
                cleanup_attempts.append(path_self)
                raise OSError("cleanup blocked")
            return original_unlink(path_self, *args, **kwargs)

        with patch.object(Path, "open", failing_open), patch.object(Path, "unlink", failing_unlink):
            error = self.assert_conversion_error(ErrorCode.WRITE_FAILED, self.make_request(source))
        self.assertTrue((self.launch_dir / "convert_result" / "sample.md").exists())
        self.assertEqual([self.launch_dir / "convert_result" / "sample.md"], cleanup_attempts)
        self.assertEqual("partial", cleanup_attempts[0].read_text(encoding="utf-8"))
        self.assertTrue(error.warnings)

    def test_conversion_error_carries_path_and_fixed_korean_message(self):
        error = ConversionError(ErrorCode.NOT_FOUND, path=self.input_dir / "missing.txt")
        self.assertEqual(ErrorCode.NOT_FOUND, error.code)
        self.assertEqual(self.input_dir / "missing.txt", error.path)
        self.assertIsInstance(str(error), str)
        self.assertRegex(str(error), r"[가-힣]")
        self.assertNotIn(str(self.input_dir), str(error))


if __name__ == "__main__":
    unittest.main()
