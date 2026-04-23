from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pybox.common import err, err_path, should_overwrite

NAME = "cp"
ALIASES: list[str] = ["copy"]
HELP = "copy files and directories"


def main(argv: list[str]) -> int:
    args = argv[1:]
    recursive = False
    force = False
    verbose = False
    preserve_meta = False
    interactive = False
    no_clobber = False
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
            if ch in ("r", "R"):
                recursive = True
            elif ch == "f":
                force = True
                interactive = False
                no_clobber = False
            elif ch == "v":
                verbose = True
            elif ch == "p":
                preserve_meta = True
            elif ch == "a":
                recursive = True
                preserve_meta = True
            elif ch == "i":
                interactive = True
                no_clobber = False
                force = False
            elif ch == "n":
                no_clobber = True
                interactive = False
            elif ch == "u":
                update = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    positional = args[i:]
    if len(positional) < 2:
        err(NAME, "missing file operand")
        return 2
    sources = positional[:-1]
    dest = positional[-1]

    dest_path = Path(dest)
    dest_is_dir = dest_path.is_dir()
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

        target = dest_path / src_path.name if dest_is_dir else dest_path

        if not should_overwrite(
            NAME, target, src_path,
            interactive=interactive, no_clobber=no_clobber,
            update=update, force=force,
        ):
            continue

        try:
            if src_path.is_dir() and not src_path.is_symlink():
                if not recursive:
                    err(NAME, f"-r not specified; omitting directory '{src}'")
                    rc = 1
                    continue
                if target.exists():
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                shutil.copytree(src_path, target, symlinks=True)
            else:
                if target.exists() or target.is_symlink():
                    try:
                        target.unlink()
                    except OSError:
                        pass
                if preserve_meta:
                    shutil.copy2(src_path, target, follow_symlinks=False)
                else:
                    shutil.copy(src_path, target, follow_symlinks=False)
            if verbose:
                sys.stdout.write(f"'{src}' -> '{target}'\n")
        except OSError as e:
            err_path(NAME, src, e)
            rc = 1

    return rc
