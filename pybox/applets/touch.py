from __future__ import annotations

import os
import time
from pathlib import Path

from pybox.common import err, err_path

NAME = "touch"
ALIASES: list[str] = []
HELP = "change file timestamps (create if missing)"


def main(argv: list[str]) -> int:
    args = argv[1:]
    no_create = False
    atime_only = False
    mtime_only = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
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
            new_atime = now if (atime_only or not mtime_only) else st.st_atime
            new_mtime = now if (mtime_only or not atime_only) else st.st_mtime
            os.utime(p, (new_atime, new_mtime))
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
    return rc
