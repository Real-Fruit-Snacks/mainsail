from __future__ import annotations

import os
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "du"
ALIASES: list[str] = []
HELP = "estimate file space usage"


def _format_human(n: int) -> str:
    units = ("", "K", "M", "G", "T", "P")
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if i == 0:
        return str(int(v))
    return f"{v:.1f}{units[i]}"


def _format_size(bytes_size: int, human: bool, bytes_exact: bool, block_size: int) -> str:
    if human:
        return _format_human(bytes_size)
    if bytes_exact:
        return str(bytes_size)
    return str((bytes_size + block_size - 1) // block_size)


def _depth(root: str, sub: str) -> int:
    try:
        rel = os.path.relpath(sub, root)
    except ValueError:
        return 0
    if rel == "." or rel == "":
        return 0
    return rel.count(os.sep) + rel.count("/") + (1 if rel and not (rel.count(os.sep) + rel.count("/")) else 0)


def main(argv: list[str]) -> int:
    args = argv[1:]
    summary = False
    all_files = False
    human = False
    bytes_exact = False
    max_depth: int | None = None
    grand_total = False
    block_size = 1024

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "--max-depth" and i + 1 < len(args):
            max_depth = int(args[i + 1])
            i += 2
            continue
        if a.startswith("--max-depth="):
            max_depth = int(a[len("--max-depth="):])
            i += 1
            continue
        if not a.startswith("-") or len(a) < 2 or a == "-":
            break
        if not all(ch in "sahbckm" for ch in a[1:]):
            err(NAME, f"invalid option: {a}")
            return 2
        for ch in a[1:]:
            if ch == "s":
                summary = True
            elif ch == "a":
                all_files = True
            elif ch == "h":
                human = True
            elif ch == "b":
                bytes_exact = True
            elif ch == "c":
                grand_total = True
            elif ch == "k":
                block_size = 1024
            elif ch == "m":
                block_size = 1024 * 1024
        i += 1

    paths = args[i:] or ["."]
    rc = 0
    running_total = 0

    def emit(size: int, path: str) -> None:
        sys.stdout.write(f"{_format_size(size, human, bytes_exact, block_size)}\t{path}\n")

    for arg in paths:
        root = Path(arg)
        try:
            st = root.lstat()
        except OSError as e:
            err_path(NAME, arg, e)
            rc = 1
            continue
        if not root.is_dir() or root.is_symlink():
            sz = st.st_size
            emit(sz, arg)
            running_total += sz
            continue

        # Walk bottom-up: children complete before their parents
        totals: dict[str, int] = {}
        for root_dir, dirs, files in os.walk(arg, topdown=False, followlinks=False):
            subtotal = 0
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    sz = os.lstat(fp).st_size
                except OSError as e:
                    err_path(NAME, fp, e)
                    rc = 1
                    continue
                subtotal += sz
                if all_files and not summary:
                    d = _depth(arg, fp)
                    if max_depth is None or d <= max_depth:
                        emit(sz, fp)
            for d in dirs:
                dp = os.path.join(root_dir, d)
                subtotal += totals.get(dp, 0)
            totals[root_dir] = subtotal
            if not summary:
                depth = _depth(arg, root_dir)
                if max_depth is None or depth <= max_depth:
                    emit(subtotal, root_dir)

        total = totals.get(str(root), totals.get(arg, 0))
        if summary:
            emit(total, arg)
        running_total += total

    if grand_total:
        emit(running_total, "total")
    return rc
