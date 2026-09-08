"""Build native-OS onedir probes; never cross-compile or publish releases."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-only", action="store_true", help="skip the GUI bundle")
    args = parser.parse_args()
    environment = os.environ.copy()
    if sys.platform.startswith("linux"):
        # uv's standalone Python keeps Tcl/Tk shared libraries here; PyInstaller's
        # dependency scan does not otherwise find them on this Linux host.
        library_dir = str(Path(sys.base_prefix) / "lib")
        previous = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = library_dir + (os.pathsep + previous if previous else "")
    for mode in (["cli"] if args.cli_only else ["cli", "gui"]):
        name = "everythingmarkdown-p0" + ("-gui" if mode == "gui" else "")
        command = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
            "--name", name, "--paths", str(ROOT / "src"),
            "--distpath", str(ROOT / "dist"),
            "--workpath", str(ROOT / "build" / "pyinstaller"),
            "--specpath", str(ROOT / "build"),
            "--copy-metadata", "markitdown", "--collect-data", "magika",
            "--windowed" if mode == "gui" else "--console",
            str(ROOT / "packaging" / f"p0_{mode}.py"),
        ]
        subprocess.run(command, cwd=ROOT, env=environment, check=True)


if __name__ == "__main__":
    main()
