from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "rm"
ALIASES: list[str] = ["del", "erase"]
HELP = "remove files or directories"


def main(argv: list[str]) -> int:
    args = argv[1:]
    recursive = False
    force = False
    verbose = False
    dir_only = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch in ("r", "R"):
                recursive = True
            elif ch == "f":
                force = True
            elif ch == "v":
                verbose = True
            elif ch == "d":
                dir_only = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    targets = args[i:]
    if not targets:
        if force:
            return 0
        err(NAME, "missing operand")
        return 2

    rc = 0
    for t in targets:
        p = Path(t)
        try:
            st = p.lstat()
        except FileNotFoundError:
            if not force:
                err_path(NAME, t, FileNotFoundError(2, "No such file or directory"))
                rc = 1
            continue
        except OSError as e:
            err_path(NAME, t, e)
            rc = 1
            continue

        is_dir = stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode)
        try:
            if is_dir:
                if recursive:
                    shutil.rmtree(p)
                elif dir_only:
                    p.rmdir()
                else:
                    err(NAME, f"cannot remove '{t}': Is a directory")
                    rc = 1
                    continue
            else:
                p.unlink()
            if verbose:
                sys.stdout.write(f"removed '{t}'\n")
        except OSError as e:
            if not force:
                err_path(NAME, t, e)
                rc = 1
    return rc
