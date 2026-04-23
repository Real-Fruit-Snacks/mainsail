from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "mv"
ALIASES: list[str] = ["move", "ren", "rename"]
HELP = "move (rename) files"


def _should_overwrite(
    target: Path,
    src: Path,
    interactive: bool,
    no_clobber: bool,
    update: bool,
    force: bool,
) -> bool:
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
        sys.stderr.write(f"{NAME}: overwrite '{target}'? ")
        sys.stderr.flush()
        try:
            ans = sys.stdin.readline().strip().lower()
        except (OSError, ValueError):
            ans = ""
        if not ans.startswith("y"):
            return False
    return True


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = False
    verbose = False
    no_clobber = False
    interactive = False
    update = False

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
                interactive = False
            elif ch == "n":
                no_clobber = True
                force = False
                interactive = False
            elif ch == "i":
                interactive = True
                force = False
                no_clobber = False
            elif ch == "u":
                update = True
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

        if not _should_overwrite(target, src_path, interactive, no_clobber, update, force):
            continue

        try:
            shutil.move(str(src_path), str(target))
            if verbose:
                sys.stdout.write(f"'{src}' -> '{target}'\n")
        except OSError as e:
            err_path(NAME, src, e)
            rc = 1

    return rc
