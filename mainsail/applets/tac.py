from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "tac"
ALIASES: list[str] = []
HELP = "concatenate and print files in reverse"


def main(argv: list[str]) -> int:
    args = argv[1:]
    sep = "\n"
    before = False  # default: separator at line end
    regex_mode = False  # not implemented; flag accepted for compat

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a in {"-b", "--before"}:
            before = True
            i += 1
            continue
        if a == "-s" or a.startswith("--separator"):
            if a == "-s" and i + 1 < len(args):
                sep = args[i + 1]
                i += 2
                continue
            if "=" in a:
                sep = a.split("=", 1)[1]
                i += 1
                continue
            err(NAME, "-s requires an argument")
            return 2
        if a in {"-r", "--regex"}:
            regex_mode = True
            i += 1
            continue
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0

    for f in files:
        try:
            if f == "-":
                data = sys.stdin.buffer.read()
            else:
                with open(f, "rb") as fh:
                    data = fh.read()
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue

        sep_b = sep.encode("utf-8")
        if not data:
            continue
        # Split keeping separators logically.
        parts = data.split(sep_b)
        # If data ends with sep, last element is "" — drop it so we don't emit
        # a phantom empty record before reversal.
        trailing = data.endswith(sep_b)
        if trailing and parts and parts[-1] == b"":
            parts.pop()
        if before:
            # Separator precedes each record (default GNU `tac -b`).
            out = b"".join(sep_b + p for p in reversed(parts))
            # Strip the leading separator we added if input didn't start with one.
            if out.startswith(sep_b) and not data.startswith(sep_b):
                out = out[len(sep_b):]
        else:
            # Separator follows each record (GNU default).
            out = sep_b.join(reversed(parts))
            if trailing:
                out += sep_b
        try:
            sys.stdout.buffer.write(out)
            sys.stdout.flush()
        except OSError as e:
            err(NAME, str(e))
            rc = 1

    if regex_mode:
        # We accept -r for compat but don't compile a regex separator.
        # GNU tac defaults to literal separator anyway; -r is rarely used.
        pass

    return rc
