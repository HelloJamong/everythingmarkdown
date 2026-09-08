"""Terminal entry point for the shared local conversion service."""

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .models import ConversionError, ConversionRequest, ErrorCode
from .service import ConversionService


def _version_label() -> str:
    try:
        installed = version("everythingmarkdown")
    except PackageNotFoundError:
        installed = "0.0.0"
    if installed == "0.0.0":
        return "EverythingMarkdown (개발 중; 정식 릴리즈 없음)"
    return f"EverythingMarkdown {installed}"


def _report_error(error: ConversionError) -> int:
    print(f"{error.code}: {error}", file=sys.stderr)
    if error.path is not None:
        print(f"경로: {error.path}", file=sys.stderr)
    for warning in error.warnings:
        print(f"경고: {warning}", file=sys.stderr)
    return error.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="everythingmarkdown",
        description="로컬 파일을 Markdown으로 변환합니다. 기존 결과는 덮어쓰지 않습니다.",
        epilog="결과: 시작 작업 디렉터리의 convert_result/<원래 이름>.md",
    )
    parser.add_argument("file", nargs="?", help="변환할 로컬 파일 경로 (PDF/DOCX/PPTX/XLSX/HTML/CSV/TXT)")
    parser.add_argument("--version", action="version", version=_version_label())
    try:
        args = parser.parse_args(argv)
        # Capture before input; never recalculate CWD after the prompt or conversion.
        try:
            launch_dir = Path.cwd()
        except OSError:
            raise ConversionError(ErrorCode.OUTPUT_UNWRITABLE) from None
        path_text = args.file
        if path_text is None:
            if not sys.stdin.isatty():
                parser.error("터미널이 아닌 환경에서는 파일 경로 인자가 필요합니다.")
            print("변환할 파일 경로: ", end="", file=sys.stderr, flush=True)
            path_text = input().strip()
            if len(path_text) >= 2 and path_text[0] == path_text[-1] and path_text[0] in "\"'":
                path_text = path_text[1:-1]
        if not path_text.strip():
            parser.error("파일 경로를 입력해 주세요.")
        result = ConversionService().convert(
            ConversionRequest(input_path=Path(path_text), launch_dir=launch_dir)
        )
        for warning in result.warnings:
            print(f"경고: {warning}", file=sys.stderr)
        print(result.output_path, flush=True)
        return 0
    except (KeyboardInterrupt, EOFError):
        return _report_error(ConversionError(ErrorCode.CANCELLED))
    except ConversionError as error:
        return _report_error(error)
    except Exception:
        # Unexpected service errors must not reveal parser text or tracebacks.
        return _report_error(ConversionError(ErrorCode.CONVERSION_FAILED))


if __name__ == "__main__":
    raise SystemExit(main())
