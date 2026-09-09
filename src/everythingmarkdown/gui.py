"""Tkinter GUI entry point. A thin single window over the shared ConversionService.

The window logic lives in ConversionController, which never imports tkinter, so the
state machine (idle/ready/running, close-while-busy, worker->queue handoff) is tested
headless. _TkView is the only Tk-aware part.
"""

import queue
import sys
import threading
from collections.abc import Callable
from importlib.resources import as_file, files
from pathlib import Path
from typing import Protocol

from .models import ConversionError, ConversionRequest, ConversionResult, ErrorCode
from .service import ConversionService, output_path_for

TITLE = "EverythingMarkdown"
SUBTITLE = "로컬 파일을 Markdown으로 변환합니다. 기존 결과는 덮어쓰지 않습니다."
FORMATS = "지원 형식  PDF · DOCX · PPTX · XLSX · HTML · CSV · TXT"
STATUS_IDLE = "변환할 파일을 선택해 주세요."
STATUS_READY = "변환할 준비가 되었습니다."
STATUS_RUNNING = "변환 중입니다…"
STATUS_CLOSING = "변환이 끝나면 창을 닫습니다."
CONFLICT_HINT = "이미 같은 이름의 결과가 있습니다. 변환 시 기존 결과를 보존하고 실패합니다."
UNWRITABLE_HINT = "쓰기 가능한 폴더에서 실행해 주세요."
NO_TK = "GUI 실행에는 Tcl/Tk와 그래픽 디스플레이가 필요합니다."
NO_CWD = "현재 작업 디렉터리를 확인할 수 없습니다."

_SYMBOLS = {"info": "●", "ready": "✓", "running": "⏳", "warn": "⚠", "success": "✓", "error": "⚠"}


class View(Protocol):
    def set_file_text(self, text: str) -> None: ...
    def set_output_text(self, text: str) -> None: ...
    def set_status(self, text: str, kind: str) -> None: ...
    def set_convert_enabled(self, enabled: bool) -> None: ...
    def set_inputs_enabled(self, enabled: bool) -> None: ...
    def set_progress_running(self, running: bool) -> None: ...
    def destroy(self) -> None: ...


def _spawn_daemon(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True).start()


def _exists_any(path: Path) -> bool:
    try:
        path.lstat()  # dangling symlinks count as a conflict, like the service.
    except (OSError, ValueError):
        return False
    return True


