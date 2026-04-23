from __future__ import annotations

import os
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "ln"
ALIASES: list[str] = []
HELP = "create links between files"


def main(argv: list[str]) -> int:
    args = argv[1:]
    symbolic = False
    force = False
    verbose = False
    relative = False
    no_target_dir = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2 or a == "-":
            break
        if not all(ch in "sfvrT" for ch in a[1:]):
            err(NAME, f"invalid option: {a}")
            return 2
        for ch in a[1:]:
            if ch == "s":
                symbolic = True
            elif ch == "f":
                force = True
            elif ch == "v":
                verbose = True
            elif ch == "r":
                relative = True
                symbolic = True
            elif ch == "T":
                no_target_dir = True
        i += 1

    positional = args[i:]
    if not positional:
        err(NAME, "missing operand")
        return 2

    # Normalize into (target, link) pairs
    pairs: list[tuple[str, Path]] = []
    if len(positional) == 1:
        target = positional[0]
        link = Path(".") / Path(target).name
        pairs.append((target, link))
    elif len(positional) == 2 and (no_target_dir or not Path(positional[-1]).is_dir()):
        pairs.append((positional[0], Path(positional[1])))
    else:
        dest_dir = Path(positional[-1])
        if not dest_dir.is_dir():
            err(NAME, f"target '{dest_dir}' is not a directory")
            return 1
        for t in positional[:-1]:
            pairs.append((t, dest_dir / Path(t).name))

    rc = 0
    for target, link in pairs:
        try:
            if link.exists() or link.is_symlink():
                if force:
                    try:
                        link.unlink()
                    except OSError as e:
                        err_path(NAME, str(link), e)
                        rc = 1
                        continue
                else:
                    err(NAME, f"failed to create link '{link}': File exists")
                    rc = 1
                    continue

            effective_target = target
            if symbolic and relative:
                effective_target = os.path.relpath(
                    os.path.abspath(target),
                    os.path.dirname(os.path.abspath(link)) or ".",
                )

            if symbolic:
                is_dir_hint = Path(target).is_dir()
                os.symlink(effective_target, link, target_is_directory=is_dir_hint)
            else:
                os.link(target, link)
            if verbose:
                arrow = " -> " if symbolic else " => "
                sys.stdout.write(f"'{link}'{arrow}'{effective_target}'\n")
        except OSError as e:
            err_path(NAME, str(link), e)
            rc = 1

    return rc
