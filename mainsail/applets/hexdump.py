"""mainsail hexdump — canonical (and a few alt) hex dump formats."""
from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "hexdump"
ALIASES: list[str] = []
HELP = "ASCII, decimal, hexadecimal, octal dump"


def _printable(b: int) -> str:
    return chr(b) if 0x20 <= b < 0x7F else "."


def _canonical(data: bytes, offset: int = 0) -> str:
    out: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        # Pad hex to 47 cols (16 bytes × 3 chars - 1 = 47)
        # Actually the canonical layout is "xx xx xx xx xx xx xx xx  xx xx xx xx xx xx xx xx"
        # — 8 bytes, 2-space, 8 bytes, then |..ascii..|
        first8 = " ".join(f"{b:02x}" for b in chunk[:8])
        second8 = " ".join(f"{b:02x}" for b in chunk[8:16])
        hex_field = f"{first8:<23}  {second8:<23}".rstrip()
        # But we need fixed-width alignment
        hex_field = (first8 + "  " + second8).ljust(48)
        ascii_part = "".join(_printable(b) for b in chunk)
        out.append(f"{offset + i:08x}  {hex_field}  |{ascii_part}|")
    out.append(f"{offset + len(data):08x}")
    return "\n".join(out) + "\n"


def _two_byte_hex(data: bytes, offset: int = 0) -> str:
    """Default hexdump output: 16 bytes per line, grouped as 2-byte words."""
    out: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        words: list[str] = []
        for j in range(0, len(chunk), 2):
            if j + 1 < len(chunk):
                # Little-endian word display, like real hexdump
                w = chunk[j] | (chunk[j + 1] << 8)
                words.append(f"{w:04x}")
            else:
                words.append(f"{chunk[j]:02x}")
        out.append(f"{offset + i:07x} " + " ".join(words))
    out.append(f"{offset + len(data):07x}")
    return "\n".join(out) + "\n"


def _decimal(data: bytes, offset: int = 0) -> str:
    out: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        words: list[str] = []
        for j in range(0, len(chunk), 2):
            if j + 1 < len(chunk):
                w = chunk[j] | (chunk[j + 1] << 8)
                words.append(f"{w:5d}")
            else:
                words.append(f"  {chunk[j]:3d}")
        out.append(f"{offset + i:07x} " + " ".join(words))
    out.append(f"{offset + len(data):07x}")
    return "\n".join(out) + "\n"


def _one_byte_hex(data: bytes, offset: int = 0) -> str:
    out: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        out.append(f"{offset + i:07x} " + " ".join(f"{b:02x}" for b in chunk))
    out.append(f"{offset + len(data):07x}")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    args = argv[1:]
    fmt = "default"  # default | canonical | C | b | d
    no_squeeze = True  # -v: don't collapse repeated rows. Default IS to squeeze.
    skip = 0
    length: int | None = None

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
        if a == "-C" or a == "--canonical":
            fmt = "canonical"
            i += 1
            continue
        if a == "-b":
            fmt = "octal_byte"
            i += 1
            continue
        if a == "-c":
            fmt = "char"
            i += 1
            continue
        if a == "-d":
            fmt = "decimal"
            i += 1
            continue
        if a == "-x":
            fmt = "default"
            i += 1
            continue
        if a == "-o":
            fmt = "octal_word"
            i += 1
            continue
        if a == "-v":
            no_squeeze = True
            i += 1
            continue
        if a in {"-s", "--skip"} and i + 1 < len(args):
            try:
                skip = int(args[i + 1], 0)
            except ValueError:
                err(NAME, f"invalid skip: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-n", "--length"} and i + 1 < len(args):
            try:
                length = int(args[i + 1], 0)
            except ValueError:
                err(NAME, f"invalid length: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0
    all_data = bytearray()

    for f in files:
        try:
            if f == "-":
                buf = sys.stdin.buffer.read()
            else:
                with open(f, "rb") as fh:
                    buf = fh.read()
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        all_data.extend(buf)

    data = bytes(all_data)
    if skip:
        data = data[skip:]
    if length is not None:
        data = data[:length]

    if fmt == "canonical":
        sys.stdout.write(_canonical(data, skip))
    elif fmt == "decimal":
        sys.stdout.write(_decimal(data, skip))
    elif fmt == "octal_byte":
        out: list[str] = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            out.append(f"{skip + i:07o} " + " ".join(f"{b:03o}" for b in chunk))
        out.append(f"{skip + len(data):07o}")
        sys.stdout.write("\n".join(out) + "\n")
    elif fmt == "octal_word":
        out_o: list[str] = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            words: list[str] = []
            for j in range(0, len(chunk), 2):
                if j + 1 < len(chunk):
                    w = chunk[j] | (chunk[j + 1] << 8)
                    words.append(f"{w:06o}")
                else:
                    words.append(f"{chunk[j]:03o}")
            out_o.append(f"{skip + i:07o} " + " ".join(words))
        out_o.append(f"{skip + len(data):07o}")
        sys.stdout.write("\n".join(out_o) + "\n")
    elif fmt == "char":
        out_c: list[str] = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            cells: list[str] = []
            for b in chunk:
                if 0x20 <= b < 0x7F:
                    cells.append(f"  {chr(b)}")
                else:
                    special = {0: "\\0", 7: "\\a", 8: "\\b", 9: "\\t",
                               10: "\\n", 11: "\\v", 12: "\\f", 13: "\\r"}
                    cells.append(special.get(b, f"{b:03o}").rjust(3))
            out_c.append(f"{skip + i:07x} " + " ".join(cells))
        out_c.append(f"{skip + len(data):07x}")
        sys.stdout.write("\n".join(out_c) + "\n")
    else:
        sys.stdout.write(_two_byte_hex(data, skip))

    sys.stdout.flush()
    return rc
