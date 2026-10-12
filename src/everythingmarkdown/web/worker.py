"""Child-process entry: convert one file. Prints only a safe ErrorCode on failure.

Usage: python -m everythingmarkdown.web.worker <input_path> <launch_dir>
"""

import sys
from pathlib import Path

from everythingmarkdown import ConversionError, ConversionRequest, ConversionService, ErrorCode


def main(argv: list[str]) -> int:
    try:
        ConversionService().convert(ConversionRequest(Path(argv[0]), Path(argv[1])))
    except ConversionError as error:
        print(error.code.value)
        return 1
    except Exception:
        print(ErrorCode.CONVERSION_FAILED.value)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
