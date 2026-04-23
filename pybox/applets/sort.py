from __future__ import annotations

import sys

from pybox.common import err, err_path

NAME = "sort"
ALIASES: list[str] = []
HELP = "sort lines of text files"


def _numeric_key(s: str) -> tuple[int, float, str]:
    stripped = s.lstrip()
    # pull off leading number (with optional sign and decimals)
    end = 0
    if end < len(stripped) and stripped[end] in "+-":
        end += 1
    saw_digit = False
    saw_dot = False
    while end < len(stripped):
        c = stripped[end]
        if c.isdigit():
            saw_digit = True
            end += 1
        elif c == "." and not saw_dot:
            saw_dot = True
            end += 1
        else:
            break
    if not saw_digit:
        return (1, 0.0, s)
    try:
        val = float(stripped[:end])
    except ValueError:
        return (1, 0.0, s)
    return (0, val, s)


def main(argv: list[str]) -> int:
    args = argv[1:]
    reverse = False
    numeric = False
    unique = False
    ignore_case = False
    ignore_leading_blanks = False
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "-" or not a.startswith("-") or len(a) < 2:
            files.append(a)
        else:
            for ch in a[1:]:
                if ch == "r":
                    reverse = True
                elif ch == "n":
                    numeric = True
                elif ch == "u":
                    unique = True
                elif ch == "f":
                    ignore_case = True
                elif ch == "b":
                    ignore_leading_blanks = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
        i += 1

    if not files:
        files = ["-"]

    lines: list[str] = []
    rc = 0
    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        try:
            for line in fh:
                lines.append(line.rstrip("\n"))
        finally:
            if close:
                fh.close()

    def key(s: str):
        k = s
        if ignore_leading_blanks:
            k = k.lstrip()
        if ignore_case:
            k = k.lower()
        if numeric:
            return _numeric_key(k)
        return k

    lines.sort(key=key, reverse=reverse)

    if unique:
        seen = set()
        deduped: list[str] = []
        for line in lines:
            k = key(line)
            if k in seen:
                continue
            seen.add(k)
            deduped.append(line)
        lines = deduped

    for line in lines:
        sys.stdout.write(line + "\n")
    return rc
