from __future__ import annotations

import sys

from mainsail.common import err

NAME = "seq"
ALIASES: list[str] = []
HELP = "print a sequence of numbers"


def _is_int_literal(s: str) -> bool:
    if not s:
        return False
    start = 1 if s[0] in "+-" else 0
    return s[start:].isdigit()


def main(argv: list[str]) -> int:
    args = argv[1:]
    separator = "\n"
    fmt: str | None = None
    equal_width = False
    terminator = "\n"

    def _take(flag: str, a: str, idx: int) -> tuple[str | None, int]:
        if len(a) > len(flag):
            return a[len(flag):], idx + 1
        if idx + 1 >= len(args):
            err(NAME, f"{flag}: missing argument")
            return None, idx
        return args[idx + 1], idx + 2

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a == "-s" or (a.startswith("-s") and not _is_int_literal(a)):
            v, i = _take("-s", a, i)
            if v is None:
                return 2
            separator = v
            continue
        if a == "-f" or (a.startswith("-f") and not _is_int_literal(a)):
            v, i = _take("-f", a, i)
            if v is None:
                return 2
            fmt = v
            continue
        if a in ("-w", "--equal-width"):
            equal_width = True
            i += 1
            continue
        break

    nums = args[i:]
    if len(nums) == 1:
        start_s, incr_s, end_s = "1", "1", nums[0]
    elif len(nums) == 2:
        start_s, incr_s, end_s = nums[0], "1", nums[1]
    elif len(nums) == 3:
        start_s, incr_s, end_s = nums[0], nums[1], nums[2]
    else:
        err(NAME, "usage: seq [-s SEP] [-f FMT] [-w] [FIRST [INCR]] LAST")
        return 2

    try:
        start = float(start_s)
        incr = float(incr_s)
        end = float(end_s)
    except ValueError:
        err(NAME, "invalid numeric argument")
        return 2
    if incr == 0:
        err(NAME, "increment must be non-zero")
        return 2

    all_int = all(_is_int_literal(s) for s in (start_s, incr_s, end_s))

    values: list[float] = []
    current = start
    if incr > 0:
        while current <= end + 1e-12:
            values.append(current)
            current += incr
    else:
        while current >= end - 1e-12:
            values.append(current)
            current += incr

    def format_one(v: float) -> str:
        if fmt:
            try:
                return fmt % v
            except (TypeError, ValueError):
                return fmt
        if all_int:
            return str(int(round(v)))
        if v == int(v):
            return str(int(v))
        return f"{v:g}"

    formatted = [format_one(v) for v in values]

    if equal_width and formatted and not fmt:
        max_len = max(len(s.lstrip("-")) for s in formatted)
        padded = []
        for s in formatted:
            if s.startswith("-"):
                padded.append("-" + s[1:].rjust(max_len, "0"))
            else:
                padded.append(s.rjust(max_len, "0"))
        formatted = padded

    if formatted:
        sys.stdout.write(separator.join(formatted))
        sys.stdout.write(terminator)
    return 0
