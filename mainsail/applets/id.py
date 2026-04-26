"""mainsail id — print user/group identity."""
from __future__ import annotations

import os
import sys

from mainsail.common import err

NAME = "id"
ALIASES: list[str] = []
HELP = "print user and group IDs"


def _have_pwdgrp() -> bool:
    try:
        import pwd, grp  # noqa: F401
        return True
    except ImportError:
        return False


def _resolve_user(name_or_uid: str | None):
    """Return a tuple (uid, gid, username) for the named user, or current
    when name_or_uid is None. None on lookup failure."""
    if not _have_pwdgrp():
        if name_or_uid is None:
            return os.environ.get("USERNAME", os.environ.get("USER", "?")), None, None
        return None
    import pwd
    if name_or_uid is None:
        try:
            entry = pwd.getpwuid(os.getuid())
        except KeyError:
            return None
    else:
        try:
            entry = pwd.getpwuid(int(name_or_uid))
        except (ValueError, KeyError):
            try:
                entry = pwd.getpwnam(name_or_uid)
            except KeyError:
                return None
    return entry.pw_uid, entry.pw_gid, entry.pw_name


def _supplementary_groups(username: str, primary_gid: int) -> list[int]:
    if not _have_pwdgrp():
        return []
    import grp
    out = [primary_gid]
    for g in grp.getgrall():
        if username in g.gr_mem and g.gr_gid not in out:
            out.append(g.gr_gid)
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    show_user = False
    show_group = False
    show_all_groups = False
    name_only = False
    real = False
    user_arg: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-u", "--user"}:
            show_user = True
            i += 1; continue
        if a in {"-g", "--group"}:
            show_group = True
            i += 1; continue
        if a in {"-G", "--groups"}:
            show_all_groups = True
            i += 1; continue
        if a in {"-n", "--name"}:
            name_only = True
            i += 1; continue
        if a in {"-r", "--real"}:
            real = True  # accepted; we already use real (geteuid) on POSIX
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        if user_arg is not None:
            err(NAME, "extra operand")
            return 2
        user_arg = a
        i += 1

    if not _have_pwdgrp():
        # Windows fallback: return whatever we can.
        username = user_arg or os.environ.get("USERNAME", os.environ.get("USER", "?"))
        if show_user:
            sys.stdout.write(f"{username}\n" if name_only else "0\n")
            return 0
        if show_group or show_all_groups:
            sys.stdout.write("?\n")
            return 0
        sys.stdout.write(f"uid=?({username}) gid=? groups=?\n")
        return 0

    info = _resolve_user(user_arg)
    if info is None:
        err(NAME, f"{user_arg!r}: no such user")
        return 1
    uid, gid, username = info
    groups = _supplementary_groups(username, gid)

    import pwd, grp
    def _gname(g: int) -> str:
        try:
            return grp.getgrgid(g).gr_name
        except KeyError:
            return str(g)

    if show_user:
        sys.stdout.write(f"{username if name_only else uid}\n")
        return 0
    if show_group:
        sys.stdout.write(f"{_gname(gid) if name_only else gid}\n")
        return 0
    if show_all_groups:
        if name_only:
            sys.stdout.write(" ".join(_gname(g) for g in groups) + "\n")
        else:
            sys.stdout.write(" ".join(str(g) for g in groups) + "\n")
        return 0

    parts = [f"uid={uid}({username})", f"gid={gid}({_gname(gid)})"]
    group_repr = ",".join(f"{g}({_gname(g)})" for g in groups)
    parts.append(f"groups={group_repr}")
    sys.stdout.write(" ".join(parts) + "\n")
    return 0
