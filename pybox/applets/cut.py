from __future__ import annotations

import sys

from pybox.common import err, err_path

NAME = "cut"
ALIASES: list[str] = []
HELP = "remove sections from each line of files"


def _parse_list(s: str) -> list[tuple[int, int]]:
    """Parse '1,3-5,7-' into list of (start, end) inclusive, end=-1 for open."""
    ranges: list[tuple[int, int]] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else -1
        else:
            start = end = int(part)
        if start < 1:
            raise ValueError(f"position must be >= 1: {part}")
        ranges.append((start, end))
    if not ranges:
        raise ValueError("empty list")
    return ranges


def _positions(n: int, ranges: list[tuple[int, int]]) -> list[int]:
    sel: set[int] = set()
    for start, end in ranges:
        stop = n if end == -1 else min(end, n)
        for p in range(start, stop + 1):
            sel.add(p)
    return sorted(sel)


def main(argv: list[str]) -> int:
    args = argv[1:]
    delim = "\t"
    suppress = False
    mode: str | None = None
    list_spec: str | None = None
    files: list[str] = []

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
            files.extend(args[i + 1:])
            break
        if a == "-d" or a.startswith("-d"):
            v, i = _take("-d", a, i)
            if v is None:
                return 2
            delim = v
            continue
        if a == "-f" or a.startswith("-f"):
            v, i = _take("-f", a, i)
            if v is None:
                return 2
            mode, list_spec = "f", v
            continue
        if a == "-c" or a.startswith("-c"):
            v, i = _take("-c", a, i)
            if v is None:
                return 2
            mode, list_spec = "c", v
            continue
        if a == "-s":
            suppress = True
            i += 1
            continue
        if a == "-n":
            i += 1  # POSIX compat no-op (with -b)
            continue
        if a == "-" or not a.startswith("-"):
            files.append(a)
            i += 1
            continue
        err(NAME, f"invalid option: {a}")
        return 2

    if mode is None or list_spec is None:
        err(NAME, "must specify -f or -c")
        return 2

    try:
        ranges = _parse_list(list_spec)
    except ValueError as e:
        err(NAME, f"invalid list '{list_spec}': {e}")
        return 2

    if not files:
        files = ["-"]

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
            for raw in fh:
                line = raw.rstrip("\n")
                if mode == "f":
                    if delim not in line:
                        if suppress:
                            continue
                        sys.stdout.write(line + "\n")
                        continue
                    fields = line.split(delim)
                    positions = _positions(len(fields), ranges)
                    out_fields = [fields[p - 1] for p in positions]
                    sys.stdout.write(delim.join(out_fields) + "\n")
                else:
                    positions = _positions(len(line), ranges)
                    out_chars = "".join(line[p - 1] for p in positions)
                    sys.stdout.write(out_chars + "\n")
        finally:
            if close:
                fh.close()
    return rc
