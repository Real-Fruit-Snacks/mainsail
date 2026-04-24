from __future__ import annotations

import os
import sys

from mainsail.common import err, err_path

NAME = "realpath"
ALIASES: list[str] = []
HELP = "resolve a path to its canonical absolute form"


def main(argv: list[str]) -> int:
    args = argv[1:]
    require_exist = False
    no_symlink = False
    zero = False
    relative_to: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a in ("-e", "--canonicalize-existing"):
            require_exist = True
            i += 1
            continue
        if a in ("-m", "--canonicalize-missing"):
            # Python's os.path.realpath already tolerates missing components,
            # which matches GNU -m semantics. Accepted as no-op for compat.
            i += 1
            continue
        if a in ("-s", "-L", "--strip", "--no-symlinks"):
            no_symlink = True
            i += 1
            continue
        if a in ("-z", "--zero"):
            zero = True
            i += 1
            continue
        if a == "--relative-to" and i + 1 < len(args):
            relative_to = args[i + 1]
            i += 2
            continue
        if a.startswith("--relative-to="):
            relative_to = a[len("--relative-to="):]
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        break

    paths = args[i:]
    if not paths:
        err(NAME, "missing operand")
        return 2

    end = "\0" if zero else "\n"
    rc = 0
    for p in paths:
        try:
            if no_symlink:
                result = os.path.abspath(p)
            else:
                result = os.path.realpath(p)
        except OSError as e:
            err_path(NAME, p, e)
            rc = 1
            continue
        if require_exist and not os.path.exists(result):
            err_path(NAME, p, FileNotFoundError(2, "No such file or directory"))
            rc = 1
            continue
        if relative_to is not None:
            try:
                result = os.path.relpath(result, os.path.realpath(relative_to))
            except ValueError as e:
                err(NAME, str(e))
                rc = 1
                continue
        sys.stdout.write(result + end)
    return rc
