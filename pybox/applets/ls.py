from __future__ import annotations

import os
import stat
import sys
from datetime import datetime
from pathlib import Path

from pybox.common import err, err_path, group_name, user_name

NAME = "ls"
ALIASES: list[str] = ["dir"]
HELP = "list directory contents"


def _format_long(p: Path, st: os.stat_result) -> str:
    mode = stat.filemode(st.st_mode)
    nlink = st.st_nlink
    usr = user_name(st.st_uid)
    grp = group_name(st.st_gid)
    size = st.st_size
    mtime = datetime.fromtimestamp(st.st_mtime)
    now = datetime.now()
    if abs((now - mtime).days) > 180:
        ts = mtime.strftime("%b %d  %Y")
    else:
        ts = mtime.strftime("%b %d %H:%M")
    name = p.name or str(p)
    return f"{mode} {nlink:>2} {usr} {grp} {size:>8} {ts} {name}"


def _entries(path: Path, show_all: bool) -> list[Path]:
    try:
        names = sorted(os.listdir(path))
    except OSError as e:
        err_path(NAME, str(path), e)
        return []
    if not show_all:
        names = [n for n in names if not n.startswith(".")]
    return [path / n for n in names]


def main(argv: list[str]) -> int:
    args = argv[1:]
    long_fmt = False
    show_all = False
    one_per_line = False
    recursive = False
    paths: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            paths.extend(args[i + 1:])
            break
        if a == "-" or not a.startswith("-") or len(a) < 2:
            paths.append(a)
        else:
            for ch in a[1:]:
                if ch == "l":
                    long_fmt = True
                elif ch == "a":
                    show_all = True
                elif ch == "1":
                    one_per_line = True
                elif ch == "R":
                    recursive = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
        i += 1

    if not paths:
        paths = ["."]

    rc = 0
    multi = len(paths) > 1 or recursive

    def list_one(root: Path, header: bool) -> None:
        nonlocal rc
        if header:
            sys.stdout.write(f"{root}:\n")
        try:
            st = root.lstat()
        except OSError as e:
            err_path(NAME, str(root), e)
            rc = 1
            return
        if not stat.S_ISDIR(st.st_mode):
            if long_fmt:
                sys.stdout.write(_format_long(root, st) + "\n")
            else:
                sys.stdout.write(str(root) + "\n")
            return

        entries = _entries(root, show_all)
        if long_fmt:
            for p in entries:
                try:
                    est = p.lstat()
                except OSError as e:
                    err_path(NAME, str(p), e)
                    rc = 1
                    continue
                sys.stdout.write(_format_long(p, est) + "\n")
        else:
            for p in entries:
                sys.stdout.write(p.name + "\n")

        if recursive:
            for p in entries:
                try:
                    if stat.S_ISDIR(p.lstat().st_mode):
                        sys.stdout.write("\n")
                        list_one(p, header=True)
                except OSError as e:
                    err_path(NAME, str(p), e)
                    rc = 1

    for idx, path in enumerate(paths):
        if multi and idx > 0:
            sys.stdout.write("\n")
        list_one(Path(path), header=multi)

    # Suppress unused var warning from _one_per_line in case user passes -1 (already default behavior)
    _ = one_per_line
    return rc
