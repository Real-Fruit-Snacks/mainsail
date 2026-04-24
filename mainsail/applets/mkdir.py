from __future__ import annotations

import os
import sys
from pathlib import Path

from mainsail.common import err, err_path

NAME = "mkdir"
ALIASES: list[str] = ["md"]
HELP = "make directories"


def main(argv: list[str]) -> int:
    args = argv[1:]
    parents = False
    verbose = False
    mode: int | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "-m" or a.startswith("--mode="):
            value = args[i + 1] if a == "-m" else a.split("=", 1)[1]
            try:
                mode = int(value, 8)
            except ValueError:
                err(NAME, f"invalid mode: '{value}'")
                return 2
            i += 2 if a == "-m" else 1
            continue
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch == "p":
                parents = True
            elif ch == "v":
                verbose = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    dirs = args[i:]
    if not dirs:
        err(NAME, "missing operand")
        return 2

    rc = 0
    for d in dirs:
        p = Path(d)
        try:
            if parents:
                p.mkdir(parents=True, exist_ok=True)
            else:
                p.mkdir()
            if mode is not None:
                os.chmod(p, mode)
            if verbose:
                sys.stdout.write(f"mkdir: created directory '{d}'\n")
        except OSError as e:
            err_path(NAME, d, e)
            rc = 1
    return rc
