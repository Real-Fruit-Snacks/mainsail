"""mainsail update — replace the running binary with the latest release.

Hits the GitHub Releases API, picks the asset that matches the current
platform/arch (or the basename suffix of the running binary), downloads
it, smoke-tests it (`--version`), and atomically replaces the current
file. The previous binary is kept next to it as `.old` for one revert.

  mainsail update                  # auto-detect; upgrade if newer
  mainsail update --check          # only print what would change
  mainsail update --force          # re-download even if up-to-date
  mainsail update --asset NAME     # override asset autodetection

Won't touch a `python -m mainsail` invocation — there's no single
binary to replace; use `pip install -U mainsail` instead (when we
publish to PyPI).
"""
from __future__ import annotations

import json as _json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from mainsail import __version__
from mainsail.common import err

NAME = "update"
ALIASES: list[str] = []
HELP = "self-update from the latest GitHub release"


_API = "https://api.github.com/repos/Real-Fruit-Snacks/mainsail/releases/latest"
_USER_AGENT = f"mainsail-update/{__version__}"


def _detect_arch() -> str | None:
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "x64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    return None


def _default_asset_name(self_path: Path) -> str | None:
    """Guess which release asset corresponds to the running binary.

    Strategy:
      1. If the basename starts with `mainsail-…` use it as-is (this is
         exactly what the release-workflow uploads, so the user might
         already have a renamed copy that points to the right preset).
      2. Otherwise infer from sys.platform + machine().
    """
    name = self_path.name
    # Drop any .exe to compare uniformly.
    name_no_ext = name[:-4] if name.lower().endswith(".exe") else name

    if name_no_ext.startswith("mainsail-"):
        return name  # already a release-style filename

    if name.endswith(".pyz"):
        return "mainsail.pyz"

    arch = _detect_arch()
    if arch is None:
        return None
    if sys.platform == "win32":
        return f"mainsail-windows-{arch}.exe"
    if sys.platform == "darwin":
        return f"mainsail-macos-{arch}"
    if sys.platform.startswith("linux"):
        return f"mainsail-linux-{arch}"
    return None


def _fetch_latest() -> dict:
    req = urllib.request.Request(_API, headers={"User-Agent": _USER_AGENT,
                                                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _stream_download(url: str, dst: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT,
                                                "Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        with open(dst, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=65536)


def _make_executable(path: Path) -> None:
    if sys.platform == "win32":
        return
    st = path.stat()
    path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _smoke_test(path: Path) -> tuple[bool, str]:
    """Run `<path> --version`; return (ok, observed_version_or_error)."""
    try:
        # For pyz, we need to invoke via Python.
        if path.suffix == ".pyz":
            cmd = [sys.executable, str(path), "--version"]
        else:
            cmd = [str(path), "--version"]
        proc = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out.startswith("mainsail "):
        return False, out or proc.stderr.strip()
    return True, out.split(" ", 1)[1]


def _replace_binary(current: Path, new_file: Path) -> Path:
    """Atomically swap `current` for `new_file`.

    On POSIX, os.replace is atomic on the same volume and the running
    process keeps its own file handle open. On Windows the running .exe
    can't be deleted — but it CAN be renamed — so we rename current to
    `.old` first, then move the new file into place. Returns the path
    where the previous binary now lives (so the caller can mention it).
    """
    backup = current.with_name(current.name + ".old")
    # Try to clean up any stale .old from a previous update; ignore if
    # it's still locked.
    if backup.exists():
        try:
            backup.unlink()
        except OSError:
            pass
    # Step 1: move the running binary out of the way.
    os.replace(current, backup)
    # Step 2: move the new file into the slot.
    os.replace(new_file, current)
    # Step 3: ensure exec bit (POSIX only).
    _make_executable(current)
    return backup


def _running_binary_path() -> Path | None:
    """Return the path to the running binary, or None when running as
    `python -m mainsail` (where there's no single artifact to update)."""
    arg0 = sys.argv[0] if sys.argv else ""
    if not arg0:
        return None
    p = Path(arg0).resolve()
    if not p.exists():
        return None
    name = p.name.lower()
    # `python -m mainsail` resolves arg0 to .../mainsail/__main__.py
    if name in {"__main__.py", "cli.py"}:
        return None
    return p


def main(argv: list[str]) -> int:
    args = argv[1:]
    check_only = False
    force = False
    asset_override: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a == "--check":
            check_only = True
            i += 1; continue
        if a == "--force":
            force = True
            i += 1; continue
        if a == "--asset" and i + 1 < len(args):
            asset_override = args[i + 1]
            i += 2; continue
        if a.startswith("--asset="):
            asset_override = a.split("=", 1)[1]
            i += 1; continue
        err(NAME, f"unknown option: {a}")
        return 2

    self_path = _running_binary_path()
    if self_path is None:
        err(NAME, "self-update needs a single-file binary; "
                  "this looks like a `python -m mainsail` invocation. "
                  "Use `pip install -U mainsail` (when on PyPI) or "
                  "download a binary from the Releases page.")
        return 2

    asset_name = asset_override or _default_asset_name(self_path)
    if asset_name is None:
        err(NAME, f"could not figure out which release asset matches "
                  f"this binary ({self_path.name}). Try --asset NAME.")
        return 2

    sys.stdout.write(f"current: mainsail {__version__} at {self_path}\n")
    sys.stdout.write(f"target asset: {asset_name}\n")
    sys.stdout.flush()

    try:
        release = _fetch_latest()
    except urllib.error.HTTPError as e:
        err(NAME, f"GitHub API: HTTP {e.code} {e.reason}")
        return 1
    except urllib.error.URLError as e:
        err(NAME, f"GitHub API: {e.reason}")
        return 1
    except OSError as e:
        err(NAME, f"GitHub API: {e}")
        return 1

    tag = release.get("tag_name", "")
    if not tag:
        err(NAME, "release has no tag_name")
        return 1
    latest_version = tag.lstrip("v")
    sys.stdout.write(f"latest release: {tag}\n")

    if latest_version == __version__ and not force:
        sys.stdout.write("already on latest. (use --force to redownload)\n")
        return 0

    asset = next((a for a in release.get("assets", []) if a.get("name") == asset_name), None)
    if asset is None:
        err(NAME, f"asset {asset_name!r} not in release {tag}. "
                  f"available: {', '.join(a['name'] for a in release.get('assets', []))}")
        return 1

    download_url = asset.get("browser_download_url")
    if not download_url:
        err(NAME, "asset has no browser_download_url")
        return 1
    size = asset.get("size", 0)
    sys.stdout.write(f"downloading {asset_name} ({size:,} bytes)... ")
    sys.stdout.flush()

    if check_only:
        sys.stdout.write("[check-only, skipped]\n")
        return 0

    tmp_dir = Path(tempfile.mkdtemp(prefix="mainsail-update-"))
    new_file = tmp_dir / asset_name
    try:
        try:
            _stream_download(download_url, new_file)
        except (urllib.error.URLError, OSError) as e:
            err(NAME, f"download failed: {e}")
            return 1
        sys.stdout.write("done.\n")

        _make_executable(new_file)

        sys.stdout.write("verifying... ")
        sys.stdout.flush()
        ok, info = _smoke_test(new_file)
        if not ok:
            err(NAME, f"new binary failed --version smoke test: {info}")
            return 1
        sys.stdout.write(f"ok ({info}).\n")

        try:
            backup = _replace_binary(self_path, new_file)
        except OSError as e:
            err(NAME, f"replace failed: {e}")
            return 1
        sys.stdout.write(f"updated. previous binary kept at {backup}\n")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
