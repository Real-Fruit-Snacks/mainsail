from __future__ import annotations

import string
import sys

from mainsail.common import err

NAME = "tr"
ALIASES: list[str] = []
HELP = "translate, delete, or squeeze characters"

_ESCAPE = {
    "n": b"\n", "t": b"\t", "r": b"\r", "\\": b"\\",
    "0": b"\0", "a": b"\a", "b": b"\b", "f": b"\f", "v": b"\v",
}

_CLASSES: dict[str, bytes] = {
    "alpha": string.ascii_letters.encode("ascii"),
    "upper": string.ascii_uppercase.encode("ascii"),
    "lower": string.ascii_lowercase.encode("ascii"),
    "digit": string.digits.encode("ascii"),
    "alnum": (string.ascii_letters + string.digits).encode("ascii"),
    "space": string.whitespace.encode("ascii"),
    "blank": b" \t",
    "print": string.printable.encode("ascii"),
    "cntrl": bytes(list(range(32)) + [0x7f]),
    "punct": string.punctuation.encode("ascii"),
    "xdigit": string.hexdigits.encode("ascii"),
}


def _expand(s: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            mapped = _ESCAPE.get(s[i + 1])
            if mapped is not None:
                out.extend(mapped)
                i += 2
                continue
            out.append(ord(s[i + 1]))
            i += 2
            continue
        if c == "[" and i + 3 < len(s) and s[i + 1] == ":":
            end = s.find(":]", i + 2)
            if end != -1:
                cls = s[i + 2:end]
                if cls in _CLASSES:
                    out.extend(_CLASSES[cls])
                    i = end + 2
                    continue
        if i + 2 < len(s) and s[i + 1] == "-" and s[i + 2] != "]":
            a, b = ord(s[i]), ord(s[i + 2])
            if a <= b:
                out.extend(range(a, b + 1))
                i += 3
                continue
        out.append(ord(c))
        i += 1
    return bytes(out)


def main(argv: list[str]) -> int:
    args = argv[1:]
    delete = False
    squeeze = False
    complement = False
    truncate = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a.startswith("-") and len(a) > 1 and all(ch in "dscCt" for ch in a[1:]):
            for ch in a[1:]:
                if ch == "d":
                    delete = True
                elif ch == "s":
                    squeeze = True
                elif ch in ("c", "C"):
                    complement = True
                elif ch == "t":
                    truncate = True
            i += 1
        else:
            break

    positional = args[i:]
    if not positional:
        err(NAME, "missing operand")
        return 2
    if not delete and not squeeze and len(positional) < 2:
        err(NAME, "when not deleting or squeezing, two arguments are required")
        return 2

    set1 = _expand(positional[0])
    set2 = _expand(positional[1]) if len(positional) > 1 else b""

    data = sys.stdin.buffer.read()

    if delete:
        if complement:
            keep = set(set1)
            data = bytes(b for b in data if b in keep)
        else:
            remove = set(set1)
            data = bytes(b for b in data if b not in remove)
    elif len(positional) >= 2:
        # Translate mode
        src = set1
        dst = set2
        if truncate:
            src = src[:len(dst)]
        elif len(dst) < len(src):
            dst = dst + bytes([dst[-1]]) * (len(src) - len(dst))
        if complement:
            replacement = dst[-1]
            keep = set(src)
            data = bytes(b if b in keep else replacement for b in data)
        else:
            tbl = dict(zip(src, dst))
            data = bytes(tbl.get(b, b) for b in data)

    if squeeze:
        sq_bytes = set2 if (delete and set2) else set1
        sq_set = set(sq_bytes)
        if complement and not delete:
            sq_set = set(range(256)) - sq_set
        out = bytearray()
        prev = -1
        for b in data:
            if b == prev and b in sq_set:
                continue
            out.append(b)
            prev = b
        data = bytes(out)

    sys.stdout.buffer.write(data)
    sys.stdout.flush()
    return 0
