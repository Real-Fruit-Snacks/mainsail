"""Build a standalone pybox binary with Nuitka.

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
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--output-dir",
        str(DIST),
        "--output-filename",
        "pybox",
        # Ensure every applet module is bundled (they are discovered via pkgutil at runtime).
        "--include-package=pybox.applets",
        str(ROOT / "pybox" / "__main__.py"),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
