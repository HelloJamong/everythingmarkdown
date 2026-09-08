"""Single conversion and output policy shared by future GUI/CLI entry points.

This is a local single-user tool, not a hostile-filesystem or document sandbox.
Callers capture Path.cwd() once at process startup and pass it as launch_dir.
"""

import os
import re
import stat
from pathlib import Path
from typing import Protocol
from zipfile import BadZipFile, ZipFile, is_zipfile

from .markitdown_adapter import SUPPORTED_EXTENSIONS, MarkItDownAdapter
from .models import ConversionError, ConversionRequest, ConversionResult, ErrorCode

MAX_INPUT_BYTES = 100 * 1024 * 1024
_OOXML_PARTS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}


class Converter(Protocol):
    def convert(self, path: Path) -> str: ...


class ConversionService:
    def __init__(self, adapter: Converter | None = None) -> None:
        self._adapter = adapter if adapter is not None else MarkItDownAdapter()

    def convert(self, request: ConversionRequest) -> ConversionResult:
        launch_dir = request.launch_dir
        if not launch_dir.is_absolute():
            raise ConversionError(ErrorCode.INVALID_INPUT, path=launch_dir)
        # Do not resolve symlinks before validating the input's own directory entry.
        path = request.input_path
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", str(path)):
            raise ConversionError(ErrorCode.INVALID_INPUT, path=path)
        if not path.is_absolute():
            path = launch_dir / path
        _validate_input(path)
        output = launch_dir / "convert_result" / (path.stem + ".md")
        _prepare_output(output)
        try:
            markdown = self._adapter.convert(path)
        except ConversionError:
            raise
        except (KeyboardInterrupt, EOFError):
            raise ConversionError(ErrorCode.CANCELLED, path=path) from None
        except Exception:
            raise ConversionError(ErrorCode.CONVERSION_FAILED, path=path) from None
        if not isinstance(markdown, str):
            raise ConversionError(ErrorCode.CONVERSION_FAILED, path=path)
        if not markdown.strip():
            raise ConversionError(ErrorCode.EMPTY_RESULT, path=path)
        markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
        _write_output(output, markdown)
        return ConversionResult(output_path=output)


def _validate_input(path: Path) -> None:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ConversionError(ErrorCode.INVALID_INPUT, path=path)
        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ConversionError(ErrorCode.UNSUPPORTED_FORMAT, path=path)
        if info.st_size > MAX_INPUT_BYTES:
            raise ConversionError(ErrorCode.TOO_LARGE, path=path)
        # Open explicitly: is_zipfile(path) alone suppresses some read errors.
        with path.open("rb") as source:
            zipped = is_zipfile(source)
            if extension in _OOXML_PARTS:
                if not zipped:
                    raise ConversionError(ErrorCode.INVALID_INPUT, path=path)
                with ZipFile(source) as archive:
                    required = {"[Content_Types].xml", _OOXML_PARTS[extension]}
                    if not required.issubset(archive.namelist()):
                        raise ConversionError(ErrorCode.INVALID_INPUT, path=path)
            elif zipped:
                raise ConversionError(ErrorCode.INVALID_INPUT, path=path)
    except FileNotFoundError:
        raise ConversionError(ErrorCode.NOT_FOUND, path=path) from None
    except (OSError, ValueError, BadZipFile):
        raise ConversionError(ErrorCode.INVALID_INPUT, path=path) from None


def _prepare_output(output: Path) -> None:
    directory = output.parent
    try:
        if directory.is_symlink():
            raise ConversionError(ErrorCode.OUTPUT_UNWRITABLE, path=directory)
        directory.mkdir(exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ConversionError(ErrorCode.OUTPUT_UNWRITABLE, path=directory)
        try:
            output.lstat()  # Includes dangling symlinks; never follow/overwrite them.
        except FileNotFoundError:
            pass
        else:
            raise ConversionError(ErrorCode.OUTPUT_CONFLICT, path=output)
        if not os.access(directory, os.W_OK):
            raise ConversionError(ErrorCode.OUTPUT_UNWRITABLE, path=directory)
    except OSError:
        raise ConversionError(ErrorCode.OUTPUT_UNWRITABLE, path=directory) from None


def _cleanup_partial(output: Path, identity: os.stat_result | None) -> tuple[str, ...]:
    try:
        current = output.lstat()
    except FileNotFoundError:
        return ()
    except OSError:
        return ("미완성 결과를 정리하지 못했습니다. 결과 경로를 확인해 주세요.",)
    if identity is None or not os.path.samestat(identity, current):
        return ("결과 파일의 소유 여부를 확인할 수 없어 삭제하지 않았습니다.",)
    try:
        output.unlink()
    except OSError:
        return ("미완성 결과를 정리하지 못했습니다. 결과 경로를 확인해 주세요.",)
    return ()


def _write_output(output: Path, markdown: str) -> None:
    created = False
    identity = None
    try:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            created = True
            identity = os.fstat(stream.fileno())
            stream.write(markdown)
    except (Exception, KeyboardInterrupt) as error:
        # The close attempted by the context manager is part of successful saving.
        # Cleanup checks inode identity so a replaced file is not deleted.
        warnings = _cleanup_partial(output, identity) if created else ()
        if isinstance(error, KeyboardInterrupt):
            code = ErrorCode.CANCELLED
        elif created:
            code = ErrorCode.WRITE_FAILED
        elif isinstance(error, FileExistsError):
            code = ErrorCode.OUTPUT_CONFLICT
        else:
            code = ErrorCode.OUTPUT_UNWRITABLE
        raise ConversionError(code, path=output, warnings=warnings) from None
