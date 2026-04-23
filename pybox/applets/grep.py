from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "grep"
ALIASES: list[str] = []
HELP = "print lines matching a pattern"


def _walk_files(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    out.append(os.path.join(root, f))
        else:
            out.append(p)
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    ignore_case = False
    invert = False
    show_line_num = False
    recursive = False
    fixed_string = False
    list_files = False
    count_only = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2:
            break
        for ch in a[1:]:
            if ch == "i":
                ignore_case = True
            elif ch == "v":
                invert = True
            elif ch == "n":
                show_line_num = True
            elif ch in ("r", "R"):
                recursive = True
            elif ch == "F":
                fixed_string = True
            elif ch == "l":
                list_files = True
            elif ch == "c":
                count_only = True
            elif ch == "E":
                pass  # Python re is already extended
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    remaining = args[i:]
    if not remaining:
        err(NAME, "missing pattern")
        return 2

    pattern = remaining[0]
    targets = remaining[1:]

    if fixed_string:
        pattern = re.escape(pattern)
    flags = re.IGNORECASE if ignore_case else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error as e:
        err(NAME, f"bad pattern: {e}")
        return 2

    if not targets:
        targets = ["-"]
    if recursive:
        expanded: list[str] = []
        for t in targets:
            if os.path.isdir(t):
                for root, _, files in os.walk(t):
                    for f in sorted(files):
                        expanded.append(os.path.join(root, f))
            else:
                expanded.append(t)
        targets = expanded

    show_filename = len(targets) > 1 or recursive
    matched_any = False
    rc = 1

    for t in targets:
        try:
            fh = sys.stdin if t == "-" else open(t, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, t, e)
            rc = 2
            continue

        close = t != "-"
        match_count = 0
        try:
            for lineno, line in enumerate(fh, 1):
                stripped = line.rstrip("\n")
                hit = bool(rx.search(stripped))
                if invert:
                    hit = not hit
                if hit:
                    match_count += 1
                    matched_any = True
                    if list_files:
                        break
                    if count_only:
                        continue
                    out: list[str] = []
                    if show_filename:
                        out.append(t)
                    if show_line_num:
                        out.append(str(lineno))
                    out.append(stripped)
                    sys.stdout.write(":".join(out) + "\n")
        finally:
            if close:
                fh.close()

        if list_files and match_count > 0:
            sys.stdout.write(t + "\n")
        if count_only:
            if show_filename:
                sys.stdout.write(f"{t}:{match_count}\n")
            else:
                sys.stdout.write(f"{match_count}\n")

    if matched_any:
        rc = 0
    return rc
