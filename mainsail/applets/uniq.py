from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "uniq"
ALIASES: list[str] = []
HELP = "report or omit repeated adjacent lines"


def _key(line: str, skip_fields: int, skip_chars: int, width: int | None, ignore_case: bool) -> str:
    s = line
    if skip_fields > 0:
        i = 0
        skipped = 0
        while skipped < skip_fields and i < len(s):
            while i < len(s) and s[i] in " \t":
                i += 1
            while i < len(s) and s[i] not in " \t":
                i += 1
            skipped += 1
        s = s[i:]
    if skip_chars > 0:
        s = s[skip_chars:]
    if width is not None:
        s = s[:width]
    if ignore_case:
        s = s.lower()
    return s


def main(argv: list[str]) -> int:
    args = argv[1:]
    count = False
    only_dup = False
    only_unique = False
    ignore_case = False
    skip_fields = 0
    skip_chars = 0
    width: int | None = None

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
            args = args[:i] + args[i + 1:]
            break
        if a == "-c":
            count = True
            i += 1
        elif a == "-d":
            only_dup = True
            i += 1
        elif a == "-u":
            only_unique = True
            i += 1
        elif a == "-i":
            ignore_case = True
            i += 1
        elif a.startswith("-f"):
            v, i = _take("-f", a, i)
            if v is None:
                return 2
            try:
                skip_fields = int(v)
            except ValueError:
                err(NAME, f"-f: invalid value '{v}'")
                return 2
        elif a.startswith("-s"):
            v, i = _take("-s", a, i)
            if v is None:
                return 2
            try:
                skip_chars = int(v)
            except ValueError:
                err(NAME, f"-s: invalid value '{v}'")
                return 2
        elif a.startswith("-w"):
            v, i = _take("-w", a, i)
            if v is None:
                return 2
            try:
                width = int(v)
            except ValueError:
                err(NAME, f"-w: invalid value '{v}'")
                return 2
        elif a.startswith("-") and a != "-" and len(a) > 1 and a[1:].isdigit():
            skip_fields = int(a[1:])
            i += 1
        else:
            break

    positional = args[i:]
    input_path = positional[0] if len(positional) >= 1 else "-"
    output_path = positional[1] if len(positional) >= 2 else "-"

    try:
        in_fh = sys.stdin if input_path == "-" else open(input_path, "r", encoding="utf-8", errors="replace")
    except OSError as e:
        err_path(NAME, input_path, e)
        return 1
    try:
        out_fh = sys.stdout if output_path == "-" else open(output_path, "w", encoding="utf-8", newline="")
    except OSError as e:
        err_path(NAME, output_path, e)
        if input_path != "-":
            in_fh.close()
        return 1

    def emit(line: str, cnt: int) -> None:
        if only_dup and cnt < 2:
            return
        if only_unique and cnt != 1:
            return
        if count:
            out_fh.write(f"{cnt:>7} {line}\n")
        else:
            out_fh.write(line + "\n")

    try:
        prev_line: str | None = None
        prev_key: str | None = None
        cnt = 0
        for raw in in_fh:
            line = raw.rstrip("\n")
            k = _key(line, skip_fields, skip_chars, width, ignore_case)
            if prev_key is None:
                prev_line = line
                prev_key = k
                cnt = 1
            elif k == prev_key:
                cnt += 1
            else:
                emit(prev_line, cnt)
                prev_line = line
                prev_key = k
                cnt = 1
        if prev_line is not None:
            emit(prev_line, cnt)
    finally:
        if input_path != "-":
            in_fh.close()
        if output_path != "-":
            out_fh.close()
    return 0
