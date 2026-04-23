from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from pybox.common import err, err_path

NAME = "unzip"
ALIASES: list[str] = []
HELP = "extract files from a .zip archive"


def main(argv: list[str]) -> int:
    args = argv[1:]
    dest = "."
    list_only = False
    overwrite: bool | None = None
    pipe_mode = False
    quiet = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a == "-d":
            if i + 1 >= len(args):
                err(NAME, "-d: missing argument")
                return 2
            dest = args[i + 1]
            i += 2
            continue
        if a == "-l":
            list_only = True
        elif a == "-o":
            overwrite = True
        elif a == "-n":
            overwrite = False
        elif a == "-p":
            pipe_mode = True
        elif a in ("-q", "-qq"):
            quiet = True
        elif a.startswith("-") and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        else:
            break
        i += 1

    positional = args[i:]
    if not positional:
        err(NAME, "missing archive")
        return 2
    archive = positional[0]
    requested = set(positional[1:]) if positional[1:] else None

    try:
        zf = zipfile.ZipFile(archive, "r")
    except (OSError, zipfile.BadZipFile) as e:
        err_path(NAME, archive, e)
        return 1

    try:
        if list_only:
            sys.stdout.write(f"Archive:  {archive}\n")
            sys.stdout.write("  Length      Date    Time    Name\n")
            sys.stdout.write("---------  ---------- -----   ----\n")
            total = 0
            count = 0
            for info in zf.infolist():
                if requested is not None and info.filename not in requested:
                    continue
                dt = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(*info.date_time[:5])
                sys.stdout.write(f"{info.file_size:>9}  {dt}   {info.filename}\n")
                total += info.file_size
                count += 1
            sys.stdout.write("---------                     -------\n")
            sys.stdout.write(f"{total:>9}                     {count} file" + ("s" if count != 1 else "") + "\n")
            return 0

        if pipe_mode:
            names = list(requested) if requested else zf.namelist()
            for n in names:
                try:
                    sys.stdout.buffer.write(zf.read(n))
                except KeyError:
                    err(NAME, f"{n}: not found in archive")
            return 0

        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)
        dest_resolved = dest_path.resolve()
        rc = 0

        for info in zf.infolist():
            if requested is not None and info.filename not in requested:
                continue
            target = dest_path / info.filename
            try:
                target.resolve().relative_to(dest_resolved)
            except ValueError:
                err(NAME, f"unsafe path skipped: {info.filename}")
                rc = 1
                continue

            if target.exists() and not info.is_dir():
                if overwrite is False:
                    continue
                if overwrite is None:
                    if sys.stdin.isatty():
                        sys.stderr.write(f"replace {target}? [y]es, [n]o, [A]ll, [N]one: ")
                        sys.stderr.flush()
                        try:
                            ans = sys.stdin.readline().strip()
                        except OSError:
                            ans = ""
                        if not ans or ans[0] in "nN":
                            if ans[:1] == "N":
                                overwrite = False
                            continue
                        if ans[0] == "A":
                            overwrite = True
                    else:
                        continue

            try:
                zf.extract(info, path=dest)
                if not quiet and not info.is_dir():
                    sys.stdout.write(f"  extracting: {info.filename}\n")
            except (OSError, zipfile.BadZipFile) as e:
                err_path(NAME, info.filename, e)
                rc = 1
        return rc
    finally:
        zf.close()
