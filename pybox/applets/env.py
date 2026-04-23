from __future__ import annotations

import os
import subprocess
import sys

from pybox.common import err

NAME = "env"
ALIASES: list[str] = []
HELP = "run a program in a modified environment, or print the environment"


def main(argv: list[str]) -> int:
    args = argv[1:]
    ignore_env = False
    unsets: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a in ("-i", "--ignore-environment"):
            ignore_env = True
            i += 1
            continue
        if a in ("-u", "--unset") and i + 1 < len(args):
            unsets.append(args[i + 1])
            i += 2
            continue
        if a.startswith("-") and a != "-" and len(a) > 1 and not a.startswith("--"):
            for ch in a[1:]:
                if ch == "i":
                    ignore_env = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
            i += 1
            continue
        break

    env = {} if ignore_env else dict(os.environ)
    for u in unsets:
        env.pop(u, None)

    while i < len(args) and "=" in args[i] and not args[i].startswith("="):
        key, _, value = args[i].partition("=")
        env[key] = value
        i += 1

    remaining = args[i:]
    if not remaining:
        for k in sorted(env):
            sys.stdout.write(f"{k}={env[k]}\n")
        return 0

    try:
        rc = subprocess.call(remaining, env=env)
        return rc
    except FileNotFoundError:
        err(NAME, f"{remaining[0]}: No such file or directory")
        return 127
    except OSError as e:
        err(NAME, f"{remaining[0]}: {e.strerror}")
        return 126
