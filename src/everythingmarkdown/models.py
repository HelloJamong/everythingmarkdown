"""Shared request/result and safe, stable errors for GUI and CLI callers."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    TOO_LARGE = "TOO_LARGE"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    EMPTY_RESULT = "EMPTY_RESULT"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    OUTPUT_CONFLICT = "OUTPUT_CONFLICT"
    OUTPUT_UNWRITABLE = "OUTPUT_UNWRITABLE"
    WRITE_FAILED = "WRITE_FAILED"
    CANCELLED = "CANCELLED"


_ERROR_DETAILS = {
    ErrorCode.INVALID_INPUT: (2, "읽을 수 있는 일반 로컬 파일과 절대 작업 경로를 지정해 주세요."),
    ErrorCode.NOT_FOUND: (2, "입력 파일을 찾을 수 없습니다."),
    ErrorCode.UNSUPPORTED_FORMAT: (2, "지원하지 않는 파일 형식입니다."),
    ErrorCode.TOO_LARGE: (2, "입력 파일이 허용된 크기를 초과했습니다."),
    ErrorCode.CONVERSION_FAILED: (3, "문서를 변환하지 못했습니다. 파일 형식과 손상 여부를 확인해 주세요."),
    ErrorCode.EMPTY_RESULT: (3, "추출된 텍스트가 없습니다. OCR은 지원하지 않습니다."),
    ErrorCode.MISSING_DEPENDENCY: (3, "변환에 필요한 라이브러리가 없습니다. 설치 상태를 확인해 주세요."),
    ErrorCode.OUTPUT_CONFLICT: (4, "같은 이름의 결과가 이미 존재합니다. 기존 결과를 보존했습니다."),
    ErrorCode.OUTPUT_UNWRITABLE: (4, "결과 폴더를 사용할 수 없습니다. 경로와 쓰기 권한을 확인해 주세요."),
    ErrorCode.WRITE_FAILED: (4, "결과 저장을 완료하지 못했습니다. 저장 공간과 쓰기 권한을 확인해 주세요."),
    ErrorCode.CANCELLED: (130, "변환을 중단했습니다."),
}


class ConversionError(Exception):
    """Never includes raw parser exceptions or source document contents."""

    def __init__(
        self,
        code: ErrorCode,
        *,
        path: Path | None = None,
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.code = code
        self.path = path
        self.warnings = warnings
        self.exit_code, message = _ERROR_DETAILS[code]
        super().__init__(message)


@dataclass(frozen=True)
class ConversionRequest:
    input_path: Path
    launch_dir: Path


@dataclass(frozen=True)
class ConversionResult:
    output_path: Path
    warnings: tuple[str, ...] = ()
