from __future__ import annotations

import sys

from pybox.common import err

NAME = "dirname"
ALIASES: list[str] = []
HELP = "strip last component from file name"


def _dirname(s: str) -> str:
    stripped = s.rstrip("/\\")
    if not stripped:
        return s if s else "."
    sep = max(stripped.rfind("/"), stripped.rfind("\\"))
    if sep < 0:
        return "."
    if sep == 0:
        return stripped[0]
    return stripped[:sep]


def main(argv: list[str]) -> int:
    args = argv[1:]
    zero = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a in ("-z", "--zero"):
            zero = True
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
    for p in paths:
        sys.stdout.write(_dirname(p) + end)
    return 0
