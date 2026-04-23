from __future__ import annotations

import fnmatch
import os
import stat
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "find"
ALIASES: list[str] = []
HELP = "search for files in a directory hierarchy"


def _parse_expr(tokens: list[str]) -> tuple[dict, int]:
    """Parse a restricted subset of find(1) expressions.

    Supported primaries:
      -name <glob>   match basename (case-sensitive)
      -iname <glob>  match basename (case-insensitive)
      -type f|d|l    filter by file type
      -maxdepth N    limit descent depth
      -mindepth N    min depth before matching
      -print         default action
    """
    expr: dict = {
        "name": None,
        "iname": None,
        "type": None,
        "maxdepth": None,
        "mindepth": 0,
    }
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "-name" and i + 1 < len(tokens):
            expr["name"] = tokens[i + 1]
            i += 2
        elif t == "-iname" and i + 1 < len(tokens):
            expr["iname"] = tokens[i + 1]
            i += 2
        elif t == "-type" and i + 1 < len(tokens):
            v = tokens[i + 1]
            if v not in ("f", "d", "l"):
                err(NAME, f"unknown -type: {v}")
                return expr, -1
            expr["type"] = v
            i += 2
        elif t == "-maxdepth" and i + 1 < len(tokens):
            expr["maxdepth"] = int(tokens[i + 1])
            i += 2
        elif t == "-mindepth" and i + 1 < len(tokens):
            expr["mindepth"] = int(tokens[i + 1])
            i += 2
        elif t == "-print":
            i += 1
        else:
            err(NAME, f"unknown predicate: {t}")
            return expr, -1
    return expr, 0


def _match(p: Path, depth: int, expr: dict) -> bool:
    if depth < expr["mindepth"]:
        return False
    try:
        st = p.lstat()
    except OSError:
        return False
    if expr["type"] == "f" and not stat.S_ISREG(st.st_mode):
        return False
    if expr["type"] == "d" and not stat.S_ISDIR(st.st_mode):
        return False
    if expr["type"] == "l" and not stat.S_ISLNK(st.st_mode):
        return False
    name = p.name
    if expr["name"] is not None and not fnmatch.fnmatchcase(name, expr["name"]):
        return False
    if expr["iname"] is not None and not fnmatch.fnmatchcase(name.lower(), expr["iname"].lower()):
        return False
    return True


def _walk(root: Path, expr: dict) -> int:
    rc = 0
    maxd = expr["maxdepth"]

    def visit(p: Path, depth: int) -> None:
        nonlocal rc
        if _match(p, depth, expr):
            sys.stdout.write(str(p) + "\n")
        if maxd is not None and depth >= maxd:
            return
        try:
            st = p.lstat()
        except OSError as e:
            err_path(NAME, str(p), e)
            rc = 1
            return
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return
        try:
            entries = sorted(os.listdir(p))
        except OSError as e:
            err_path(NAME, str(p), e)
            rc = 1
            return
        for entry in entries:
            visit(p / entry, depth + 1)

    visit(root, 0)
    return rc


def main(argv: list[str]) -> int:
    args = argv[1:]
    paths: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("-") and a != "-":
            break
        paths.append(a)
        i += 1
    if not paths:
        paths = ["."]

    expr, status = _parse_expr(args[i:])
    if status != 0:
        return 2

    rc = 0
    for p in paths:
        root = Path(p)
        if not root.exists() and not root.is_symlink():
            err_path(NAME, p, FileNotFoundError(2, "No such file or directory"))
            rc = 1
            continue
        if _walk(root, expr) != 0:
            rc = 1
    return rc
