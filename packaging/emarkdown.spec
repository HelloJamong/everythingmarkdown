# PyInstaller spec: one onedir distribution holding both the GUI and the console CLI.
#
# DRAFT — authored on Linux, not yet built or run on Windows/macOS. The target-OS
# build, bundled Tcl/Tk loading, and frozen execution are P4/"배포 후" items.
#
#   uv run --group build --group dev pyinstaller --noconfirm --clean packaging/emarkdown.spec
#
# Produces dist/EverythingMarkdown/ (Windows/Linux) or dist/EverythingMarkdown.app (macOS) with:
#   - EverythingMarkdown        (GUI, windowed)
#   - everythingmarkdown-cli    (console)
# COLLECT concatenates both Analyses' TOCs and de-duplicates by destination, so the
# shared runtime (numpy, onnxruntime, Tcl/Tk, ...) is collected once. No MERGE: MERGE
# would give even these onedir executables onefile extraction semantics.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

# markitdown reads its own distribution metadata at import time; magika ships model data.
datas = copy_metadata("markitdown") + collect_data_files("magika")
datas += [(str(SRC / "everythingmarkdown" / "logo.png"), "everythingmarkdown")]

gui_a = Analysis([str(ROOT / "packaging" / "emarkdown_gui.py")], pathex=[str(SRC)], datas=datas)
cli_a = Analysis([str(ROOT / "packaging" / "emarkdown_cli.py")], pathex=[str(SRC)], datas=datas)

gui_pyz = PYZ(gui_a.pure)
cli_pyz = PYZ(cli_a.pure)

_icon = str(ROOT / "assets" / ("logo.icns" if sys.platform == "darwin" else "logo.ico"))

gui_exe = EXE(
    gui_pyz, gui_a.scripts, [], exclude_binaries=True,
    name="EverythingMarkdown", console=False, icon=_icon,
)
cli_exe = EXE(
    cli_pyz, cli_a.scripts, [], exclude_binaries=True,
    name="everythingmarkdown-cli", console=True, icon=_icon,
)

# GUI last so COLLECT/BUNDLE inherit console=False (Dock icon, not a background agent).
coll = COLLECT(
    cli_exe, cli_a.binaries, cli_a.datas,
    gui_exe, gui_a.binaries, gui_a.datas,
    name="EverythingMarkdown",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="EverythingMarkdown.app",
        icon=_icon,
        bundle_identifier="dev.hellojamong.everythingmarkdown",
        info_plist={
            "CFBundleDisplayName": "EverythingMarkdown",
            "LSMinimumSystemVersion": "14.0",
            "LSBackgroundOnly": False,
            "NSHighResolutionCapable": True,
        },
    )
