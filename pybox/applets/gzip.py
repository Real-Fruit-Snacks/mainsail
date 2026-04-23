from __future__ import annotations

import gzip as _gzip
import os
import shutil
import sys

from pybox.common import err, err_path

NAME = "gzip"
ALIASES: list[str] = []
HELP = "compress or decompress files (.gz)"


def _compress_stream(src, dst, level: int) -> None:
    with _gzip.GzipFile(fileobj=dst, mode="wb", compresslevel=level) as out:
        shutil.copyfileobj(src, out)


def _decompress_stream(src, dst) -> None:
    with _gzip.GzipFile(fileobj=src, mode="rb") as inp:
        shutil.copyfileobj(inp, dst)


def _compress_file(path: str, level: int, keep: bool, force: bool, to_stdout: bool) -> int:
    if to_stdout:
        try:
            with open(path, "rb") as fh:
                _compress_stream(fh, sys.stdout.buffer, level)
        except OSError as e:
            err_path(NAME, path, e)
            return 1
        return 0

    out = path + ".gz"
    if os.path.exists(out) and not force:
        err(NAME, f"{out} already exists; use -f to overwrite")
        return 1
    try:
        with open(path, "rb") as fh, open(out, "wb") as wh:
            _compress_stream(fh, wh, level)
    except OSError as e:
        err_path(NAME, path, e)
        return 1
    if not keep:
        try:
            os.unlink(path)
        except OSError as e:
            err_path(NAME, path, e)
            return 1
    return 0


def _decompress_file(path: str, keep: bool, force: bool, to_stdout: bool, test_only: bool) -> int:
    if not path.endswith(".gz") and not force and not to_stdout and not test_only:
        err(NAME, f"{path}: unknown suffix; skipping (use -f to force)")
        return 1

    out = path[:-3] if path.endswith(".gz") else path + ".out"

    if test_only or to_stdout:
        try:
            target = sys.stdout.buffer if to_stdout else open(os.devnull, "wb")
            with open(path, "rb") as fh:
                _decompress_stream(fh, target)
            if not to_stdout:
                target.close()
        except (OSError, _gzip.BadGzipFile, EOFError) as e:
            err_path(NAME, path, e)
            return 1
        return 0

    if os.path.exists(out) and not force:
        err(NAME, f"{out} already exists; use -f to overwrite")
        return 1
    try:
        with open(path, "rb") as fh, open(out, "wb") as wh:
            _decompress_stream(fh, wh)
    except (OSError, _gzip.BadGzipFile, EOFError) as e:
        err_path(NAME, path, e)
        try:
            os.unlink(out)
        except OSError:
            pass
        return 1
    if not keep:
        try:
            os.unlink(path)
        except OSError as e:
            err_path(NAME, path, e)
            return 1
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    decompress = False
    to_stdout = False
    keep = False
    force = False
    level = 6
    test_only = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a in ("-d", "--decompress", "--uncompress"):
            decompress = True
        elif a in ("-c", "--stdout", "--to-stdout"):
            to_stdout = True
            keep = True
        elif a in ("-k", "--keep"):
            keep = True
        elif a in ("-f", "--force"):
            force = True
        elif a in ("-t", "--test"):
            test_only = True
            decompress = True
        elif a in ("-q", "--quiet", "-v", "--verbose"):
            pass  # accepted but ignored
        elif a in ("-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"):
            level = int(a[1:])
        elif a.startswith("-") and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        else:
            break
        i += 1

    files = args[i:]
    # stdin→stdout mode when no files or "-"
    if not files or files == ["-"]:
        try:
            if decompress:
                _decompress_stream(sys.stdin.buffer, sys.stdout.buffer)
            else:
                _compress_stream(sys.stdin.buffer, sys.stdout.buffer, level)
            return 0
        except (OSError, _gzip.BadGzipFile, EOFError) as e:
            err(NAME, f"{e}")
            return 1

    rc = 0
    for f in files:
        if decompress:
            r = _decompress_file(f, keep, force, to_stdout, test_only)
        else:
            r = _compress_file(f, level, keep, force, to_stdout)
        if r != 0:
            rc = r
    return rc
