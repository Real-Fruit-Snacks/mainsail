from __future__ import annotations

import sys
from pathlib import Path

try:
    import pwd as _pwd  # noqa: F401
    import grp as _grp  # noqa: F401
    HAVE_PWDGRP = True
except ImportError:
    HAVE_PWDGRP = False


def err(applet: str, msg: str) -> None:
    sys.stderr.write(f"{applet}: {msg}\n")


def err_path(applet: str, path: str, exc: OSError) -> None:
    msg = exc.strerror or str(exc)
    sys.stderr.write(f"{applet}: {path}: {msg}\n")


def user_name(uid: int) -> str:
    if not HAVE_PWDGRP:
        return "-"
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def group_name(gid: int) -> str:
    if not HAVE_PWDGRP:
        return "-"
    try:
        import grp
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def should_overwrite(
    applet: str,
    target: Path,
    src: Path,
    *,
    interactive: bool,
    no_clobber: bool,
    update: bool,
    force: bool,
) -> bool:
    """Shared overwrite policy for cp/mv.

    Returns True if the caller should proceed with overwriting the target.
    Honors -n (never), -u (only when source is strictly newer), and -i
    (prompt y/n on stderr, reading the answer from stdin).
    """
    if not (target.exists() or target.is_symlink()):
        return True
    if no_clobber:
        return False
    if update:
        try:
            if src.stat().st_mtime <= target.stat().st_mtime:
                return False
        except OSError:
            pass
    if interactive and not force:
        sys.stderr.write(f"{applet}: overwrite '{target}'? ")
        sys.stderr.flush()
        try:
            ans = sys.stdin.readline().strip().lower()
        except (OSError, ValueError):
            ans = ""
        if not ans.startswith("y"):
            return False
    return True
