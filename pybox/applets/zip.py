from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

from pybox.common import err, err_path

NAME = "zip"
ALIASES: list[str] = []
HELP = "package and compress files into a .zip archive"


def _delete_entries(archive: str, names: list[str]) -> int:
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            kept: list[tuple[zipfile.ZipInfo, bytes]] = []
            for info in zf.infolist():
                if info.filename in names:
                    continue
                kept.append((info, zf.read(info)))
    except (OSError, zipfile.BadZipFile) as e:
        err_path(NAME, archive, e)
        return 1
    try:
        with zipfile.ZipFile(archive, "w") as zf:
            for info, data in kept:
                zf.writestr(info, data)
    except OSError as e:
        err_path(NAME, archive, e)
        return 1
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    recursive = False
    junk_paths = False
    delete_mode = False
    append = False
    level = 6

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a in ("-r", "--recurse-paths"):
            recursive = True
        elif a in ("-j", "--junk-paths"):
            junk_paths = True
        elif a in ("-d", "--delete"):
            delete_mode = True
        elif a in ("-g", "--grow"):
            append = True
        elif a in ("-0", "-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9"):
            level = int(a[1:])
        elif a.startswith("-") and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        else:
            break
        i += 1

    positional = args[i:]
    if not positional:
        err(NAME, "missing archive name")
        return 2
    archive = positional[0]
    names = positional[1:]

    if delete_mode:
        if not names:
            err(NAME, "no entries to delete")
            return 2
        return _delete_entries(archive, names)

    if not names:
        err(NAME, "no files to archive")
        return 2

    method = zipfile.ZIP_STORED if level == 0 else zipfile.ZIP_DEFLATED
    mode = "a" if append and os.path.exists(archive) else "w"

    rc = 0
    try:
        kwargs: dict = {"compression": method}
        if method == zipfile.ZIP_DEFLATED:
            kwargs["compresslevel"] = level
        with zipfile.ZipFile(archive, mode, **kwargs) as zf:
            for name in names:
                p = Path(name)
                if not p.exists():
                    err_path(NAME, name, FileNotFoundError(2, "No such file or directory"))
                    rc = 1
                    continue
                if p.is_dir():
                    if not recursive:
                        err(NAME, f"{name} is a directory (use -r)")
                        rc = 1
                        continue
                    for root, _, files in os.walk(p):
                        for f in files:
                            src = os.path.join(root, f)
                            arcname = os.path.basename(src) if junk_paths else src
                            try:
                                zf.write(src, arcname=arcname)
                            except OSError as e:
                                err_path(NAME, src, e)
                                rc = 1
                else:
                    arcname = p.name if junk_paths else name
                    try:
                        zf.write(name, arcname=arcname)
                    except OSError as e:
                        err_path(NAME, name, e)
                        rc = 1
    except OSError as e:
        err_path(NAME, archive, e)
        return 1
    return rc
