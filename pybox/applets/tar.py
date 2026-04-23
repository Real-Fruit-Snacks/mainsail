from __future__ import annotations

import fnmatch
import os
import sys
import tarfile
from pathlib import Path

from pybox.common import err, err_path

NAME = "tar"
ALIASES: list[str] = []
HELP = "create, extract, or list tar archives"


def _expand_bundled(args: list[str]) -> list[str]:
    """Handle bundled flags: traditional 'cvfz' or dashed '-cvfz'."""
    if not args or not args[0]:
        return args
    first = args[0]
    if first.startswith("--") or first == "-":
        return args
    bundled = first[1:] if first.startswith("-") else first
    if not bundled or not all(c in "cxtrvzjJfkpaoC" for c in bundled):
        return args
    value_taking = "fC"
    need = sum(1 for c in bundled if c in value_taking)
    if len(args) < 1 + need:
        return args
    values = list(args[1:1 + need])
    rest = args[1 + need:]
    out: list[str] = []
    for c in bundled:
        out.append("-" + c)
        if c in value_taking and values:
            out.append(values.pop(0))
    return out + rest


def _iter_paths(paths: list[str]) -> list[str]:
    return list(paths)


def _should_exclude(path: str, excludes: list[str]) -> bool:
    base = os.path.basename(path)
    return any(fnmatch.fnmatchcase(base, pat) or fnmatch.fnmatchcase(path, pat)
               for pat in excludes)


def _create(archive: str, mode: str, paths: list[str], verbose: bool,
            excludes: list[str], cwd: str | None) -> int:
    rc = 0
    fileobj = None
    try:
        if archive == "-":
            fileobj = sys.stdout.buffer
            tf = tarfile.open(fileobj=fileobj, mode=mode)
        else:
            tf = tarfile.open(archive, mode=mode)
    except (OSError, tarfile.TarError) as e:
        err(NAME, f"cannot open '{archive}': {e}")
        return 1
    original_cwd = None
    if cwd:
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)
        except OSError as e:
            err_path(NAME, cwd, e)
            tf.close()
            return 1
    try:
        for p in paths:
            try:
                def _filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
                    if _should_exclude(info.name, excludes):
                        return None
                    if verbose:
                        sys.stderr.write(info.name + "\n")
                    return info
                tf.add(p, arcname=p, filter=_filter)
            except OSError as e:
                err_path(NAME, p, e)
                rc = 1
    finally:
        tf.close()
        if original_cwd is not None:
            os.chdir(original_cwd)
    return rc


def _extract(archive: str, mode: str, verbose: bool, excludes: list[str],
             cwd: str | None) -> int:
    try:
        if archive == "-":
            tf = tarfile.open(fileobj=sys.stdin.buffer, mode=mode)
        else:
            tf = tarfile.open(archive, mode=mode)
    except (OSError, tarfile.TarError) as e:
        err(NAME, f"cannot open '{archive}': {e}")
        return 1
    try:
        members = []
        for m in tf.getmembers():
            if _should_exclude(m.name, excludes):
                continue
            members.append(m)
            if verbose:
                sys.stderr.write(m.name + "\n")
        # Use "data" filter where supported to block dangerous paths/types
        extract_kwargs: dict = {}
        if hasattr(tarfile, "data_filter"):
            extract_kwargs["filter"] = "data"
        if cwd:
            tf.extractall(path=cwd, members=members, **extract_kwargs)
        else:
            tf.extractall(members=members, **extract_kwargs)
    except (OSError, tarfile.TarError) as e:
        err(NAME, f"extract: {e}")
        return 1
    finally:
        tf.close()
    return 0


def _list(archive: str, mode: str, verbose: bool) -> int:
    try:
        if archive == "-":
            tf = tarfile.open(fileobj=sys.stdin.buffer, mode=mode)
        else:
            tf = tarfile.open(archive, mode=mode)
    except (OSError, tarfile.TarError) as e:
        err(NAME, f"cannot open '{archive}': {e}")
        return 1
    try:
        for m in tf.getmembers():
            if verbose:
                sys.stdout.write(
                    f"{tarfile.filemode(m.mode)} {m.uname or m.uid}/{m.gname or m.gid} "
                    f"{m.size:>10} {m.name}\n"
                )
            else:
                sys.stdout.write(m.name + "\n")
    finally:
        tf.close()
    return 0


def main(argv: list[str]) -> int:
    args = _expand_bundled(argv[1:])
    op: str | None = None
    archive: str | None = None
    verbose = False
    compress = ""  # "", ":gz", ":bz2", ":xz"
    change_dir: str | None = None
    excludes: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a == "-c" or a == "--create":
            op = "c"
            i += 1
            continue
        if a == "-x" or a == "--extract":
            op = "x"
            i += 1
            continue
        if a == "-t" or a == "--list":
            op = "t"
            i += 1
            continue
        if a == "-v" or a == "--verbose":
            verbose = True
            i += 1
            continue
        if a == "-z" or a == "--gzip":
            compress = ":gz"
            i += 1
            continue
        if a == "-j" or a == "--bzip2":
            compress = ":bz2"
            i += 1
            continue
        if a == "-J" or a == "--xz":
            compress = ":xz"
            i += 1
            continue
        if a == "-f":
            if i + 1 >= len(args):
                err(NAME, "-f: missing argument")
                return 2
            archive = args[i + 1]
            i += 2
            continue
        if a.startswith("--file="):
            archive = a[len("--file="):]
            i += 1
            continue
        if a == "-C":
            if i + 1 >= len(args):
                err(NAME, "-C: missing argument")
                return 2
            change_dir = args[i + 1]
            i += 2
            continue
        if a.startswith("--directory="):
            change_dir = a[len("--directory="):]
            i += 1
            continue
        if a == "--exclude":
            if i + 1 >= len(args):
                err(NAME, "--exclude: missing argument")
                return 2
            excludes.append(args[i + 1])
            i += 2
            continue
        if a.startswith("--exclude="):
            excludes.append(a[len("--exclude="):])
            i += 1
            continue
        if a.startswith("-") and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        break

    if op is None:
        err(NAME, "must specify one of -c, -x, -t")
        return 2
    if archive is None:
        err(NAME, "-f is required")
        return 2

    paths = args[i:]

    if op == "c":
        mode = "w" + compress
        if not paths:
            err(NAME, "nothing to archive")
            return 2
        return _create(archive, mode, paths, verbose, excludes, change_dir)
    if op == "x":
        mode = "r" + (compress if compress else ":*")
        return _extract(archive, mode, verbose, excludes, change_dir)
    if op == "t":
        mode = "r" + (compress if compress else ":*")
        return _list(archive, mode, verbose)
    return 2