class ConversionController:
    def __init__(
        self,
        launch_dir: Path,
        view: View,
        *,
        service: ConversionService | None = None,
        run_async: Callable[[Callable[[], None]], None] = _spawn_daemon,
    ) -> None:
        self._launch_dir = launch_dir
        self._view = view
        self._service = service if service is not None else ConversionService()
        self._run_async = run_async
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._selected: Path | None = None
        self._running = False
        self._close_when_done = False
        self._render_idle()

    @property
    def running(self) -> bool:
        return self._running

    def _render_idle(self) -> None:
        self._view.set_output_text(str(self._launch_dir / "convert_result"))
        self._view.set_status(STATUS_IDLE, "info")
        self._view.set_convert_enabled(False)
        self._view.set_inputs_enabled(True)
        self._view.set_progress_running(False)

    def _render_ready(self) -> None:
        assert self._selected is not None
        output = output_path_for(self._launch_dir, self._selected)
        self._view.set_file_text(str(self._selected))
        self._view.set_output_text(str(output))
        if _exists_any(output):
            self._view.set_status(CONFLICT_HINT, "warn")
        else:
            self._view.set_status(STATUS_READY, "ready")
        self._view.set_convert_enabled(True)
        self._view.set_inputs_enabled(True)
        self._view.set_progress_running(False)

    def select_file(self, path: str | None) -> None:
        if self._running or not path:  # empty string == dialog cancelled: keep prior choice.
            return
        self._selected = Path(path)
        self._render_ready()

    def reset(self) -> None:
        if self._running:
            return
        self._selected = None
        self._view.set_file_text("")
        self._render_idle()

    def convert(self) -> bool:
        """Start a conversion. Returns False if it was a no-op (busy or nothing selected)."""
        if self._running or self._selected is None:
            return False
        request = ConversionRequest(input_path=self._selected, launch_dir=self._launch_dir)
        self._running = True
        self._view.set_status(STATUS_RUNNING, "running")
        self._view.set_convert_enabled(False)
        self._view.set_inputs_enabled(False)
        self._view.set_progress_running(True)
        result_queue = self._queue
        service = self._service

        def work() -> None:
            try:
                result = service.convert(request)
            except ConversionError as error:
                result_queue.put(("error", error))
            except Exception:
                result_queue.put(("error", None))
            else:
                result_queue.put(("ok", result))

        self._run_async(work)
        return True

    def poll(self) -> bool:
        """Drain one worker result on the main thread. Returns whether work is still running."""
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            return self._running
        self._running = False
        self._view.set_progress_running(False)
        if kind == "ok" and isinstance(payload, ConversionResult):
            self._show_success(payload)
        else:
            self._show_error(payload if isinstance(payload, ConversionError) else None)
        self._view.set_inputs_enabled(True)
        self._view.set_convert_enabled(self._selected is not None)
        if self._close_when_done:
            self._view.destroy()
        return False

    def request_close(self) -> bool:
        """Return True if the window may close now; False if the close is deferred."""
        if not self._running:
            return True
        self._close_when_done = True
        self._view.set_status(STATUS_CLOSING, "info")
        return False

    def _show_success(self, result: ConversionResult) -> None:
        lines = [f"변환 완료 · {result.output_path}"]
        lines += [f"경고: {warning}" for warning in result.warnings]
        self._view.set_status("\n".join(lines), "success")

    def _show_error(self, error: ConversionError | None) -> None:
        if error is None:
            code = ErrorCode.CONVERSION_FAILED
            self._view.set_status(f"{ConversionError(code)} (코드: {code})", "error")
            return
        lines = [f"{error} (코드: {error.code})"]
        if error.code == ErrorCode.OUTPUT_UNWRITABLE:
            lines.append(UNWRITABLE_HINT)
        if error.path is not None:
            lines.append(f"경로: {error.path}")
        lines += [f"경고: {warning}" for warning in error.warnings]
        self._view.set_status("\n".join(lines), "error")


