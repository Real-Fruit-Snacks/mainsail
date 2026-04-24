from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "head"
ALIASES: list[str] = []
HELP = "output the first part of files"


def _parse_count(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    lines = 10
    bytes_mode = False
    byte_count = 0

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "-n" and i + 1 < len(args):
            n = _parse_count(args[i + 1])
            if n is None:
                err(NAME, f"invalid line count: {args[i + 1]}")
                return 2
            lines = n
            i += 2
            continue
        if a == "-c" and i + 1 < len(args):
            n = _parse_count(args[i + 1])
            if n is None:
                err(NAME, f"invalid byte count: {args[i + 1]}")
                return 2
            bytes_mode = True
            byte_count = n
            i += 2
            continue
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            lines = int(a[1:])
            i += 1
            continue
        break

    files = args[i:] or ["-"]
    multi = len(files) > 1
    rc = 0

    for idx, f in enumerate(files):
        try:
            fh = sys.stdin.buffer if f == "-" else open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        if multi:
            if idx > 0:
                sys.stdout.write("\n")
            sys.stdout.write(f"==> {f} <==\n")
            sys.stdout.flush()
        try:
            if bytes_mode:
                data = fh.read(byte_count)
                sys.stdout.buffer.write(data)
            else:
                count = 0
                for raw in fh:
                    if count >= lines:
                        break
                    sys.stdout.buffer.write(raw)
                    count += 1
        finally:
            if close:
                fh.close()
        sys.stdout.flush()
    return rc
