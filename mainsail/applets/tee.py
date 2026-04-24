from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "tee"
ALIASES: list[str] = []
HELP = "read from stdin and write to stdout and files"

_CHUNK = 64 * 1024


def main(argv: list[str]) -> int:
    args = argv[1:]
    append = False
    ignore_sigint = False
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "--append":
            append = True
            i += 1
            continue
        if a == "-" or not a.startswith("-") or len(a) < 2:
            files.append(a)
            i += 1
            continue
        if all(ch in "ai" for ch in a[1:]):
            for ch in a[1:]:
                if ch == "a":
                    append = True
                elif ch == "i":
                    ignore_sigint = True
            i += 1
            continue
        err(NAME, f"invalid option: {a}")
        return 2

    if ignore_sigint:
        try:
            import signal
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except (AttributeError, ValueError, OSError):
            pass

    mode = "ab" if append else "wb"
    handles: list = []
    rc = 0
    for f in files:
        try:
            handles.append(open(f, mode))
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1

    try:
        while True:
            chunk = sys.stdin.buffer.read(_CHUNK)
            if not chunk:
                break
            try:
                sys.stdout.buffer.write(chunk)
                sys.stdout.flush()
            except OSError as e:
                err(NAME, f"stdout: {e}")
                rc = 1
            for fh in handles:
                try:
                    fh.write(chunk)
                    fh.flush()
                except OSError as e:
                    err(NAME, f"{getattr(fh, 'name', '?')}: {e}")
                    rc = 1
    finally:
        for fh in handles:
            try:
                fh.close()
            except OSError:
                pass
    return rc
