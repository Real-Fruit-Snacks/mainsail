from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

from pybox.common import err, err_path

NAME = "touch"
ALIASES: list[str] = []
HELP = "change file timestamps (create if missing)"


def _parse_t(s: str) -> float | None:
    """Parse POSIX -t format: [[CC]YY]MMDDhhmm[.ss]."""
    secs_str = "00"
    if "." in s:
        s, secs_str = s.rsplit(".", 1)
    if not s.isdigit() or not secs_str.isdigit():
        return None
    if len(s) == 8:  # MMDDhhmm - current year
        s = f"{datetime.now().year:04d}{s}"
    elif len(s) == 10:  # YYMMDDhhmm - 1969 cutoff per POSIX
        yy = int(s[:2])
        cc = "20" if yy < 69 else "19"
        s = cc + s
    if len(s) != 12:
        return None
    try:
        dt = datetime(
            year=int(s[0:4]),
            month=int(s[4:6]),
            day=int(s[6:8]),
            hour=int(s[8:10]),
            minute=int(s[10:12]),
            second=int(secs_str),
        )
        return dt.timestamp()
    except ValueError:
        return None


def _parse_d(s: str) -> float | None:
    """Parse a -d date string. Supports several ISO 8601 variants."""
    s = s.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            pass
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1] + "+00:00").timestamp()
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    no_create = False
    atime_only = False
    mtime_only = False
    ref_mtime: float | None = None
    ref_atime: float | None = None
    target_time: float | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "-r" and i + 1 < len(args):
            try:
                rst = os.stat(args[i + 1])
            except OSError as e:
                err_path(NAME, args[i + 1], e)
                return 1
            ref_atime = rst.st_atime
            ref_mtime = rst.st_mtime
            i += 2
            continue
        if a == "-d" and i + 1 < len(args):
            target_time = _parse_d(args[i + 1])
            if target_time is None:
                err(NAME, f"invalid date: '{args[i + 1]}'")
                return 2
            i += 2
            continue
        if a == "-t" and i + 1 < len(args):
            target_time = _parse_t(args[i + 1])
            if target_time is None:
                err(NAME, f"invalid -t value: '{args[i + 1]}'")
                return 2
            i += 2
            continue
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch == "c":
                no_create = True
            elif ch == "a":
                atime_only = True
            elif ch == "m":
                mtime_only = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    files = args[i:]
    if not files:
        err(NAME, "missing file operand")
        return 2

    now = time.time()
    rc = 0
    for f in files:
        p = Path(f)
        exists = p.exists()
        if not exists:
            if no_create:
                continue
            try:
                p.touch()
            except OSError as e:
                err_path(NAME, f, e)
                rc = 1
                continue
        try:
            st = p.stat()
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue

        if ref_mtime is not None:
            new_a_src = ref_atime if ref_atime is not None else st.st_atime
            new_m_src = ref_mtime
        elif target_time is not None:
            new_a_src = target_time
            new_m_src = target_time
        else:
            new_a_src = now
            new_m_src = now

        new_atime = new_a_src if (atime_only or not mtime_only) else st.st_atime
        new_mtime = new_m_src if (mtime_only or not atime_only) else st.st_mtime
        try:
            os.utime(p, (new_atime, new_mtime))
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
    return rc
