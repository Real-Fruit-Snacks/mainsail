"""Build a standalone mainsail binary with Nuitka.

Usage:
    python build.py            # builds into ./dist/
    python build.py --onefile  # (default) single-file executable
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def main() -> int:
    if shutil.which("nuitka") is None:
        try:
            import nuitka  # noqa: F401
        except ImportError:
            print("nuitka not installed — run: pip install nuitka", file=sys.stderr)
            return 1

    DIST.mkdir(exist_ok=True)
    # Modules none of our applets import — skipping them trims several
    # megabytes of stdlib from the onefile payload.
    exclude = (
        "tkinter", "turtle", "test", "tests", "idlelib", "ensurepip",
        "venv", "pydoc_data", "distutils", "setuptools", "pip", "wheel",
        "lib2to3",
    )
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--output-dir={DIST}",
        "--output-filename=mainsail",
        # Applets are discovered via pkgutil at runtime, so Nuitka has to
        # bundle the whole package explicitly.
        "--include-package=mainsail.applets",
        # Nuitka's onefile bootstrap treats "-c" as a Python interpreter
        # self-call; our applets use -c legitimately (gzip -c, cp -c, etc.).
        "--no-deployment-flag=self-execution",
        # Size: strip asserts/docstrings/site from bundled bytecode.
        "--python-flag=no_asserts",
        "--python-flag=no_docstrings",
        "--python-flag=no_site",
        # Size: LTO trims compiled-C code (slower build).
        "--lto=yes",
        *(f"--nofollow-import-to={m}" for m in exclude),
    ]
    if sys.platform == "win32":
        # Windows bundles VC++ runtime DLLs by default; most users already
        # have them. Disabling shaves ~8 MB off the Windows build.
        cmd.append("--include-windows-runtime-dlls=no")
    cmd.append(str(ROOT / "mainsail" / "__main__.py"))
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
