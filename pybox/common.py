from __future__ import annotations

import os
import sys
from typing import Iterable

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


def parse_short_flags(
    args: list[str],
    known: Iterable[str],
) -> tuple[set[str], list[str]]:
    """Parse POSIX-style short flags up to first non-flag or '--'.

    Returns (set of flag chars seen, remaining args).
    """
    known_set = set(known)
    seen: set[str] = set()
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return seen, args[i + 1:]
        if a == "-" or not a.startswith("-") or len(a) < 2:
            break
        chars = a[1:]
        if not set(chars).issubset(known_set):
            break
        seen.update(chars)
        i += 1
    return seen, args[i:]


def open_input(path: str):
    """Open a file for binary read, or return sys.stdin.buffer for '-'."""
    if path == "-":
        return sys.stdin.buffer, False
    return open(path, "rb"), True


def write_bytes(data: bytes) -> None:
    sys.stdout.buffer.write(data)


def is_windows() -> bool:
    return os.name == "nt"
