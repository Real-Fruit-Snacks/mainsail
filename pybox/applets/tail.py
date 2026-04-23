from __future__ import annotations

import os
import sys
import time
from collections import deque

from pybox.common import err, err_path

NAME = "tail"
ALIASES: list[str] = []
HELP = "output the last part of files"


def _parse_count(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        return None


def _initial_tail(fh, bytes_mode: bool, byte_count: int, lines: int) -> None:
    if bytes_mode:
        data = fh.read()
        sys.stdout.buffer.write(data[-byte_count:] if byte_count > 0 else b"")
        return
    dq: deque[bytes] = deque(maxlen=lines)
    for raw in fh:
        dq.append(raw)
    for raw in dq:
        sys.stdout.buffer.write(raw)


def _follow(follow_files: list[str], multi: bool, sleep_interval: float) -> int:
    rc = 0
    handles: list[list] = []  # [path, fh, inode] per file
    for f in follow_files:
        try:
            fh = open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        fh.seek(0, 2)
        try:
            # st_ino is 0 on Windows for regular files, so rotation detection
            # effectively becomes a no-op there; we detect truncation instead.
            ino = os.fstat(fh.fileno()).st_ino
        except OSError:
            ino = 0
        handles.append([f, fh, ino])

    if not handles:
        return rc

    last_file = handles[-1][0]

    try:
        while True:
            any_data = False
            for entry in handles:
                f, fh, ino = entry
                # Detect truncation and rotation
                try:
                    st = os.stat(f)
                    pos = fh.tell()
                    if st.st_size < pos:
                        fh.seek(0)
                    if ino and st.st_ino and st.st_ino != ino:
                        fh.close()
                        fh = open(f, "rb")
                        entry[1] = fh
                        entry[2] = st.st_ino
                except OSError:
                    pass
                data = fh.read()
                if data:
                    if multi and last_file != f:
                        sys.stdout.write(f"\n==> {f} <==\n")
                        last_file = f
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
                    any_data = True
            if not any_data:
                time.sleep(sleep_interval)
    except KeyboardInterrupt:
        pass
    finally:
        for _, fh, _ in handles:
            try:
                fh.close()
            except OSError:
                pass
    return rc


def main(argv: list[str]) -> int:
    args = argv[1:]
    lines = 10
    bytes_mode = False
    byte_count = 0
    follow = False
    sleep_interval = 1.0

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "-n" and i + 1 < len(args):
            n = _parse_count(args[i + 1])
            if n is None:
                err(NAME, f"invalid line count: {args[i + 1]}")
                return 2
            lines = n
            i += 2
            continue
        if a == "-c" and i + 1 < len(args):
            n = _parse_count(args[i + 1])
            if n is None:
                err(NAME, f"invalid byte count: {args[i + 1]}")
                return 2
            bytes_mode = True
            byte_count = n
            i += 2
            continue
        if a == "-s" and i + 1 < len(args):
            try:
                sleep_interval = float(args[i + 1])
            except ValueError:
                err(NAME, f"invalid sleep interval: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            lines = int(a[1:])
            i += 1
            continue
        if a.startswith("-") and len(a) > 1:
            for ch in a[1:]:
                if ch in ("f", "F"):
                    follow = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
            i += 1
            continue
        break

    files = args[i:] or ["-"]
    multi = len(files) > 1
    rc = 0

    for idx, f in enumerate(files):
        try:
            fh = sys.stdin.buffer if f == "-" else open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        if multi:
            if idx > 0:
                sys.stdout.write("\n")
            sys.stdout.write(f"==> {f} <==\n")
            sys.stdout.flush()
        try:
            _initial_tail(fh, bytes_mode, byte_count, lines)
        finally:
            if close:
                fh.close()
        sys.stdout.flush()

    if not follow:
        return rc

    follow_files = [f for f in files if f != "-"]
    if not follow_files:
        return rc
    f_rc = _follow(follow_files, multi, sleep_interval)
    return rc if rc else f_rc
