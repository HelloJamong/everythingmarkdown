"""Build the native-OS release distribution from emarkdown.spec and zip it.

DRAFT — runs PyInstaller for the OS it is invoked on. Windows .exe and macOS .app
must each be built on that OS (or its CI runner); a Linux build is not a release.
"""

import os
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

_PLATFORM_TAG = {"win32": "windows-x64", "darwin": "macos-arm64", "linux": "linux-x64"}


def _release_version() -> str:
    installed = version("everythingmarkdown")
    return "0.0.0-dev" if installed == "0.0.0" else installed


def _zip_tree(source: Path, archive: Path) -> None:
    """Zip source/ preserving symlinks (macOS .app bundles rely on them)."""
    if sys.platform == "darwin":
        # ditto keeps the bundle structure, symlinks, and metadata intact for signing.
        subprocess.run(["ditto", "-c", "-k", "--keepParent", str(source), str(archive)], check=True)
        return
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        for item in sorted(source.rglob("*")):
            zipped.write(item, item.relative_to(source.parent))


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)  # avoid mixing a stale zip from another platform into SHA256SUMS.

    environment = os.environ.copy()
    if sys.platform.startswith("linux"):
        library_dir = str(Path(sys.base_prefix) / "lib")
        previous = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = library_dir + (os.pathsep + previous if previous else "")

    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", str(DIST),
            "--workpath", str(ROOT / "build" / "pyinstaller-release"),
            str(ROOT / "packaging" / "emarkdown.spec"),
        ],
        cwd=ROOT, env=environment, check=True,
    )

    bundle = DIST / ("EverythingMarkdown.app" if sys.platform == "darwin" else "EverythingMarkdown")
    tag = _PLATFORM_TAG.get(sys.platform, sys.platform)
    archive = DIST / f"EverythingMarkdown-{_release_version()}-{tag}.zip"
    _zip_tree(bundle, archive)
    print(archive)


if __name__ == "__main__":
    main()
