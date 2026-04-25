from __future__ import annotations

import sys
from pathlib import Path

from mainsail.common import err, err_path

NAME = "split"
ALIASES: list[str] = []
HELP = "split a file into pieces"


def _parse_size(s: str) -> int | None:
    if not s:
        return None
    last = s[-1]
    mult = 1
    if last in "KMGTPkmgtp":
        mult = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3,
                "T": 1024 ** 4, "P": 1024 ** 5}[last.upper()]
        s = s[:-1]
    elif last in "Bb":
        # 'b' is 512 bytes (POSIX), 'B' is also 512 — keep simple.
        mult = 512
        s = s[:-1]
    try:
        return int(s) * mult
    except ValueError:
        return None


def _suffix(n: int, length: int) -> str:
    """Generate the n-th suffix in alphabetic sequence: aa, ab, ..., az, ba ...

    For length=2 this matches GNU split's default `aa..zz` numbering.
    """
    out = []
    for _ in range(length):
        out.append(chr(ord("a") + n % 26))
        n //= 26
    return "".join(reversed(out))


def main(argv: list[str]) -> int:
    args = argv[1:]
    lines: int | None = None
    bytes_per: int | None = None
    suffix_length = 2
    additional_suffix = ""
    numeric = False
    prefix = "x"
    in_file: str | None = None

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
        if a in {"-l", "--lines"} and i + 1 < len(args):
            try:
                lines = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid number of lines: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a.startswith("-l"):
            try:
                lines = int(a[2:])
                i += 1
                continue
            except ValueError:
                pass
        if a in {"-b", "--bytes"} and i + 1 < len(args):
            v = _parse_size(args[i + 1])
            if v is None:
                err(NAME, f"invalid byte count: {args[i + 1]}")
                return 2
            bytes_per = v
            i += 2
            continue
        if a in {"-a", "--suffix-length"} and i + 1 < len(args):
            try:
                suffix_length = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid suffix length: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-d", "--numeric-suffixes"}:
            numeric = True
            i += 1
            continue
        if a == "--additional-suffix" and i + 1 < len(args):
            additional_suffix = args[i + 1]
            i += 2
            continue
        if a.startswith("--additional-suffix="):
            additional_suffix = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1 and not a[1:].isdigit():
            err(NAME, f"unknown option: {a}")
            return 2
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            lines = int(a[1:])
            i += 1
            continue
        break

    rest = args[i:]
    if rest:
        in_file = rest[0]
        if len(rest) > 1:
            prefix = rest[1]

    if lines is None and bytes_per is None:
        lines = 1000  # GNU default

    try:
        if in_file is None or in_file == "-":
            data = sys.stdin.buffer.read()
        else:
            with open(in_file, "rb") as fh:
                data = fh.read()
    except OSError as e:
        err_path(NAME, in_file or "-", e)
        return 1

    chunks: list[bytes] = []
    if bytes_per is not None:
        for j in range(0, len(data), bytes_per):
            chunks.append(data[j:j + bytes_per])
    else:
        # Line-based: split on \n keeping the newline with the line.
        cur = bytearray()
        line_count = 0
        for byte in data:
            cur.append(byte)
            if byte == 0x0A:
                line_count += 1
                if line_count >= lines:
                    chunks.append(bytes(cur))
                    cur = bytearray()
                    line_count = 0
        if cur:
            chunks.append(bytes(cur))

    rc = 0
    for idx, chunk in enumerate(chunks):
        if numeric:
            suf = str(idx).rjust(suffix_length, "0")
        else:
            suf = _suffix(idx, suffix_length)
        out = f"{prefix}{suf}{additional_suffix}"
        try:
            with open(out, "wb") as fh:
                fh.write(chunk)
        except OSError as e:
            err_path(NAME, out, e)
            rc = 1

    return rc
