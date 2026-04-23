from __future__ import annotations

import os
import shutil
import sys

from pybox.common import err

NAME = "which"
ALIASES: list[str] = ["where"]
HELP = "locate a command on PATH"


def main(argv: list[str]) -> int:
    args = argv[1:]
    all_matches = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch == "a":
                all_matches = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    names = args[i:]
    if not names:
        err(NAME, "missing command name")
        return 2

    rc = 0
    path_env = os.environ.get("PATH", "")
    path_dirs = path_env.split(os.pathsep)

    # On Windows, also try PATHEXT-suffixed variants
    pathexts = [""]
    if os.name == "nt":
        pathexts = os.environ.get("PATHEXT", ".EXE;.BAT;.CMD;.COM").split(os.pathsep)
        pathexts = [""] + [e.lower() for e in pathexts]

    for name in names:
        found = []
        if os.sep in name or (os.altsep and os.altsep in name):
            if os.access(name, os.X_OK) and os.path.isfile(name):
                found.append(name)
        else:
            for d in path_dirs:
                if not d:
                    continue
                for ext in pathexts:
                    candidate = os.path.join(d, name + ext)
                    if os.path.isfile(candidate):
                        found.append(candidate)
                        if not all_matches:
                            break
                if found and not all_matches:
                    break
        if not found:
            # fallback to shutil.which
            w = shutil.which(name)
            if w:
                found = [w]

        if found:
            for match in found:
                sys.stdout.write(match + "\n")
                if not all_matches:
                    break
        else:
            rc = 1
    return rc
