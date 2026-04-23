from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "mv"
ALIASES: list[str] = ["move", "ren", "rename"]
HELP = "move (rename) files"


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = False
    verbose = False
    no_clobber = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch == "f":
                force = True
                no_clobber = False
            elif ch == "n":
                no_clobber = True
                force = False
            elif ch == "v":
                verbose = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    positional = args[i:]
    if len(positional) < 2:
        err(NAME, "missing file operand")
        return 2
    sources = positional[:-1]
    dest = Path(positional[-1])
    dest_is_dir = dest.is_dir()
    if len(sources) > 1 and not dest_is_dir:
        err(NAME, f"target '{dest}' is not a directory")
        return 1

    rc = 0
    for src in sources:
        src_path = Path(src)
        if not src_path.exists() and not src_path.is_symlink():
            err_path(NAME, src, FileNotFoundError(2, "No such file or directory"))
            rc = 1
            continue

        target = dest / src_path.name if dest_is_dir else dest
        if target.exists():
            if no_clobber:
                continue
            if not force and sys.stdin.isatty():
                sys.stderr.write(f"mv: overwrite '{target}'? ")
                ans = sys.stdin.readline().strip().lower()
                if not ans.startswith("y"):
                    continue
        try:
            shutil.move(str(src_path), str(target))
            if verbose:
                sys.stdout.write(f"'{src}' -> '{target}'\n")
        except OSError as e:
            err_path(NAME, src, e)
            rc = 1

    return rc
