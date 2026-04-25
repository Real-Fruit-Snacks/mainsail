"""mainsail od — octal/hex/decimal/character dump."""
from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "od"
ALIASES: list[str] = []
HELP = "dump files in octal and other formats"


_ESCAPES = {0: "\\0", 7: "\\a", 8: "\\b", 9: "\\t", 10: "\\n",
            11: "\\v", 12: "\\f", 13: "\\r"}


def _format_byte_oct(b: int) -> str: return f"{b:03o}"
def _format_byte_hex(b: int) -> str: return f"{b:02x}"
def _format_byte_dec(b: int) -> str: return f"{b:3d}"
def _format_byte_chr(b: int) -> str:
    if b in _ESCAPES: return _ESCAPES[b].rjust(3)
    if 0x20 <= b < 0x7F: return f"  {chr(b)}"
    return f"{b:03o}"


_FORMATTERS = {
    "o": (_format_byte_oct, 1),  # 1-byte octal
    "x": (_format_byte_hex, 1),  # 1-byte hex
    "d": (_format_byte_dec, 1),  # 1-byte decimal
    "c": (_format_byte_chr, 1),  # character
}


def main(argv: list[str]) -> int:
    args = argv[1:]
    fmt_letter = "o"  # default = octal
    width = 16
    address_radix = "o"  # default address in octal
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
        if a in {"-c"}: fmt_letter = "c"; i += 1; continue
        if a in {"-d"}: fmt_letter = "d"; i += 1; continue
        if a in {"-o"}: fmt_letter = "o"; i += 1; continue
        if a in {"-x"}: fmt_letter = "x"; i += 1; continue
        if a in {"-b"}: fmt_letter = "o"; i += 1; continue  # backward-compat
        if a in {"-A", "--address-radix"} and i + 1 < len(args):
            r = args[i + 1]
            if r not in {"d", "o", "x", "n"}:
                err(NAME, f"invalid address radix: {r}")
                return 2
            address_radix = r
            i += 2
            continue
        if a.startswith("-A") and len(a) == 3 and a[2] in "doxn":
            # -An, -Ad, -Ax, -Ao
            address_radix = a[2]
            i += 1
            continue
        if a.startswith("--address-radix="):
            r = a.split("=", 1)[1]
            if r not in {"d", "o", "x", "n"}:
                err(NAME, f"invalid address radix: {r}")
                return 2
            address_radix = r
            i += 1
            continue
        if a in {"-w", "--width"} and i + 1 < len(args):
            try:
                width = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid width: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-N", "--read-bytes"} and i + 1 < len(args):
            try:
                length = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid length: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a in {"-j", "--skip-bytes"} and i + 1 < len(args):
            try:
                skip = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid skip: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a == "-v":
            i += 1; continue  # we never collapse anyway
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    all_data = bytearray()
    rc = 0
    for f in files:
        try:
            if f == "-":
                all_data.extend(sys.stdin.buffer.read())
            else:
                with open(f, "rb") as fh:
                    all_data.extend(fh.read())
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1

    data = bytes(all_data)
    if skip:
        data = data[skip:]
    if length is not None:
        data = data[:length]

    formatter, _bytes_per_field = _FORMATTERS[fmt_letter]
    out: list[str] = []
    offset = skip
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        if address_radix == "n":
            addr = ""
        elif address_radix == "d":
            addr = f"{offset + i:07d}"
        elif address_radix == "x":
            addr = f"{offset + i:07x}"
        else:
            addr = f"{offset + i:07o}"
        cells = " ".join(formatter(b) for b in chunk)
        out.append(f"{addr} {cells}".rstrip())

    if address_radix == "d":
        out.append(f"{offset + len(data):07d}")
    elif address_radix == "x":
        out.append(f"{offset + len(data):07x}")
    elif address_radix == "n":
        pass
    else:
        out.append(f"{offset + len(data):07o}")

    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()
    return rc
