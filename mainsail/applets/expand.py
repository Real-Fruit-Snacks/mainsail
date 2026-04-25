from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "expand"
ALIASES: list[str] = []
HELP = "convert tabs to spaces"


def _parse_tabs(spec: str) -> list[int]:
    parts = [p for p in spec.replace(" ", ",").split(",") if p]
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            return []
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    tabs = [8]
    initial_only = False

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
        if a in {"-i", "--initial"}:
            initial_only = True
            i += 1
            continue
        if a in {"-t", "--tabs"} and i + 1 < len(args):
            t = _parse_tabs(args[i + 1])
            if not t:
                err(NAME, f"invalid tabs: {args[i + 1]}")
                return 2
            tabs = t
            i += 2
            continue
        if a.startswith("-t"):
            t = _parse_tabs(a[2:])
            if not t:
                err(NAME, f"invalid tabs: {a[2:]}")
                return 2
            tabs = t
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            tabs = [int(a[1:])]
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0

    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        try:
            for line in fh:
                trailing = ""
                if line.endswith("\r\n"):
                    line, trailing = line[:-2], "\r\n"
                elif line.endswith("\n"):
                    line, trailing = line[:-1], "\n"
                col = 0
                seen_non_blank = False
                out = []
                for ch in line:
                    if ch == "\t":
                        if initial_only and seen_non_blank:
                            out.append("\t")
                            col += 1
                            continue
                        # Compute next tab stop based on current col.
                        if len(tabs) == 1:
                            step = tabs[0]
                            n = step - (col % step)
                        else:
                            # multi-stop: find next stop > col
                            stop = next((t for t in tabs if t > col), None)
                            if stop is None:
                                # past last stop: just one space
                                n = 1
                            else:
                                n = stop - col
                        out.append(" " * n)
                        col += n
                    else:
                        out.append(ch)
                        col += 1
                        if ch != " ":
                            seen_non_blank = True
                sys.stdout.write("".join(out) + trailing)
        finally:
            if f != "-":
                fh.close()
        sys.stdout.flush()

    return rc
