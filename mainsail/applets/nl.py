from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "nl"
ALIASES: list[str] = []
HELP = "number lines of files"


def main(argv: list[str]) -> int:
    args = argv[1:]
    width = 6
    sep = "\t"
    start = 1
    increment = 1
    body_style = "t"  # t=non-empty, a=all, n=none
    skip_blank = False  # alias for body_style="t"

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-b", "--body-numbering"} and i + 1 < len(args):
            body_style = args[i + 1]
            if body_style not in {"a", "t", "n"}:
                err(NAME, f"invalid body-numbering style: {body_style}")
                return 2
            i += 2
            continue
        if a in {"-w", "--number-width"} and i + 1 < len(args):
            try:
                width = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid width: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-s", "--number-separator"} and i + 1 < len(args):
            sep = args[i + 1]
            i += 2
            continue
        if a in {"-v", "--starting-line-number"} and i + 1 < len(args):
            try:
                start = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid starting line: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-i", "--line-increment"} and i + 1 < len(args):
            try:
                increment = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid increment: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a == "-ba":
            body_style = "a"
            i += 1
            continue
        if a == "-bt":
            body_style = "t"
            i += 1
            continue
        if a == "-bn":
            body_style = "n"
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    n = start
    rc = 0

    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        try:
            for line in fh:
                stripped = line.rstrip("\r\n")
                emit = True
                if body_style == "n":
                    emit = False
                elif body_style == "t" and stripped == "":
                    emit = False
                if emit:
                    sys.stdout.write(f"{str(n).rjust(width)}{sep}{stripped}\n")
                    n += increment
                else:
                    # blank/skipped line: print without number, with separator
                    # GNU nl prints just the line, no leading number columns
                    sys.stdout.write(f"{stripped}\n")
        finally:
            if f != "-":
                fh.close()
        sys.stdout.flush()

    return rc
