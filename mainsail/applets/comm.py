from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "comm"
ALIASES: list[str] = []
HELP = "compare two sorted files line by line"


def main(argv: list[str]) -> int:
    args = argv[1:]
    suppress = {1: False, 2: False, 3: False}
    sep = "\t"
    check_order = True

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
        # -1, -2, -3 individually OR combined: -12, -13, -23, -123
        if a.startswith("-") and len(a) >= 2 and a[1:].isdigit() and all(c in "123" for c in a[1:]):
            for c in a[1:]:
                suppress[int(c)] = True
            i += 1
            continue
        if a == "--nocheck-order":
            check_order = False
            i += 1
            continue
        if a == "--check-order":
            check_order = True
            i += 1
            continue
        if a == "--output-delimiter" and i + 1 < len(args):
            sep = args[i + 1]
            i += 2
            continue
        if a.startswith("--output-delimiter="):
            sep = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    rest = args[i:]
    if len(rest) != 2:
        err(NAME, "two file operands required")
        return 2
    f1, f2 = rest

    def _open(p: str):
        return sys.stdin if p == "-" else open(p, "r", encoding="utf-8", errors="replace")

    try:
        h1 = _open(f1)
    except OSError as e:
        err_path(NAME, f1, e)
        return 1
    try:
        h2 = _open(f2)
    except OSError as e:
        err_path(NAME, f2, e)
        if h1 is not sys.stdin:
            h1.close()
        return 1

    def _readline(h):
        ln = h.readline()
        if not ln:
            return None
        return ln.rstrip("\r\n")

    rc = 0
    try:
        a_line = _readline(h1)
        b_line = _readline(h2)
        prev_a: str | None = None
        prev_b: str | None = None
        while a_line is not None or b_line is not None:
            if check_order:
                if prev_a is not None and a_line is not None and a_line < prev_a:
                    err(NAME, f"file 1 is not in sorted order")
                    rc = 1
                if prev_b is not None and b_line is not None and b_line < prev_b:
                    err(NAME, f"file 2 is not in sorted order")
                    rc = 1
            if a_line is None:
                col = 2
                line = b_line
                prev_b = b_line
                b_line = _readline(h2)
            elif b_line is None:
                col = 1
                line = a_line
                prev_a = a_line
                a_line = _readline(h1)
            elif a_line == b_line:
                col = 3
                line = a_line
                prev_a, prev_b = a_line, b_line
                a_line = _readline(h1)
                b_line = _readline(h2)
            elif a_line < b_line:
                col = 1
                line = a_line
                prev_a = a_line
                a_line = _readline(h1)
            else:
                col = 2
                line = b_line
                prev_b = b_line
                b_line = _readline(h2)
            if suppress[col]:
                continue
            # Indent = number of NOT-suppressed lower-numbered columns. So
            # if only column 3 is being emitted (cols 1 & 2 suppressed),
            # the leading tabs collapse to zero.
            shown_below = sum(1 for c in (1, 2) if c < col and not suppress[c])
            sys.stdout.write(f"{sep * shown_below}{line}\n")
    finally:
        if h1 is not sys.stdin:
            h1.close()
        if h2 is not sys.stdin:
            h2.close()
    sys.stdout.flush()
    return rc
