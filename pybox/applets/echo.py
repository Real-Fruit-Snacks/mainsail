from __future__ import annotations

import sys

NAME = "echo"
ALIASES: list[str] = []
HELP = "display a line of text"

_ESCAPES = {
    "\\": "\\",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "0": "\0",
}


def _interpret(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            mapped = _ESCAPES.get(s[i + 1])
            if mapped is not None:
                out.append(mapped)
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def main(argv: list[str]) -> int:
    args = argv[1:]
    newline = True
    interpret = False

    while args and args[0].startswith("-") and len(args[0]) > 1 and args[0] != "--":
        flag = args[0]
        if not set(flag[1:]).issubset({"n", "e", "E"}):
            break
        for ch in flag[1:]:
            if ch == "n":
                newline = False
            elif ch == "e":
                interpret = True
            elif ch == "E":
                interpret = False
        args = args[1:]

    text = " ".join(args)
    if interpret:
        text = _interpret(text)

    sys.stdout.write(text)
    if newline:
        sys.stdout.write("\n")
    return 0
