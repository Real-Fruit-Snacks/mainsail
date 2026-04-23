from __future__ import annotations

import platform
import sys

from pybox.common import err

NAME = "uname"
ALIASES: list[str] = []
HELP = "print system information"


def main(argv: list[str]) -> int:
    args = argv[1:]
    wanted: list[str] = []  # preserves order

    def add(ch: str) -> None:
        if ch not in wanted:
            wanted.append(ch)

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            break
        if a in ("-a", "--all"):
            for ch in "snrvmpio":
                add(ch)
            i += 1
            continue
        if a in ("--kernel-name",):
            add("s")
            i += 1
            continue
        if a in ("--nodename",):
            add("n")
            i += 1
            continue
        if a in ("--kernel-release",):
            add("r")
            i += 1
            continue
        if a in ("--kernel-version",):
            add("v")
            i += 1
            continue
        if a in ("--machine",):
            add("m")
            i += 1
            continue
        if a in ("--processor",):
            add("p")
            i += 1
            continue
        if a in ("--hardware-platform",):
            add("i")
            i += 1
            continue
        if a in ("--operating-system",):
            add("o")
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and a != "-":
            if not all(ch in "snrvmpioa" for ch in a[1:]):
                err(NAME, f"invalid option: {a}")
                return 2
            for ch in a[1:]:
                if ch == "a":
                    for c in "snrvmpio":
                        add(c)
                else:
                    add(ch)
            i += 1
            continue
        break

    if not wanted:
        wanted = ["s"]

    u = platform.uname()
    parts: list[str] = []
    for ch in wanted:
        if ch == "s":
            parts.append(u.system or "unknown")
        elif ch == "n":
            parts.append(u.node or "unknown")
        elif ch == "r":
            parts.append(u.release or "unknown")
        elif ch == "v":
            parts.append(u.version or "unknown")
        elif ch == "m":
            parts.append(u.machine or "unknown")
        elif ch == "p":
            parts.append(u.processor or "unknown")
        elif ch == "i":
            parts.append(u.machine or "unknown")
        elif ch == "o":
            if u.system == "Linux":
                parts.append("GNU/Linux")
            else:
                parts.append(u.system or "unknown")

    sys.stdout.write(" ".join(parts) + "\n")
    return 0
