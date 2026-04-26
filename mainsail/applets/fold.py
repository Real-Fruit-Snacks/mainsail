"""mainsail fold — wrap each input line at a column."""
from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "fold"
ALIASES: list[str] = []
HELP = "wrap each input line to fit a width"


def main(argv: list[str]) -> int:
    args = argv[1:]
    width = 80
    space_break = False
    by_bytes = False  # we operate on chars; flag accepted for compat

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-w", "--width"} and i + 1 < len(args):
            try:
                width = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid width: {args[i + 1]}")
                return 2
            if width < 1:
                err(NAME, "width must be >= 1")
                return 2
            i += 2; continue
        if a.startswith("-w"):
            try:
                width = int(a[2:])
                i += 1; continue
            except ValueError:
                pass
        if a in {"-s", "--spaces"}:
            space_break = True
            i += 1; continue
        if a in {"-b", "--bytes"}:
            by_bytes = True
            i += 1; continue
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            width = int(a[1:])
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0

    for f in files:
        try:
            if f == "-":
                source = sys.stdin
            else:
                source = open(f, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        try:
            while True:
                line = source.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    body, nl = line[:-2], "\r\n"
                elif line.endswith("\n"):
                    body, nl = line[:-1], "\n"
                else:
                    body, nl = line, ""
                _emit_wrapped(body, width, space_break)
                sys.stdout.write(nl)
        finally:
            if f != "-":
                source.close()
        sys.stdout.flush()
    return rc


def _emit_wrapped(line: str, width: int, space_break: bool) -> None:
    while len(line) > width:
        cut = width
        if space_break:
            # Find last space at or before width.
            idx = line.rfind(" ", 0, width + 1)
            if idx > 0:
                cut = idx + 1  # break AFTER the space, like GNU fold -s
        sys.stdout.write(line[:cut] + "\n")
        line = line[cut:]
    sys.stdout.write(line)
