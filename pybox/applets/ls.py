from __future__ import annotations

import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

from pybox.common import err, err_path, group_name, user_name

NAME = "ls"
ALIASES: list[str] = ["dir"]
HELP = "list directory contents"


def _classify(st: os.stat_result) -> str:
    if stat.S_ISDIR(st.st_mode):
        return "/"
    if stat.S_ISLNK(st.st_mode):
        return "@"
    if stat.S_ISFIFO(st.st_mode):
        return "|"
    if stat.S_ISSOCK(st.st_mode):
        return "="
    if stat.S_ISREG(st.st_mode) and st.st_mode & 0o111:
        return "*"
    return ""


def _format_long(name: str, st: os.stat_result) -> str:
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
    return f"{mode} {nlink:>2} {usr} {grp} {size:>8} {ts} {name}"


def _format_columns(names: list[str], term_width: int) -> list[str]:
    if not names:
        return []
    max_width = max(len(n) for n in names) + 2
    cols = max(1, term_width // max_width)
    rows = -(-len(names) // cols)
    out: list[str] = []
    for r in range(rows):
        parts: list[str] = []
        for c in range(cols):
            idx = c * rows + r
            if idx < len(names):
                parts.append(names[idx].ljust(max_width))
        out.append("".join(parts).rstrip())
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    long_fmt = False
    show_all = False
    show_almost_all = False
    one_per_line = False
    recursive = False
    classify = False
    sort_size = False
    sort_time = False
    reverse = False
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
                elif ch == "A":
                    show_almost_all = True
                elif ch == "1":
                    one_per_line = True
                elif ch == "R":
                    recursive = True
                elif ch == "F":
                    classify = True
                elif ch == "S":
                    sort_size = True
                elif ch == "t":
                    sort_time = True
                elif ch == "r":
                    reverse = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
        i += 1

    if not paths:
        paths = ["."]

    try:
        term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    except OSError:
        term_width = 80
    is_tty = sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False

    use_long = long_fmt
    use_cols = (not long_fmt) and (not one_per_line) and is_tty
    need_stat = use_long or classify or sort_size or sort_time

    rc = 0
    multi = len(paths) > 1 or recursive

    def sort_key(entry: tuple[str, Path, os.stat_result | None]):
        _name, _path, st_e = entry
        if sort_size and st_e is not None:
            return -st_e.st_size
        if sort_time and st_e is not None:
            return -st_e.st_mtime
        return entry[0]

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

        # Single (non-directory) target
        if not stat.S_ISDIR(st.st_mode):
            name = root.name or str(root)
            suffix = _classify(st) if classify else ""
            if use_long:
                sys.stdout.write(_format_long(name + suffix, st) + "\n")
            else:
                sys.stdout.write(name + suffix + "\n")
            return

        try:
            raw_names = sorted(os.listdir(root))
        except OSError as e:
            err_path(NAME, str(root), e)
            rc = 1
            return
        if not (show_all or show_almost_all):
            raw_names = [n for n in raw_names if not n.startswith(".")]

        entries: list[tuple[str, Path, os.stat_result | None]] = []
        if show_all:
            entries.append((".", root, None))
            parent = root.parent if str(root.parent) != str(root) else root
            entries.append(("..", parent, None))
        entries.extend((n, root / n, None) for n in raw_names)

        if need_stat:
            enriched: list[tuple[str, Path, os.stat_result | None]] = []
            for name, path, _ in entries:
                try:
                    enriched.append((name, path, path.lstat()))
                except OSError as e:
                    err_path(NAME, str(path), e)
                    rc = 1
            entries = enriched

        entries.sort(key=sort_key)
        if reverse:
            entries.reverse()

        # Apply classify suffix to display names
        display_entries: list[tuple[str, Path, os.stat_result | None]] = []
        for name, path, st_e in entries:
            suffix = _classify(st_e) if (classify and st_e is not None) else ""
            display_entries.append((name + suffix, path, st_e))

        if use_long:
            for name, _p, st_e in display_entries:
                if st_e is None:
                    continue
                sys.stdout.write(_format_long(name, st_e) + "\n")
        elif use_cols:
            names_only = [d[0] for d in display_entries]
            for line in _format_columns(names_only, term_width):
                sys.stdout.write(line + "\n")
        else:
            for name, _p, _s in display_entries:
                sys.stdout.write(name + "\n")

        if recursive:
            for name, path, st_e in entries:
                if name in (".", ".."):
                    continue
                try:
                    mode = (st_e or path.lstat()).st_mode
                except OSError as e:
                    err_path(NAME, str(path), e)
                    rc = 1
                    continue
                if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
                    sys.stdout.write("\n")
                    list_one(path, header=True)

    for idx, path in enumerate(paths):
        if multi and idx > 0:
            sys.stdout.write("\n")
        list_one(Path(path), header=multi)

    return rc
