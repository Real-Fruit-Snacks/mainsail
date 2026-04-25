from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "unexpand"
ALIASES: list[str] = []
HELP = "convert spaces to tabs"


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
    all_blanks = False  # default: only convert leading blanks

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
        if a in {"-a", "--all"}:
            all_blanks = True
            i += 1
            continue
        if a == "--first-only":
            all_blanks = False
            i += 1
            continue
        if a in {"-t", "--tabs"} and i + 1 < len(args):
            t = _parse_tabs(args[i + 1])
            if not t:
                err(NAME, f"invalid tabs: {args[i + 1]}")
                return 2
            tabs = t
            all_blanks = True  # GNU: -t implies -a
            i += 2
            continue
        if a.startswith("-t"):
            t = _parse_tabs(a[2:])
            if not t:
                err(NAME, f"invalid tabs: {a[2:]}")
                return 2
            tabs = t
            all_blanks = True
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0
    step = tabs[0] if len(tabs) == 1 else 0  # 0 means multi-stop mode

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
                out = _convert(line, tabs, step, all_blanks)
                sys.stdout.write(out + trailing)
        finally:
            if f != "-":
                fh.close()
        sys.stdout.flush()
    return rc


def _convert(line: str, tabs: list[int], step: int, all_blanks: bool) -> str:
    """Replace runs of spaces that align to tab stops with TABs."""
    # Walk char-by-char, keeping a buffer of consecutive spaces.
    out: list[str] = []
    col = 0
    pending_spaces = 0
    seen_non_blank = False
    for ch in line:
        if ch == " ":
            pending_spaces += 1
            continue
        # Flush pending spaces, possibly converting some to a tab.
        if pending_spaces:
            if not seen_non_blank or all_blanks:
                out.extend(_compact_spaces(col, pending_spaces, tabs, step))
            else:
                out.append(" " * pending_spaces)
            col += pending_spaces
            pending_spaces = 0
        out.append(ch)
        col += 1
        if ch != "\t":
            seen_non_blank = True
        if ch == "\t":
            # Tab advances col to next stop
            if step:
                col = ((col + step) // step) * step if step else col
                # already counted +1; subtract because we want to set col to stop
                col -= 1
                col = ((col // step) + 1) * step
            else:
                stop = next((t for t in tabs if t > col), None)
                col = stop if stop is not None else col + 1
    # Trailing spaces
    if pending_spaces:
        if not seen_non_blank or all_blanks:
            out.extend(_compact_spaces(col, pending_spaces, tabs, step))
        else:
            out.append(" " * pending_spaces)
    return "".join(out)


def _compact_spaces(start_col: int, count: int, tabs: list[int], step: int) -> list[str]:
    """Return a list of strings (tabs and spaces) that, starting at start_col,
    advance the column by `count` positions, using TABs when they align."""
    out: list[str] = []
    col = start_col
    remaining = count
    while remaining > 0:
        # Find next tab stop strictly greater than col.
        if step:
            next_stop = ((col // step) + 1) * step
        else:
            next_stop = next((t for t in tabs if t > col), None)
            if next_stop is None:
                next_stop = col + remaining  # no more stops; emit literal spaces
        gap = next_stop - col
        if gap <= remaining:
            out.append("\t")
            remaining -= gap
            col = next_stop
        else:
            out.append(" " * remaining)
            col += remaining
            remaining = 0
    return out
