from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "cmp"
ALIASES: list[str] = []
HELP = "compare two files byte by byte"


def main(argv: list[str]) -> int:
    args = argv[1:]
    silent = False
    print_chars = False
    print_all = False
    skip1 = 0
    skip2 = 0
    bytes_limit: int | None = None

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
        if a in {"-s", "--quiet", "--silent"}:
            silent = True
            i += 1
            continue
        if a in {"-b", "--print-bytes"}:
            print_chars = True
            i += 1
            continue
        if a in {"-l", "--verbose"}:
            print_all = True
            i += 1
            continue
        if a in {"-n", "--bytes"} and i + 1 < len(args):
            try:
                bytes_limit = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid byte count: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a == "-i" and i + 1 < len(args):
            try:
                spec = args[i + 1]
                if ":" in spec:
                    a1, a2 = spec.split(":", 1)
                    skip1, skip2 = int(a1), int(a2)
                else:
                    skip1 = skip2 = int(spec)
            except ValueError:
                err(NAME, f"invalid skip: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    rest = args[i:]
    if len(rest) < 2:
        err(NAME, "missing operand")
        return 2
    f1, f2 = rest[0], rest[1]
    if len(rest) > 2:
        try:
            skip1 = int(rest[2])
        except ValueError:
            err(NAME, f"invalid skip: {rest[2]}")
            return 2
    if len(rest) > 3:
        try:
            skip2 = int(rest[3])
        except ValueError:
            err(NAME, f"invalid skip: {rest[3]}")
            return 2

    try:
        h1 = sys.stdin.buffer if f1 == "-" else open(f1, "rb")
    except OSError as e:
        err_path(NAME, f1, e)
        return 2
    try:
        h2 = sys.stdin.buffer if f2 == "-" else open(f2, "rb")
    except OSError as e:
        if h1 is not sys.stdin.buffer:
            h1.close()
        err_path(NAME, f2, e)
        return 2

    try:
        if skip1:
            h1.read(skip1)
        if skip2:
            h2.read(skip2)
        offset = 0
        line = 1
        differ = False
        while True:
            if bytes_limit is not None and offset >= bytes_limit:
                break
            b1 = h1.read(1)
            b2 = h2.read(1)
            if not b1 and not b2:
                break
            if not b1:
                if not silent:
                    err(NAME, f"EOF on {f1} after byte {offset}")
                return 1
            if not b2:
                if not silent:
                    err(NAME, f"EOF on {f2} after byte {offset}")
                return 1
            if b1 != b2:
                differ = True
                if silent:
                    return 1
                if print_all:
                    sys.stdout.write(f"{offset + 1} {b1[0]:>3o} {b2[0]:>3o}\n")
                else:
                    if print_chars:
                        sys.stdout.write(
                            f"{f1} {f2} differ: byte {offset + 1}, line {line} is "
                            f"{b1[0]:>3o} {chr(b1[0]) if 32 <= b1[0] < 127 else '.'} "
                            f"{b2[0]:>3o} {chr(b2[0]) if 32 <= b2[0] < 127 else '.'}\n"
                        )
                    else:
                        sys.stdout.write(
                            f"{f1} {f2} differ: byte {offset + 1}, line {line}\n"
                        )
                    return 1
            if b1 == b"\n":
                line += 1
            offset += 1
        if differ and print_all:
            return 1
        return 0
    finally:
        if h1 is not sys.stdin.buffer:
            h1.close()
        if h2 is not sys.stdin.buffer:
            h2.close()
