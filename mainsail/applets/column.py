"""mainsail column — format input as table or columns."""
from __future__ import annotations

import os
import sys

from mainsail.common import err, err_path

NAME = "column"
ALIASES: list[str] = []
HELP = "format input into multiple columns"


def main(argv: list[str]) -> int:
    args = argv[1:]
    table_mode = False
    in_sep: str | None = None  # None = whitespace
    out_sep = "  "
    fill_rows = False  # -x: rows first instead of columns first

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-t", "--table"}:
            table_mode = True
            i += 1; continue
        if a in {"-s", "--separator"} and i + 1 < len(args):
            in_sep = args[i + 1]
            i += 2; continue
        if a in {"-o", "--output-separator"} and i + 1 < len(args):
            out_sep = args[i + 1]
            i += 2; continue
        if a in {"-x", "--fillrows"}:
            fill_rows = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    lines: list[str] = []
    rc = 0

    for f in files:
        try:
            if f == "-":
                lines.extend(sys.stdin.read().splitlines())
            else:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    lines.extend(fh.read().splitlines())
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1

    # Drop trailing empty line(s)
    while lines and lines[-1] == "":
        lines.pop()

    if not lines:
        return rc

    if table_mode:
        rows = [_split_row(line, in_sep) for line in lines]
        if not rows:
            return rc
        widths = [0] * max(len(r) for r in rows)
        for row in rows:
            for j, cell in enumerate(row):
                widths[j] = max(widths[j], len(cell))
        for row in rows:
            cells = []
            for j, cell in enumerate(row):
                if j < len(row) - 1:
                    cells.append(cell.ljust(widths[j]))
                else:
                    cells.append(cell)
            sys.stdout.write(out_sep.join(cells).rstrip() + "\n")
    else:
        # Columnar (non-table) output: arrange entries to fit terminal width.
        try:
            term_w = os.get_terminal_size().columns
        except OSError:
            term_w = 80
        items = lines
        max_w = max(len(s) for s in items)
        col_w = max_w + 2
        cols = max(1, term_w // col_w)
        rows = (len(items) + cols - 1) // cols
        if fill_rows:
            for r in range(rows):
                row_cells = items[r * cols:(r + 1) * cols]
                sys.stdout.write("".join(c.ljust(col_w) for c in row_cells).rstrip() + "\n")
        else:
            for r in range(rows):
                row_cells = []
                for c in range(cols):
                    idx = c * rows + r
                    if idx < len(items):
                        row_cells.append(items[idx].ljust(col_w))
                sys.stdout.write("".join(row_cells).rstrip() + "\n")
    sys.stdout.flush()
    return rc


def _split_row(line: str, sep: str | None) -> list[str]:
    if sep is None:
        return line.split()
    if len(sep) == 1:
        return line.split(sep)
    # Multi-char: split on any of the chars (column -s "; ")
    out = [""]
    for ch in line:
        if ch in sep:
            out.append("")
        else:
            out[-1] += ch
    return out
