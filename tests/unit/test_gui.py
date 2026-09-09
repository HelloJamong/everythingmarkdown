import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from everythingmarkdown.gui import (
    CONFLICT_HINT,
    NO_TK,
    STATUS_CLOSING,
    ConversionController,
    main,
)
from everythingmarkdown.models import ConversionError, ConversionResult, ErrorCode
from everythingmarkdown.service import output_path_for


class FakeView:
    def __init__(self):
        self.file_text = ""
        self.output_text = ""
        self.status = ("", "")
        self.convert_enabled = None
        self.inputs_enabled = None
        self.progress_running = None
        self.destroyed = False

    def set_file_text(self, text): self.file_text = text
    def set_output_text(self, text): self.output_text = text
    def set_status(self, text, kind): self.status = (text, kind)
    def set_convert_enabled(self, enabled): self.convert_enabled = enabled
    def set_inputs_enabled(self, enabled): self.inputs_enabled = enabled
    def set_progress_running(self, running): self.progress_running = running
    def destroy(self): self.destroyed = True


class ManualRunner:
    """Captures worker callables so the test decides when they run."""

    def __init__(self):
        self.jobs = []

    def __call__(self, work):
        self.jobs.append(work)

    def run_all(self):
        while self.jobs:
            self.jobs.pop(0)()


class FakeService:
    def __init__(self, *, result=None, error=None):
        self._result = result
        self._error = error
        self.calls = 0

    def convert(self, request):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result or ConversionResult(output_path=request.launch_dir / "convert_result" / "x.md")


class GuiControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.launch = Path(self.tmp.name)
        self.view = FakeView()
        self.runner = ManualRunner()

    def make(self, service=None):
        return ConversionController(
            self.launch, self.view,
            service=service or FakeService(), run_async=self.runner,
        )

    def source(self, name="report.v2.docx"):
        path = self.launch / name
        path.write_bytes(b"data")
        return path

    def test_starts_idle_with_convert_disabled(self):
        self.make()
        self.assertFalse(self.view.convert_enabled)
        self.assertEqual("info", self.view.status[1])
        self.assertEqual(str(self.launch / "convert_result"), self.view.output_text)

    def test_select_file_moves_to_ready_and_previews_output(self):
        controller = self.make()
        source = self.source()
        controller.select_file(str(source))
        self.assertTrue(self.view.convert_enabled)
        self.assertEqual("ready", self.view.status[1])
        self.assertEqual(str(output_path_for(self.launch, source)), self.view.output_text)
        self.assertEqual(str(self.launch / "convert_result" / "report.v2.md"), self.view.output_text)

    def test_cancelled_dialog_keeps_previous_selection(self):
        controller = self.make()
        source = self.source()
        controller.select_file(str(source))
        controller.select_file("")
        controller.select_file(None)
        self.assertEqual(str(source), self.view.file_text)
        self.assertTrue(self.view.convert_enabled)

    def test_existing_output_shows_conflict_hint_but_stays_convertible(self):
        (self.launch / "convert_result").mkdir()
        (self.launch / "convert_result" / "report.v2.md").write_text("keep", encoding="utf-8")
        controller = self.make()
        controller.select_file(str(self.source()))
        self.assertEqual(CONFLICT_HINT, self.view.status[0])
        self.assertEqual("warn", self.view.status[1])
        self.assertTrue(self.view.convert_enabled)

    def test_convert_runs_single_worker_and_reports_success(self):
        result = ConversionResult(output_path=self.launch / "convert_result" / "report.v2.md")
        service = FakeService(result=result)
        controller = self.make(service)
        controller.select_file(str(self.source()))
        controller.convert()
        self.assertTrue(controller.running)
        self.assertFalse(self.view.inputs_enabled)
        self.assertTrue(self.view.progress_running)
        controller.convert()  # ignored while running
        self.assertEqual(1, len(self.runner.jobs))  # only one worker despite two clicks
        self.runner.run_all()
        self.assertFalse(controller.poll())
        self.assertEqual("success", self.view.status[1])
        self.assertIn("report.v2.md", self.view.status[0])
        self.assertFalse(controller.running)
        self.assertFalse(self.view.progress_running)
        self.assertTrue(self.view.inputs_enabled)

    def test_conversion_error_surfaces_code_and_keeps_selection(self):
        service = FakeService(error=ConversionError(ErrorCode.OUTPUT_CONFLICT))
        controller = self.make(service)
        controller.select_file(str(self.source()))
        controller.convert()
        self.runner.run_all()
        controller.poll()
        self.assertEqual("error", self.view.status[1])
        self.assertIn("OUTPUT_CONFLICT", self.view.status[0])
        self.assertTrue(self.view.convert_enabled)

    def test_unexpected_worker_exception_maps_to_safe_message(self):
        service = FakeService(error=RuntimeError("secret /tmp/private.docx"))
        controller = self.make(service)
        controller.select_file(str(self.source()))
        controller.convert()
        self.runner.run_all()
        controller.poll()
        self.assertEqual("error", self.view.status[1])
        self.assertIn("CONVERSION_FAILED", self.view.status[0])
        self.assertNotIn("secret", self.view.status[0])
        self.assertNotIn("private.docx", self.view.status[0])

    def test_every_error_code_maps_to_safe_error_status(self):
        for code in ErrorCode:
            with self.subTest(code=code):
                self.view = FakeView()
                self.runner = ManualRunner()
                controller = self.make(FakeService(error=ConversionError(code, path=Path("/x/secret.docx"))))
                controller.select_file(str(self.source()))
                controller.convert()
                self.runner.run_all()
                controller.poll()
                self.assertEqual("error", self.view.status[1])
                self.assertIn(str(code), self.view.status[0])
                self.assertNotIn("Traceback", self.view.status[0])

    def test_unwritable_error_appends_hint(self):
        service = FakeService(error=ConversionError(ErrorCode.OUTPUT_UNWRITABLE))
        controller = self.make(service)
        controller.select_file(str(self.source()))
        controller.convert()
        self.runner.run_all()
        controller.poll()
        self.assertIn("쓰기 가능한 폴더", self.view.status[0])

    def test_warnings_are_shown_on_success(self):
        result = ConversionResult(
            output_path=self.launch / "convert_result" / "report.v2.md",
            warnings=("정리 실패 경고",),
        )
        controller = self.make(FakeService(result=result))
        controller.select_file(str(self.source()))
        controller.convert()
        self.runner.run_all()
        controller.poll()
        self.assertIn("정리 실패 경고", self.view.status[0])

    def test_close_while_idle_allows_immediate_exit(self):
        controller = self.make()
        self.assertTrue(controller.request_close())

    def test_close_while_running_defers_until_result(self):
        controller = self.make()
        controller.select_file(str(self.source()))
        controller.convert()
        self.assertFalse(controller.request_close())
        self.assertEqual(STATUS_CLOSING, self.view.status[0])
        self.assertFalse(self.view.destroyed)
        self.runner.run_all()
        controller.poll()
        self.assertTrue(self.view.destroyed)

    def test_reset_returns_to_idle(self):
        controller = self.make()
        controller.select_file(str(self.source()))
        controller.reset()
        self.assertEqual("", self.view.file_text)
        self.assertFalse(self.view.convert_enabled)
        self.assertEqual("info", self.view.status[1])

    def test_main_returns_three_without_tkinter(self):
        captured = []
        with patch.dict(sys.modules, {"tkinter": None}), \
             patch("sys.stderr"), \
             patch("builtins.print", lambda *a, **k: captured.append(a)):
            self.assertEqual(3, main())
        self.assertIn(NO_TK, [a[0] for a in captured if a])

    def test_main_returns_three_without_a_display(self):
        import tkinter

        captured = []
        with patch("tkinter.Tk", side_effect=tkinter.TclError("no display name")), \
             patch("sys.stderr"), \
             patch("builtins.print", lambda *a, **k: captured.append(a)):
            self.assertEqual(3, main())
        self.assertIn(NO_TK, [a[0] for a in captured if a])

    def test_worker_only_touches_queue_not_view(self):
        service = FakeService()
        controller = self.make(service)
        controller.select_file(str(self.source()))
        controller.convert()
        # Worker captured but not run: the view must not have progressed past "running".
        before = self.view.status
        self.runner.run_all()  # worker runs; still no view change until poll()
        self.assertEqual(before, self.view.status)
        self.assertEqual(1, service.calls)


if __name__ == "__main__":
    unittest.main()
