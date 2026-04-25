from __future__ import annotations

import os
import sys

from mainsail.common import err, err_path

NAME = "truncate"
ALIASES: list[str] = []
HELP = "shrink or extend the size of a file to the specified size"


def _parse_size(s: str) -> tuple[str, int] | None:
    """Return (op, abs_bytes). op is one of '=' '+' '-' '<' '>' '/' '%'.

    Multipliers: K M G T P (1024-based when appended); for SI (1000-based)
    GNU appends KB/MB/etc. We keep it simple — K=1024 always.
    """
    if not s:
        return None
    op = "="
    if s[0] in "+-<>/%":
        op = s[0]
        s = s[1:]
    if not s:
        return None
    mult = 1
    last = s[-1]
    if last in "KMGTPkmgtp":
        mult = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3,
                "T": 1024 ** 4, "P": 1024 ** 5}[last.upper()]
        s = s[:-1]
    try:
        n = int(s)
    except ValueError:
        return None
    return (op, n * mult)


def _new_size(op: str, val: int, current: int) -> int | None:
    if op == "=": return max(0, val)
    if op == "+": return current + val
    if op == "-": return max(0, current - val)
    if op == "<": return min(current, val)
    if op == ">": return max(current, val)
    if op == "/": return (current // val) * val if val else None
    if op == "%": return ((current + val - 1) // val) * val if val else None
    return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    size_arg: str | None = None
    reference: str | None = None
    no_create = False
    io_blocks = False  # accepted, no-op (we don't honor block size)

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
        if a in {"-s", "--size"} and i + 1 < len(args):
            size_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--size="):
            size_arg = a.split("=", 1)[1]
            i += 1
            continue
        if a == "-s" and i + 1 < len(args):
            size_arg = args[i + 1]
            i += 2
            continue
        if a in {"-r", "--reference"} and i + 1 < len(args):
            reference = args[i + 1]
            i += 2
            continue
        if a in {"-c", "--no-create"}:
            no_create = True
            i += 1
            continue
        if a in {"-o", "--io-blocks"}:
            io_blocks = True
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:]
    if not files:
        err(NAME, "missing FILE operand")
        return 2

    if size_arg is None and reference is None:
        err(NAME, "you must specify either '--size' or '--reference'")
        return 2

    parsed = None
    if size_arg is not None:
        parsed = _parse_size(size_arg)
        if parsed is None:
            err(NAME, f"invalid size: {size_arg}")
            return 2

    ref_size = 0
    if reference is not None:
        try:
            ref_size = os.path.getsize(reference)
        except OSError as e:
            err_path(NAME, reference, e)
            return 1

    rc = 0
    for f in files:
        exists = os.path.exists(f)
        if not exists and no_create:
            continue
        try:
            current = os.path.getsize(f) if exists else 0
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue

        if parsed is not None:
            op, val = parsed
            target = _new_size(op, val, current)
            if target is None:
                err(NAME, f"division by zero in size operator: {size_arg}")
                rc = 1
                continue
        else:
            target = ref_size

        try:
            # os.truncate creates the file if it doesn't exist? On POSIX it
            # doesn't; on Windows it doesn't either. We need to handle both.
            if not exists:
                with open(f, "wb"):
                    pass
            os.truncate(f, target)
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1

    return rc
