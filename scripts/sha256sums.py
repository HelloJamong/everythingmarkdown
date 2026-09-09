"""Write and verify a SHA256SUMS file for the release archives in dist/.

    uv run python scripts/sha256sums.py write      # create dist/SHA256SUMS
    uv run python scripts/sha256sums.py verify     # check dist/ against it

Format matches `sha256sum -c`: "<hex>  <filename>" per line, names only (no paths).
"""

import hashlib
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / "dist"
SUMS = DIST / "SHA256SUMS"


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _archives() -> list[Path]:
    return sorted(p for p in DIST.glob("*.zip") if p.is_file())


def write() -> int:
    archives = _archives()
    if not archives:
        print("dist/에 .zip 배포 파일이 없습니다.", file=sys.stderr)
        return 1
    SUMS.write_text("".join(f"{_digest(p)}  {p.name}\n" for p in archives), encoding="utf-8")
    print(SUMS)
    return 0


def verify() -> int:
    if not SUMS.is_file():
        print("dist/SHA256SUMS가 없습니다. 먼저 write를 실행하세요.", file=sys.stderr)
        return 1
    ok = True
    listed = set()
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        expected, _, name = line.partition("  ")
        listed.add(name)
        target = DIST / name
        actual = _digest(target) if target.is_file() else None
        status = "OK" if actual == expected else "FAILED"
        ok &= status == "OK"
        print(f"{name}: {status}")
    for extra in sorted({p.name for p in _archives()} - listed):
        ok = False
        print(f"{extra}: 목록에 없는 파일")
    return 0 if ok else 1


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in {"write", "verify"}:
        print(f"사용법: {sys.argv[0]} write|verify", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(write() if action == "write" else verify())
