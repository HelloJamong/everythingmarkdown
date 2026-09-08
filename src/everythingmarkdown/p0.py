"""Bounded feasibility probe. No production output writer or GUI conversion yet."""

import argparse
import json
import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from zipfile import ZipFile, is_zipfile

from markitdown import MarkItDown
from markitdown.converters import (
    CsvConverter,
    DocxConverter,
    HtmlConverter,
    PdfConverter,
    PlainTextConverter,
    PptxConverter,
    XlsxConverter,
)

CONVERTERS = {
    ".pdf": PdfConverter,
    ".docx": DocxConverter,
    ".pptx": PptxConverter,
    ".xlsx": XlsxConverter,
    ".html": HtmlConverter,
    ".csv": CsvConverter,
    ".txt": PlainTextConverter,
}
OOXML_PARTS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}
MAX_BYTES = 100 * 1024 * 1024
FIXTURE_MARKER = "EverythingMarkdown P0 sample"


def convert_sample(path: Path) -> str:
    """Convert one trusted sample using exactly one explicitly selected converter."""
    extension = path.suffix.lower()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular local file, not a symbolic link")
    if extension not in CONVERTERS:
        raise ValueError("Unsupported sample format")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Sample exceeds the proposed 100 MiB limit")
    zipped = is_zipfile(path)
    if extension in OOXML_PARTS:
        if not zipped:
            raise ValueError("Expected an OOXML container")
        with ZipFile(path) as archive:
            if not {"[Content_Types].xml", OOXML_PARTS[extension]} <= set(archive.namelist()):
                raise ValueError("Missing required OOXML parts")
    elif zipped:
        raise ValueError("ZIP disguised as a supported sample is not allowed")
    engine = MarkItDown(enable_builtins=False, enable_plugins=False)
    engine.register_converter(CONVERTERS[extension]())
    markdown = engine.convert_local(str(path)).markdown
    if not markdown.strip():
        raise ValueError("Sample produced empty Markdown")
    return markdown


def environment() -> dict:
    cwd = Path.cwd()
    return {
        "phase": "P0 probe; no Markdown files are saved",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "markitdown": version("markitdown"),
        "frozen": bool(getattr(sys, "frozen", False)),
        "cwd": str(cwd),
        "proposed_output_directory": str(cwd / "convert_result"),
        "cwd_writable_hint": os.access(cwd, os.W_OK),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, help="trusted local sample")
    parser.add_argument("--fixtures", type=Path, help="check all seven sample.* fixtures")
    parser.add_argument("--environment", action="store_true", help="report environment only")
    args = parser.parse_args(argv)
    if sum((args.file is not None, args.fixtures is not None, args.environment)) > 1:
        parser.error("choose a file, --fixtures, or --environment")
    report = environment()
    if args.environment:
        print(json.dumps(report, ensure_ascii=True))
        return 0
    try:
        if args.file is None and args.fixtures is None:
            if not sys.stdin.isatty():
                parser.error("a file argument is required when stdin is not a terminal")
            print("Sample file path: ", end="", file=sys.stderr, flush=True)
            raw = input().strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                raw = raw[1:-1]
            if not raw:
                parser.error("sample path must not be empty")
            args.file = Path(raw)
        paths = (
            [args.fixtures / f"sample{ext}" for ext in CONVERTERS]
            if args.fixtures is not None else [args.file]
        )
        results = []
        for path in paths:
            markdown = convert_sample(path)
            if args.fixtures is not None and FIXTURE_MARKER not in markdown:
                raise ValueError("Fixture marker missing from conversion")
            results.append({"format": path.suffix.lower(), "characters": len(markdown)})
        report["results"] = results
        print(json.dumps(report, ensure_ascii=True))
        return 0
    except (KeyboardInterrupt, EOFError):
        print("P0 probe cancelled", file=sys.stderr)
        return 130
    except Exception as error:
        # Parser errors may contain source document text: do not echo them.
        print(f"P0 probe failed ({type(error).__name__}); check the sample and dependencies", file=sys.stderr)
        return 3


def gui_main() -> int:
    import tkinter as tk
    from tkinter import ttk

    try:
        root = tk.Tk()
    except tk.TclError:
        print("P0 GUI requires working Tcl/Tk and a graphical display", file=sys.stderr)
        return 3
    root.title("EverythingMarkdown — P0 environment probe")
    report = environment()
    report["tcl"] = root.tk.call("info", "patchlevel")
    report["tk"] = root.tk.call("package", "require", "Tk")
    ttk.Label(root, text="P0 startup probe — conversion GUI is not implemented").pack(padx=16, pady=12)
    details = tk.Text(root, width=88, height=18, wrap="word")
    details.insert("1.0", json.dumps(report, ensure_ascii=False, indent=2))
    details.configure(state="disabled")
    details.pack(padx=16, pady=8, fill="both", expand=True)
    ttk.Button(root, text="Close", command=root.destroy).pack(pady=12)
    root.mainloop()
    return 0
