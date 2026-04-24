from __future__ import annotations

import os
import sys

NAME = "pwd"
ALIASES: list[str] = []
HELP = "print name of current/working directory"


def main(argv: list[str]) -> int:
    physical = False
    for arg in argv[1:]:
        if arg == "-L":
            physical = False
        elif arg == "-P":
            physical = True
        elif arg in ("--help", "-h"):
            sys.stdout.write("usage: pwd [-LP]\n")
            return 0
        else:
            sys.stderr.write(f"pwd: invalid option: {arg}\n")
            return 2

    cwd = os.getcwd()
    if physical:
        sys.stdout.write(os.path.realpath(cwd) + "\n")
        return 0

    pwd_env = os.environ.get("PWD")
    if pwd_env and os.path.isabs(pwd_env):
        try:
            # samefile raises OSError on Windows when PWD points to a missing
            # or inaccessible path; treat that as "PWD is stale, fall back".
            if os.path.samefile(pwd_env, cwd):
                sys.stdout.write(pwd_env + "\n")
                return 0
        except OSError:
            pass
    sys.stdout.write(cwd + "\n")
    return 0
