from __future__ import annotations

import os
import sys
from pathlib import Path

from pybox.common import err, err_path

NAME = "chmod"
ALIASES: list[str] = []
HELP = "change file mode bits"


def _parse_octal(s: str) -> int | None:
    try:
        return int(s, 8)
    except ValueError:
        return None


def _apply_clause(mode: int, clause: str) -> int:
    """Apply one symbolic clause like 'u+x' or 'go-w' or 'a=r' to mode."""
    op_idx = -1
    for i, c in enumerate(clause):
        if c in "+-=":
            op_idx = i
            break
    if op_idx < 0:
        raise ValueError(f"no operator in clause '{clause}'")

    who = clause[:op_idx]
    op = clause[op_idx]
    perms = clause[op_idx + 1:]

    if not who or "a" in who:
        who_mask = 0o777
        has_u = has_g = True
    else:
        who_mask = 0
        if "u" in who:
            who_mask |= 0o700
        if "g" in who:
            who_mask |= 0o070
        if "o" in who:
            who_mask |= 0o007
        has_u = "u" in who
        has_g = "g" in who

    perm_bits = 0
    if "r" in perms:
        perm_bits |= 0o444
    if "w" in perms:
        perm_bits |= 0o222
    if "x" in perms:
        perm_bits |= 0o111

    effective = perm_bits & who_mask
    if "s" in perms:
        if has_u:
            effective |= 0o4000
        if has_g:
            effective |= 0o2000
    if "t" in perms:
        effective |= 0o1000

    if op == "+":
        return mode | effective
    if op == "-":
        return mode & ~effective
    if op == "=":
        clear_mask = who_mask
        if "s" in perms or has_u:
            clear_mask |= 0o4000 if has_u else 0
        if "s" in perms or has_g:
            clear_mask |= 0o2000 if has_g else 0
        return (mode & ~clear_mask) | effective
    return mode


def _compute_new_mode(current: int, spec: str) -> int:
    octal = _parse_octal(spec)
    if octal is not None:
        return octal
    mode = current
    for clause in spec.split(","):
        mode = _apply_clause(mode, clause.strip())
    return mode


def main(argv: list[str]) -> int:
    args = argv[1:]
    recursive = False
    verbose = False
    changes_only = False
    silent = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2 or a == "-":
            break
        # Mode strings like -rwx or -r or -644 would conflict with flags.
        # chmod accepts mode-as-first-arg; once we see the first non-flag
        # token, everything else is mode + paths. We stop flag parsing on
        # anything that isn't a recognized flag char.
        if not all(ch in "Rrvcf" for ch in a[1:]):
            break
        for ch in a[1:]:
            if ch in ("R", "r"):
                recursive = True
            elif ch == "v":
                verbose = True
            elif ch == "c":
                changes_only = True
            elif ch == "f":
                silent = True
        i += 1

    remaining = args[i:]
    if len(remaining) < 2:
        err(NAME, "missing operand")
        return 2

    mode_spec = remaining[0]
    paths = remaining[1:]

    rc = 0

    def apply(p: Path) -> None:
        nonlocal rc
        try:
            st = p.lstat()
        except OSError as e:
            if not silent:
                err_path(NAME, str(p), e)
            rc = 1
            return
        try:
            new_mode = _compute_new_mode(st.st_mode & 0o7777, mode_spec)
        except ValueError as e:
            err(NAME, str(e))
            rc = 2
            return
        old_mode = st.st_mode & 0o7777
        if new_mode == old_mode:
            if verbose and not changes_only:
                sys.stdout.write(f"mode of '{p}' retained as {old_mode:04o}\n")
            return
        try:
            os.chmod(p, new_mode)
        except OSError as e:
            if not silent:
                err_path(NAME, str(p), e)
            rc = 1
            return
        if verbose or changes_only:
            sys.stdout.write(f"mode of '{p}' changed from {old_mode:04o} to {new_mode:04o}\n")

    for path in paths:
        p = Path(path)
        if not p.exists() and not p.is_symlink():
            if not silent:
                err_path(NAME, path, FileNotFoundError(2, "No such file or directory"))
            rc = 1
            continue
        apply(p)
        if recursive and p.is_dir() and not p.is_symlink():
            for root, dirs, files in os.walk(p):
                for d in dirs:
                    apply(Path(root) / d)
                for f in files:
                    apply(Path(root) / f)
    return rc
