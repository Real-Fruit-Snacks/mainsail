from __future__ import annotations

import os
import stat as _stat
import sys
from datetime import datetime
from pathlib import Path

from mainsail.common import err, err_path, group_name, user_name

NAME = "stat"
ALIASES: list[str] = []
HELP = "display file or file system status"


def _type_string(mode: int) -> str:
    if _stat.S_ISREG(mode):
        return "regular file"
    if _stat.S_ISDIR(mode):
        return "directory"
    if _stat.S_ISLNK(mode):
        return "symbolic link"
    if _stat.S_ISCHR(mode):
        return "character special file"
    if _stat.S_ISBLK(mode):
        return "block special file"
    if _stat.S_ISFIFO(mode):
        return "fifo"
    if _stat.S_ISSOCK(mode):
        return "socket"
    return "unknown"


def _format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _apply_format(p: Path, st: os.stat_result, fmt: str) -> str:
    repl = {
        "n": str(p),
        "s": str(st.st_size),
        "a": f"{st.st_mode & 0o7777:o}",
        "A": _stat.filemode(st.st_mode),
        "u": str(st.st_uid),
        "U": user_name(st.st_uid),
        "g": str(st.st_gid),
        "G": group_name(st.st_gid),
        "F": _type_string(st.st_mode),
        "Y": str(int(st.st_mtime)),
        "X": str(int(st.st_atime)),
        "Z": str(int(st.st_ctime)),
        "y": _format_time(st.st_mtime),
        "x": _format_time(st.st_atime),
        "z": _format_time(st.st_ctime),
        "h": str(st.st_nlink),
        "i": str(st.st_ino),
        "%": "%",
    }
    out: list[str] = []
    i = 0
    while i < len(fmt):
        c = fmt[i]
        if c == "%" and i + 1 < len(fmt):
            key = fmt[i + 1]
            if key in repl:
                out.append(repl[key])
                i += 2
                continue
        if c == "\\" and i + 1 < len(fmt):
            esc = {"n": "\n", "t": "\t", "\\": "\\", "r": "\r"}.get(fmt[i + 1])
            if esc is not None:
                out.append(esc)
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def _default_output(p: Path, st: os.stat_result) -> str:
    lines = [
        f"  File: {p}",
        f"  Size: {st.st_size:<12}  Type: {_type_string(st.st_mode)}",
        f"  Mode: ({st.st_mode & 0o7777:04o}/{_stat.filemode(st.st_mode)})  "
        f"Uid: ({st.st_uid:>4}/{user_name(st.st_uid)})  "
        f"Gid: ({st.st_gid:>4}/{group_name(st.st_gid)})",
        f"Access: {_format_time(st.st_atime)}",
        f"Modify: {_format_time(st.st_mtime)}",
        f"Change: {_format_time(st.st_ctime)}",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = argv[1:]
    fmt: str | None = None
    terse = False
    dereference = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "-c" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
            continue
        if a.startswith("--format="):
            fmt = a[len("--format="):]
            i += 1
            continue
        if a == "-t" or a == "--terse":
            terse = True
            i += 1
            continue
        if a == "-L" or a == "--dereference":
            dereference = True
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        break

    paths = args[i:]
    if not paths:
        err(NAME, "missing operand")
        return 2

    rc = 0
    for path in paths:
        p = Path(path)
        try:
            st = p.stat() if dereference else p.lstat()
        except OSError as e:
            err_path(NAME, path, e)
            rc = 1
            continue
        if fmt is not None:
            sys.stdout.write(_apply_format(p, st, fmt) + "\n")
        elif terse:
            sys.stdout.write(
                f"{p} {st.st_size} {st.st_nlink} {st.st_mode:o} "
                f"{st.st_uid} {st.st_gid} {int(st.st_mtime)} "
                f"{int(st.st_atime)} {int(st.st_ctime)}\n"
            )
        else:
            sys.stdout.write(_default_output(p, st) + "\n")
    return rc
