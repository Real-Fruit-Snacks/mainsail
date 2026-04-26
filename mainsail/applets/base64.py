"""mainsail base64 — encode/decode base64."""
from __future__ import annotations

import base64 as _b64
import sys

from mainsail.common import err, err_path

NAME = "base64"
ALIASES: list[str] = []
HELP = "encode/decode base64 data"


def main(argv: list[str]) -> int:
    args = argv[1:]
    decode = False
    wrap = 76
    ignore_garbage = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-d", "--decode"}:
            decode = True
            i += 1; continue
        if a in {"-w", "--wrap"} and i + 1 < len(args):
            try:
                wrap = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid wrap: {args[i + 1]}")
                return 2
            if wrap < 0:
                err(NAME, f"wrap must be >= 0")
                return 2
            i += 2; continue
        if a.startswith("--wrap="):
            try:
                wrap = int(a.split("=", 1)[1])
            except ValueError:
                err(NAME, f"invalid wrap: {a}")
                return 2
            i += 1; continue
        if a in {"-i", "--ignore-garbage"}:
            ignore_garbage = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    if len(files) > 1:
        err(NAME, "extra operand")
        return 2

    src = files[0]
    try:
        if src == "-":
            data = sys.stdin.buffer.read()
        else:
            with open(src, "rb") as fh:
                data = fh.read()
    except OSError as e:
        err_path(NAME, src, e)
        return 1

    try:
        if decode:
            if ignore_garbage:
                # Keep only valid base64 alphabet characters.
                valid = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
                data = bytes(b for b in data if b in valid)
            else:
                # Strip whitespace and newlines (standard tolerant behavior).
                data = bytes(b for b in data if b not in (0x20, 0x09, 0x0A, 0x0D))
            try:
                out = _b64.b64decode(data, validate=not ignore_garbage)
            except (ValueError, _b64.binascii.Error) as e:
                err(NAME, f"invalid input: {e}")
                return 1
            sys.stdout.buffer.write(out)
        else:
            encoded = _b64.b64encode(data)
            if wrap == 0:
                sys.stdout.buffer.write(encoded)
            else:
                for j in range(0, len(encoded), wrap):
                    sys.stdout.buffer.write(encoded[j:j + wrap])
                    sys.stdout.buffer.write(b"\n")
                if not encoded:
                    sys.stdout.buffer.write(b"\n")
        sys.stdout.flush()
    except OSError as e:
        err(NAME, str(e))
        return 1

    return 0
