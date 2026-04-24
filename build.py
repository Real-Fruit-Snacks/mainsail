"""Build mainsail artifacts.

Usage:
    python build.py             # Nuitka onefile binary (default)
    python build.py --onefile   # same as above, explicit
    python build.py --pyz       # portable Python zipapp (mainsail.pyz)
    python build.py --all       # both binary and zipapp
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def build_pyz() -> int:
    """Build a portable zipapp (mainsail.pyz).

    Runs on any host with Python 3.8+; no native compilation. Intended
    for environments where our Nuitka binary won't run (ESXi, exotic
    architectures) but a Python interpreter is already present.
    """
    DIST.mkdir(exist_ok=True)
    target = DIST / "mainsail.pyz"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(
            ROOT / "mainsail",
            tmp_path / "mainsail",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        # Top-level __main__.py: zipapp's own `main=` synthesiser drops
        # the return code, so we write our own shim that sys.exit()s.
        (tmp_path / "__main__.py").write_text(
            "import sys\nfrom mainsail.cli import main\nsys.exit(main())\n",
            encoding="utf-8",
        )
        zipapp.create_archive(
            source=tmp_path,
            target=target,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    size_kb = target.stat().st_size / 1024
    print(f"wrote {target} ({size_kb:.1f} KB)")
    return 0


def build_binary() -> int:
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
        # NB: `--remove-output` used to tidy the intermediate .dist dir, but
        # on Windows ARM64 runners Defender file-locks the freshly-written
        # artifacts long enough for Nuitka's 5-retry cleanup to fail FATAL
        # even though the onefile .exe was already produced. Skip auto-
        # cleanup; ephemeral CI VMs don't care, and locals can `rm -rf
        # dist/*.dist` themselves.
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


def main() -> int:
    args = set(sys.argv[1:])
    want_pyz = "--pyz" in args or "--all" in args
    want_binary = "--all" in args or not want_pyz  # default: binary
    if want_pyz:
        rc = build_pyz()
        if rc != 0:
            return rc
    if want_binary:
        return build_binary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
