from __future__ import annotations

import sys

from pybox.common import err, err_path

NAME = "cat"
ALIASES: list[str] = ["type"]
HELP = "concatenate files and print on the standard output"

_CHUNK = 64 * 1024


def _numbered(files: list[str], number_all: bool, number_nonblank: bool) -> int:
    rc = 0
    counter = 0
    for f in files:
        try:
            fh = sys.stdin.buffer if f == "-" else open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        try:
            for raw in fh:
                line = raw.decode("utf-8", errors="replace")
                ends_nl = line.endswith("\n")
                body = line[:-1] if ends_nl else line
                blank = len(body) == 0
                if number_all or (number_nonblank and not blank):
                    counter += 1
                    sys.stdout.write(f"{counter:>6}\t{body}")
                else:
                    sys.stdout.write(body)
                if ends_nl:
                    sys.stdout.write("\n")
        finally:
            if close:
                fh.close()
    return rc


def main(argv: list[str]) -> int:
    args = argv[1:]
    number_all = False
    number_nonblank = False
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
                if ch == "n":
                    number_all = True
                    number_nonblank = False
                elif ch == "b":
                    number_nonblank = True
                    number_all = False
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
        i += 1

    if not files:
        files = ["-"]

    if number_all or number_nonblank:
        return _numbered(files, number_all, number_nonblank)

    rc = 0
    for f in files:
        try:
            fh = sys.stdin.buffer if f == "-" else open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        try:
            while True:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
        finally:
            if close:
                fh.close()
    sys.stdout.flush()
    return rc
