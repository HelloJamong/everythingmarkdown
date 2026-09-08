import contextlib
import io
import unittest
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

from everythingmarkdown import ConversionError, ConversionResult, ErrorCode
from everythingmarkdown import cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.launch = Path.cwd()
        self.output = self.launch / "convert_result" / "한글 report.md"
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))
        self.factory = self.enterContext(patch.object(cli, "ConversionService"))
        self.factory.return_value.convert.return_value = ConversionResult(self.output)

    def test_file_argument_uses_shared_service_and_outputs_only_path(self):
        with patch.object(Path, "cwd", return_value=self.launch) as cwd:
            self.assertEqual(0, cli.main(["한글 report.txt"]))
        cwd.assert_called_once_with()
        request = self.factory.return_value.convert.call_args.args[0]
        self.assertEqual(Path("한글 report.txt"), request.input_path)
        self.assertEqual(self.launch, request.launch_dir)
        self.assertEqual(str(self.output) + "\n", self.stdout.getvalue())
        self.assertEqual("", self.stderr.getvalue())

    def test_file_argument_never_reads_stdin(self):
        with patch("builtins.input") as read, patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(0, cli.main(["file.txt"]))
        read.assert_not_called()

    def test_interactive_input_strips_outer_matching_quotes_only(self):
        for value, expected in [
            ('  "한글 report.txt"  ', "한글 report.txt"),
            ("' leading space.txt'", " leading space.txt"),
            ("'unmatched.txt", "'unmatched.txt"),
        ]:
            with self.subTest(value=value), patch("sys.stdin.isatty", return_value=True), \
                 patch("builtins.input", return_value=value):
                self.assertEqual(0, cli.main([]))
            request = self.factory.return_value.convert.call_args.args[0]
            self.assertEqual(Path(expected), request.input_path)
        self.assertIn("변환할 파일 경로:", self.stderr.getvalue())
        self.assertNotIn("변환할 파일 경로:", self.stdout.getvalue())

    def test_cwd_is_captured_before_prompt_and_only_once(self):
        events = []

        def cwd():
            events.append("cwd")
            return self.launch

        def read():
            events.append("input")
            return "relative.txt"

        with patch.object(Path, "cwd", side_effect=cwd), \
             patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=read):
            self.assertEqual(0, cli.main([]))
        self.assertEqual(["cwd", "input"], events)

    def test_non_tty_without_argument_is_immediate_usage_error(self):
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.input") as read, \
             self.assertRaises(SystemExit) as error:
            cli.main([])
        self.assertEqual(2, error.exception.code)
        read.assert_not_called()
        self.factory.assert_not_called()
        self.assertEqual("", self.stdout.getvalue())

    def test_empty_interactive_paths_are_usage_errors(self):
        for value in ("", "  ", '""', "''", '"  "'):
            with self.subTest(value=value), patch("sys.stdin.isatty", return_value=True), \
                 patch("builtins.input", return_value=value), self.assertRaises(SystemExit) as error:
                cli.main([])
            self.assertEqual(2, error.exception.code)
        self.factory.assert_not_called()

    def test_empty_argument_is_usage_error(self):
        with self.assertRaises(SystemExit) as error:
            cli.main([""])
        self.assertEqual(2, error.exception.code)
        self.factory.assert_not_called()

    def test_argument_quotes_are_left_to_the_shell(self):
        self.assertEqual(0, cli.main(['"file.txt"']))
        self.assertEqual(Path('"file.txt"'), self.factory.return_value.convert.call_args.args[0].input_path)

    def test_double_dash_accepts_dash_prefixed_filename(self):
        self.assertEqual(0, cli.main(["--", "-file.txt"]))
        self.assertEqual(Path("-file.txt"), self.factory.return_value.convert.call_args.args[0].input_path)

    def test_unknown_options_and_extra_files_are_usage_errors(self):
        for args in (["--unknown"], ["one.txt", "two.txt"]):
            with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                cli.main(args)
            self.assertEqual(2, error.exception.code)
        self.factory.assert_not_called()

    def test_help_does_not_read_input_or_call_service(self):
        with patch("builtins.input") as read, self.assertRaises(SystemExit) as error:
            cli.main(["--help"])
        self.assertEqual(0, error.exception.code)
        self.assertIn("convert_result", self.stdout.getvalue())
        self.assertEqual("", self.stderr.getvalue())
        read.assert_not_called()
        self.factory.assert_not_called()

    def test_version_does_not_advertise_an_unreleased_number(self):
        with patch.object(cli, "version", return_value="0.0.0"), self.assertRaises(SystemExit) as error:
            cli.main(["--version"])
        self.assertEqual(0, error.exception.code)
        self.assertIn("정식 릴리즈 없음", self.stdout.getvalue())
        self.assertNotIn("0.0.0", self.stdout.getvalue())
        self.assertNotIn("26.1.0", self.stdout.getvalue())
        self.factory.assert_not_called()

    def test_version_uses_installed_metadata_after_release(self):
        with patch.object(cli, "version", return_value="26.1.0"):
            self.assertEqual("EverythingMarkdown 26.1.0", cli._version_label())

    def test_version_without_metadata_is_development_label(self):
        with patch.object(cli, "version", side_effect=PackageNotFoundError):
            self.assertIn("정식 릴리즈 없음", cli._version_label())

    def test_interactive_eof_and_ctrl_c_are_cancelled(self):
        for signal in (EOFError, KeyboardInterrupt):
            with self.subTest(signal=signal), patch("sys.stdin.isatty", return_value=True), \
                 patch("builtins.input", side_effect=signal):
                self.assertEqual(130, cli.main([]))
        self.assertEqual("", self.stdout.getvalue())
        self.assertIn("CANCELLED", self.stderr.getvalue())
        self.factory.assert_not_called()

    def test_ctrl_c_during_conversion_is_cancelled(self):
        self.factory.return_value.convert.side_effect = KeyboardInterrupt
        self.assertEqual(130, cli.main(["file.txt"]))
        self.assertEqual("", self.stdout.getvalue())

    def test_all_service_error_exit_codes_propagate(self):
        for code in ErrorCode:
            with self.subTest(code=code):
                error = ConversionError(code, path=Path("file.txt"))
                self.factory.return_value.convert.side_effect = error
                self.assertEqual(error.exit_code, cli.main(["file.txt"]))
                self.assertIn(code.value, self.stderr.getvalue())
        self.assertEqual("", self.stdout.getvalue())

    def test_cleanup_warning_and_path_are_reported_on_stderr(self):
        self.factory.return_value.convert.side_effect = ConversionError(
            ErrorCode.WRITE_FAILED, path=self.output, warnings=("미완성 결과 정리 실패",)
        )
        self.assertEqual(4, cli.main(["file.txt"]))
        self.assertIn(str(self.output), self.stderr.getvalue())
        self.assertIn("미완성 결과 정리 실패", self.stderr.getvalue())
        self.assertEqual("", self.stdout.getvalue())

    def test_success_warnings_are_not_mixed_into_stdout(self):
        self.factory.return_value.convert.return_value = ConversionResult(self.output, ("확인 필요",))
        self.assertEqual(0, cli.main(["file.txt"]))
        self.assertEqual(str(self.output) + "\n", self.stdout.getvalue())
        self.assertIn("확인 필요", self.stderr.getvalue())

    def test_unexpected_error_does_not_leak_traceback_or_document(self):
        self.factory.return_value.convert.side_effect = RuntimeError("private document contents")
        self.assertEqual(3, cli.main(["file.txt"]))
        self.assertEqual("", self.stdout.getvalue())
        self.assertIn("CONVERSION_FAILED", self.stderr.getvalue())
        self.assertNotIn("private document", self.stderr.getvalue())
        self.assertNotIn("Traceback", self.stderr.getvalue())

    def test_unavailable_cwd_is_output_error(self):
        with patch.object(Path, "cwd", side_effect=OSError("private path")):
            self.assertEqual(4, cli.main(["file.txt"]))
        self.factory.assert_not_called()
        self.assertNotIn("private path", self.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
