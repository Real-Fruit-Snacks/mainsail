from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from mainsail.common import err

NAME = "mktemp"
ALIASES: list[str] = []
HELP = "create a unique temporary file or directory"


def _from_template(tmpl: str) -> tuple[str, str, int]:
    """Split a template like 'foo.XXXXXX' into (prefix, suffix, X-count)."""
    # Find the longest run of trailing X's anywhere in the basename. POSIX
    # mktemp expects at least 3, GNU/BusyBox accept >= 6.
    base = os.path.basename(tmpl)
    dirpart = os.path.dirname(tmpl)
    # Find rightmost X-run
    j = len(base)
    end = j
    while end > 0 and base[end - 1] != "X":
        end -= 1
    start = end
    while start > 0 and base[start - 1] == "X":
        start -= 1
    n = end - start
    if n < 3:
        return ("", "", 0)
    prefix = os.path.join(dirpart, base[:start]) if dirpart else base[:start]
    suffix = base[end:]
    return (prefix, suffix, n)


def main(argv: list[str]) -> int:
    args = argv[1:]
    make_dir = False
    dry_run = False
    quiet = False
    use_tmpdir = False
    explicit_dir: str | None = None
    template: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-d", "--directory"}:
            make_dir = True
            i += 1
            continue
        if a in {"-u", "--dry-run"}:
            dry_run = True
            i += 1
            continue
        if a in {"-q", "--quiet"}:
            quiet = True
            i += 1
            continue
        if a in {"-t"}:
            use_tmpdir = True
            i += 1
            continue
        if a == "-p" or a == "--tmpdir":
            if a == "-p" and i + 1 < len(args):
                explicit_dir = args[i + 1]
                i += 2
                continue
            if "=" in a:
                explicit_dir = a.split("=", 1)[1]
                i += 1
                continue
            # Bare --tmpdir means default tmp
            explicit_dir = tempfile.gettempdir()
            i += 1
            continue
        if a.startswith("--tmpdir="):
            explicit_dir = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            if quiet:
                return 1
            err(NAME, f"unknown option: {a}")
            return 2
        if template is None:
            template = a
            i += 1
            continue
        err(NAME, "too many arguments")
        return 2

    if template is None:
        template = "tmp.XXXXXXXXXX"

    prefix, suffix, n = _from_template(template)
    if n == 0:
        if not quiet:
            err(NAME, f"too few X's in template '{template}'")
        return 1

    target_dir: str | None
    if use_tmpdir:
        target_dir = explicit_dir or tempfile.gettempdir()
    elif explicit_dir is not None:
        target_dir = explicit_dir
    elif os.path.dirname(prefix):
        target_dir = None  # prefix already has a directory
    else:
        target_dir = None  # GNU default: cwd when template has no path

    try:
        # tempfile names use prefix/suffix; the X-count maps to a fixed
        # 8-char random suffix in CPython, which is fine for our purposes.
        if make_dir:
            path = tempfile.mkdtemp(prefix=os.path.basename(prefix),
                                    suffix=suffix, dir=target_dir)
            if dry_run:
                os.rmdir(path)
        else:
            fd, path = tempfile.mkstemp(prefix=os.path.basename(prefix),
                                        suffix=suffix, dir=target_dir)
            os.close(fd)
            if dry_run:
                os.unlink(path)
    except OSError as e:
        if not quiet:
            err(NAME, e.strerror or str(e))
        return 1

    sys.stdout.write(path + "\n")
    sys.stdout.flush()
    return 0