class _TkView:
    """The only Tk-aware class. Bind a controller with attach() before mainloop()."""

    def __init__(self, root, modules) -> None:
        tk, ttk, filedialog = modules
        self._root = root
        self._filedialog = filedialog
        self._controller: ConversionController | None = None

        root.title(TITLE)
        root.minsize(460, 360)
        root.columnconfigure(0, weight=1)
        _apply_icon(root, tk)

        pad = {"padx": 16}
        ttk.Label(root, text=TITLE, font=("TkDefaultFont", 15, "bold")).grid(
            row=0, column=0, sticky="w", pady=(16, 0), **pad
        )
        ttk.Label(root, text=SUBTITLE, foreground="#555").grid(row=1, column=0, sticky="w", **pad)

        ttk.Label(root, text="파일").grid(row=2, column=0, sticky="w", pady=(14, 2), **pad)
        file_row = ttk.Frame(root)
        file_row.grid(row=3, column=0, sticky="ew", **pad)
        file_row.columnconfigure(0, weight=1)
        self._file_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self._file_var, state="readonly").grid(row=0, column=0, sticky="ew")
        self._browse = ttk.Button(file_row, text="찾아보기", command=self._on_browse)
        self._browse.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(root, text="저장 위치").grid(row=4, column=0, sticky="w", pady=(12, 2), **pad)
        out_row = ttk.Frame(root)
        out_row.grid(row=5, column=0, sticky="ew", **pad)
        out_row.columnconfigure(0, weight=1)
        self._out_var = tk.StringVar()
        ttk.Entry(out_row, textvariable=self._out_var, state="readonly").grid(row=0, column=0, sticky="ew")
        self._copy = ttk.Button(out_row, text="복사", command=self._on_copy)
        self._copy.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(root, text="상태").grid(row=6, column=0, sticky="w", pady=(12, 2), **pad)
        self._status_var = tk.StringVar()
        self._status = ttk.Label(root, textvariable=self._status_var, justify="left", wraplength=420)
        self._status.grid(row=7, column=0, sticky="w", **pad)

        ttk.Label(root, text=FORMATS, foreground="#777").grid(
            row=8, column=0, sticky="w", pady=(12, 0), **pad
        )

        self._progress = ttk.Progressbar(root, mode="indeterminate")
        self._progress.grid(row=9, column=0, sticky="ew", pady=(10, 0), **pad)
        self._progress.grid_remove()

        action_row = ttk.Frame(root)
        action_row.grid(row=10, column=0, sticky="ew", pady=16, **pad)
        action_row.columnconfigure(0, weight=1)
        self._convert = ttk.Button(action_row, text="변환", command=self._on_convert)
        self._convert.grid(row=0, column=0, sticky="ew")
        self._reset = ttk.Button(action_row, text="초기화", command=self._on_reset)
        self._reset.grid(row=0, column=1, padx=(8, 0))

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def attach(self, controller: ConversionController) -> None:
        self._controller = controller

    # View protocol -------------------------------------------------
    def set_file_text(self, text: str) -> None:
        self._file_var.set(text)

    def set_output_text(self, text: str) -> None:
        self._out_var.set(text)

    def set_status(self, text: str, kind: str) -> None:
        colors = {"warn": "#8a6d00", "success": "#1a7f37", "error": "#b3261e"}
        self._status_var.set(f"{_SYMBOLS.get(kind, '●')} {text}")
        self._status.configure(foreground=colors.get(kind, "#222"))

    def set_convert_enabled(self, enabled: bool) -> None:
        self._convert.configure(state="normal" if enabled else "disabled")

    def set_inputs_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in (self._browse, self._reset, self._copy):
            widget.configure(state=state)

    def set_progress_running(self, running: bool) -> None:
        if running:
            self._progress.grid()
            self._progress.start(12)
        else:
            self._progress.stop()
            self._progress.grid_remove()

    def destroy(self) -> None:
        self._root.destroy()

    # Tk callbacks -------------------------------------------------
    def _on_browse(self) -> None:
        assert self._controller is not None
        path = self._filedialog.askopenfilename(
            title="변환할 파일 선택",
            filetypes=[
                ("지원 형식", "*.pdf *.docx *.pptx *.xlsx *.html *.csv *.txt"),
                ("모든 파일", "*.*"),
            ],
        )
        self._controller.select_file(path or None)

    def _on_copy(self) -> None:
        self._root.clipboard_clear()
        self._root.clipboard_append(self._out_var.get())

    def _on_convert(self) -> None:
        assert self._controller is not None
        if self._controller.convert():
            self._tick()

    def _on_reset(self) -> None:
        assert self._controller is not None
        self._controller.reset()

    def _on_close(self) -> None:
        assert self._controller is not None
        if self._controller.request_close():
            self._root.destroy()

    def _tick(self) -> None:
        assert self._controller is not None
        if self._controller.poll():
            self._root.after(100, self._tick)

    def run(self) -> None:
        self._root.mainloop()


def _apply_icon(root, tk) -> None:
    try:
        with as_file(files("everythingmarkdown").joinpath("logo.png")) as path:
            image = tk.PhotoImage(file=str(path))
        root._em_icon = image  # keep a reference or Tk drops the icon.
        root.iconphoto(True, image)
    except Exception:
        pass


def main() -> int:
    try:
        launch_dir = Path.cwd()  # Capture once at startup; never recompute.
    except OSError:
        print(NO_CWD, file=sys.stderr)
        return 3
    try:
        import tkinter as tk
        from tkinter import filedialog, ttk
    except ImportError:
        print(NO_TK, file=sys.stderr)
        return 3
    try:
        root = tk.Tk()
    except tk.TclError:
        print(NO_TK, file=sys.stderr)
        return 3
    view = _TkView(root, (tk, ttk, filedialog))
    view.attach(ConversionController(launch_dir, view))
    view.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
