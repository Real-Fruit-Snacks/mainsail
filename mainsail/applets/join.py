"""mainsail join — relational join of two pre-sorted files."""
from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "join"
ALIASES: list[str] = []
HELP = "join lines of two files on a common field"


def _split(line: str, sep: str | None) -> list[str]:
    return line.split(sep) if sep is not None else line.split()


def main(argv: list[str]) -> int:
    args = argv[1:]
    field1 = 1   # 1-based
    field2 = 1
    sep: str | None = None  # default: split on runs of whitespace
    out_sep = " "
    print_unpaired1 = False
    print_unpaired2 = False
    fmt: list[tuple[int, int]] = []  # explicit -o list
    empty_field = ""
    case_insensitive = False
    suppress_paired = False

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
        if a == "-1" and i + 1 < len(args):
            try:
                field1 = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid field: {args[i + 1]}")
                return 2
            i += 2; continue
        if a == "-2" and i + 1 < len(args):
            try:
                field2 = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid field: {args[i + 1]}")
                return 2
            i += 2; continue
        if a == "-j" and i + 1 < len(args):
            try:
                field1 = field2 = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid field: {args[i + 1]}")
                return 2
            i += 2; continue
        if a == "-t" and i + 1 < len(args):
            sep = args[i + 1]
            out_sep = sep
            i += 2; continue
        if a == "-a" and i + 1 < len(args):
            n = args[i + 1]
            if n == "1": print_unpaired1 = True
            elif n == "2": print_unpaired2 = True
            else:
                err(NAME, f"invalid -a value: {n}")
                return 2
            i += 2; continue
        if a == "-e" and i + 1 < len(args):
            empty_field = args[i + 1]
            i += 2; continue
        if a == "-i" or a == "--ignore-case":
            case_insensitive = True
            i += 1; continue
        if a == "-v" and i + 1 < len(args):
            n = args[i + 1]
            suppress_paired = True
            if n == "1": print_unpaired1 = True
            elif n == "2": print_unpaired2 = True
            i += 2; continue
        if a == "-o" and i + 1 < len(args):
            spec = args[i + 1]
            for piece in spec.replace(" ", ",").split(","):
                if "." not in piece:
                    err(NAME, f"invalid -o spec: {piece}")
                    return 2
                f, num = piece.split(".", 1)
                try:
                    fmt.append((int(f), int(num)))
                except ValueError:
                    err(NAME, f"invalid -o spec: {piece}")
                    return 2
            i += 2; continue
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

    def _norm_key(k: str) -> str:
        return k.lower() if case_insensitive else k

    def _read(h):
        line = h.readline()
        if not line:
            return None
        return line.rstrip("\r\n")

    rc = 0
    try:
        a_line = _read(h1)
        b_line = _read(h2)
        while a_line is not None or b_line is not None:
            if a_line is None:
                if print_unpaired2:
                    sys.stdout.write(_emit_solo(b_line, sep, out_sep, fmt, 2, field2, empty_field))
                b_line = _read(h2)
                continue
            if b_line is None:
                if print_unpaired1:
                    sys.stdout.write(_emit_solo(a_line, sep, out_sep, fmt, 1, field1, empty_field))
                a_line = _read(h1)
                continue
            a_fields = _split(a_line, sep)
            b_fields = _split(b_line, sep)
            ka = _norm_key(a_fields[field1 - 1] if field1 - 1 < len(a_fields) else "")
            kb = _norm_key(b_fields[field2 - 1] if field2 - 1 < len(b_fields) else "")
            if ka == kb:
                if not suppress_paired:
                    sys.stdout.write(_emit_paired(a_fields, b_fields, ka, out_sep, fmt, field1, field2, empty_field))
                # advance both; group consumption (cross-product on duplicates)
                # is approximated by single-line pairing here
                a_line = _read(h1)
                b_line = _read(h2)
            elif ka < kb:
                if print_unpaired1:
                    sys.stdout.write(_emit_solo(a_line, sep, out_sep, fmt, 1, field1, empty_field))
                a_line = _read(h1)
            else:
                if print_unpaired2:
                    sys.stdout.write(_emit_solo(b_line, sep, out_sep, fmt, 2, field2, empty_field))
                b_line = _read(h2)
    finally:
        if h1 is not sys.stdin: h1.close()
        if h2 is not sys.stdin: h2.close()

    sys.stdout.flush()
    return rc


def _emit_paired(af: list[str], bf: list[str], key: str, out_sep: str,
                 fmt: list[tuple[int, int]], field1: int, field2: int,
                 empty: str) -> str:
    if fmt:
        out = []
        for src, num in fmt:
            fields = af if src == 1 else bf
            try:
                out.append(fields[num - 1])
            except IndexError:
                out.append(empty)
        return out_sep.join(out) + "\n"
    # default: key, then non-key fields of file 1, then non-key fields of file 2
    out = [key]
    out.extend(f for j, f in enumerate(af) if j != field1 - 1)
    out.extend(f for j, f in enumerate(bf) if j != field2 - 1)
    return out_sep.join(out) + "\n"


def _emit_solo(line: str, sep: str | None, out_sep: str,
               fmt: list[tuple[int, int]], src: int, field: int,
               empty: str) -> str:
    fields = _split(line, sep)
    if fmt:
        out = []
        for s, num in fmt:
            if s == src:
                try:
                    out.append(fields[num - 1])
                except IndexError:
                    out.append(empty)
            else:
                out.append(empty)
        return out_sep.join(out) + "\n"
    # default: line as-is but using out_sep
    return out_sep.join(fields) + "\n"
