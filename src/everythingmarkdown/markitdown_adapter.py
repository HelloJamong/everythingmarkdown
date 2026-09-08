"""Narrow MarkItDown boundary; input/filesystem policy belongs to the service."""

from pathlib import Path

from .models import ConversionError, ErrorCode

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".csv", ".txt")


class MarkItDownAdapter:
    def convert(self, path: Path) -> str:
        extension = path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ConversionError(ErrorCode.UNSUPPORTED_FORMAT, path=path)
        # Lazy imports allow a missing installation to become a stable user error.
        try:
            from markitdown import (
                FileConversionException,
                MarkItDown,
                MissingDependencyException,
            )
            from markitdown.converters import (
                CsvConverter,
                DocxConverter,
                HtmlConverter,
                PdfConverter,
                PlainTextConverter,
                PptxConverter,
                XlsxConverter,
            )
        except ImportError:
            raise ConversionError(ErrorCode.MISSING_DEPENDENCY, path=path) from None

        converters = {
            ".pdf": PdfConverter,
            ".docx": DocxConverter,
            ".pptx": PptxConverter,
            ".xlsx": XlsxConverter,
            ".html": HtmlConverter,
            ".csv": CsvConverter,
            ".txt": PlainTextConverter,
        }
        try:
            engine = MarkItDown(enable_builtins=False, enable_plugins=False)
            engine.register_converter(converters[extension]())
            markdown = engine.convert_local(str(path)).markdown
        except (ImportError, MissingDependencyException):
            raise ConversionError(ErrorCode.MISSING_DEPENDENCY, path=path) from None
        except FileConversionException as error:
            # MarkItDown wraps converter dependency errors inside failed attempts.
            missing = any(
                attempt.exc_info is not None
                and isinstance(attempt.exc_info[1], (ImportError, MissingDependencyException))
                for attempt in error.attempts or ()
            )
            code = ErrorCode.MISSING_DEPENDENCY if missing else ErrorCode.CONVERSION_FAILED
            raise ConversionError(code, path=path) from None
        except Exception:
            raise ConversionError(ErrorCode.CONVERSION_FAILED, path=path) from None
        if not isinstance(markdown, str):
            raise ConversionError(ErrorCode.CONVERSION_FAILED, path=path)
        if not markdown.strip():
            raise ConversionError(ErrorCode.EMPTY_RESULT, path=path)
        return markdown
