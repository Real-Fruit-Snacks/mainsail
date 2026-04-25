"""mainsail diff — line-by-line file comparison.

Default output is the unified diff. Implemented on top of stdlib
``difflib`` so the algorithm is solid; we just wrap arg parsing and
output formatting.

Exit codes match POSIX: 0 if identical, 1 if differ, 2 on error.
"""
from __future__ import annotations

import difflib
import os
import sys
import time

from mainsail.common import err, err_path

NAME = "diff"
ALIASES: list[str] = []
HELP = "compare files line by line"


def _read_lines(path: str, *, ignore_eol: bool = False) -> list[str]:
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    lines = text.splitlines(keepends=True)
    if ignore_eol:
        lines = [l.rstrip("\r\n") + "\n" if l.endswith(("\r\n", "\n")) else l
                 for l in lines]
    return lines


def _file_label(path: str) -> str:
    if path == "-":
        return "-"
    try:
        mtime = os.path.getmtime(path)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        return f"{path}\t{ts}"
    except OSError:
        return path


def main(argv: list[str]) -> int:
    args = argv[1:]
    mode = "unified"  # unified | context | normal | brief | side-by-side | ed
    context = 3
    ignore_case = False
    ignore_blank = False
    ignore_eol = False
    ignore_all_space = False
    brief = False

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
        if a in {"-u", "--unified"}:
            mode = "unified"
            i += 1; continue
        if a.startswith("-u") and a[2:].isdigit():
            mode = "unified"
            context = int(a[2:])
            i += 1; continue
        if a == "-U" and i + 1 < len(args):
            try:
                context = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid context: {args[i + 1]}")
                return 2
            mode = "unified"
            i += 2; continue
        if a in {"-c"}:
            mode = "context"
            i += 1; continue
        if a in {"-q", "--brief"}:
            brief = True
            i += 1; continue
        if a == "-y" or a == "--side-by-side":
            mode = "side-by-side"
            i += 1; continue
        if a == "-i" or a == "--ignore-case":
            ignore_case = True
            i += 1; continue
        if a == "-w" or a == "--ignore-all-space":
            ignore_all_space = True
            i += 1; continue
        if a == "-B" or a == "--ignore-blank-lines":
            ignore_blank = True
            i += 1; continue
        if a == "--strip-trailing-cr":
            ignore_eol = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    rest = args[i:]
    if len(rest) != 2:
        err(NAME, "two file arguments required")
        return 2
    a_path, b_path = rest

    try:
        a_lines = _read_lines(a_path, ignore_eol=ignore_eol)
    except OSError as e:
        err_path(NAME, a_path, e)
        return 2
    try:
        b_lines = _read_lines(b_path, ignore_eol=ignore_eol)
    except OSError as e:
        err_path(NAME, b_path, e)
        return 2

    def _norm(line: str) -> str:
        s = line
        if ignore_case:
            s = s.lower()
        if ignore_all_space:
            s = "".join(s.split())
        return s

    if ignore_case or ignore_all_space:
        a_cmp = [_norm(l) for l in a_lines]
        b_cmp = [_norm(l) for l in b_lines]
    else:
        a_cmp, b_cmp = a_lines, b_lines

    if ignore_blank:
        keep_a = [(idx, l) for idx, l in enumerate(a_lines) if l.strip()]
        keep_b = [(idx, l) for idx, l in enumerate(b_lines) if l.strip()]
        a_cmp = [_norm(l) for _, l in keep_a]
        b_cmp = [_norm(l) for _, l in keep_b]

    if a_cmp == b_cmp:
        return 0

    if brief:
        sys.stdout.write(f"Files {a_path} and {b_path} differ\n")
        return 1

    if mode == "unified":
        diff = difflib.unified_diff(
            a_lines, b_lines,
            fromfile=a_path, tofile=b_path,
            fromfiledate=_file_label(a_path).split("\t", 1)[1] if "\t" in _file_label(a_path) else "",
            tofiledate=_file_label(b_path).split("\t", 1)[1] if "\t" in _file_label(b_path) else "",
            n=context,
        )
        for _line in diff:
            sys.stdout.write(_line)
    elif mode == "context":
        diff = difflib.context_diff(
            a_lines, b_lines,
            fromfile=a_path, tofile=b_path, n=context,
        )
        for _line in diff:
            sys.stdout.write(_line)
    elif mode == "side-by-side":
        for line in difflib.ndiff(a_lines, b_lines):
            sys.stdout.write(line)
    else:
        diff = difflib.unified_diff(a_lines, b_lines, fromfile=a_path,
                                    tofile=b_path, n=context)
        for _line in diff:
            sys.stdout.write(_line)

    sys.stdout.flush()
    return 1
