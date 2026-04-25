from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "paste"
ALIASES: list[str] = []
HELP = "merge corresponding lines of files"


def main(argv: list[str]) -> int:
    args = argv[1:]
    delims = ["\t"]
    serial = False

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
        if a in {"-d", "--delimiters"} and i + 1 < len(args):
            d = args[i + 1]
            delims = list(d) if d else ["\t"]
            i += 2
            continue
        if a.startswith("-d") and len(a) > 2:
            d = a[2:]
            delims = list(d) if d else ["\t"]
            i += 1
            continue
        if a in {"-s", "--serial"}:
            serial = True
            i += 1
            continue
        if a == "-z" or a == "--zero-terminated":
            err(NAME, "-z is not supported")
            return 2
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]

    # Open all files (or stdin) — use list of file handles, replacing exhausted
    # ones with None so we can keep iterating until all are done.
    handles: list = []
    for f in files:
        try:
            if f == "-":
                handles.append(sys.stdin)
            else:
                handles.append(open(f, "r", encoding="utf-8", errors="replace"))
        except OSError as e:
            err_path(NAME, f, e)
            for h in handles:
                if h is not sys.stdin:
                    h.close()
            return 1

    rc = 0
    try:
        if serial:
            # Concatenate lines of each file, separated by delim cycle, one
            # output line per input file.
            for h in handles:
                lines = []
                for line in h:
                    lines.append(line.rstrip("\r\n"))
                if lines:
                    sys.stdout.write(_join_with_delims(lines, delims) + "\n")
        else:
            # Round-robin: read one line from each file in lockstep.
            done = [False] * len(handles)
            while not all(done):
                row: list[str] = []
                any_data = False
                for idx, h in enumerate(handles):
                    if done[idx]:
                        row.append("")
                        continue
                    line = h.readline()
                    if not line:
                        done[idx] = True
                        row.append("")
                        continue
                    any_data = True
                    row.append(line.rstrip("\r\n"))
                if not any_data:
                    break
                sys.stdout.write(_join_with_delims(row, delims) + "\n")
    except OSError as e:
        err(NAME, str(e))
        rc = 1
    finally:
        for h in handles:
            if h is not sys.stdin:
                h.close()

    sys.stdout.flush()
    return rc


def _join_with_delims(parts: list[str], delims: list[str]) -> str:
    out = parts[0]
    for j, p in enumerate(parts[1:]):
        out += delims[j % len(delims)] + p
    return out
