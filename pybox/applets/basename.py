from __future__ import annotations

import sys

from pybox.common import err

NAME = "basename"
ALIASES: list[str] = []
HELP = "strip directory components from a filename"


def _basename(s: str) -> str:
    stripped = s.rstrip("/\\")
    if not stripped:
        return s[0] if s else ""
    sep = max(stripped.rfind("/"), stripped.rfind("\\"))
    return stripped[sep + 1:] if sep >= 0 else stripped


def main(argv: list[str]) -> int:
    args = argv[1:]
    multiple = False
    suffix_all: str | None = None
    zero = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a in ("-a", "--multiple"):
            multiple = True
            i += 1
            continue
        if a == "-s" and i + 1 < len(args):
            suffix_all = args[i + 1]
            multiple = True
            i += 2
            continue
        if a.startswith("--suffix="):
            suffix_all = a[len("--suffix="):]
            multiple = True
            i += 1
            continue
        if a in ("-z", "--zero"):
            zero = True
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        break

    remaining = args[i:]
    if not remaining:
        err(NAME, "missing operand")
        return 2

    end = "\0" if zero else "\n"
    # -s and -a both set `multiple`; otherwise POSIX form "PATH [SUFFIX]".
    if multiple:
        paths = remaining
        suffix = suffix_all or ""
    else:
        paths = [remaining[0]]
        suffix = remaining[1] if len(remaining) > 1 else ""

    for p in paths:
        name = _basename(p)
        if suffix and name.endswith(suffix) and name != suffix:
            name = name[:-len(suffix)]
        sys.stdout.write(name + end)
    return 0
