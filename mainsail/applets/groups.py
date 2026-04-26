"""mainsail groups — print group memberships for a user."""
from __future__ import annotations

import os
import sys

from mainsail.common import err

NAME = "groups"
ALIASES: list[str] = []
HELP = "print groups a user is in"


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] in {"-h", "--help"}:
        from mainsail.usage import USAGE
        sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
        return 0

    try:
        import pwd, grp
    except ImportError:
        # Windows: no equivalent without ctypes / win32api dance.
        username = (args[0] if args else
                    os.environ.get("USERNAME", os.environ.get("USER", "?")))
        sys.stdout.write(f"{username} : (groups not available on this platform)\n")
        return 0

    users = args or [None]  # type: ignore[list-item]
    rc = 0
    for u in users:
        if u is None:
            try:
                entry = pwd.getpwuid(os.getuid())
            except KeyError:
                err(NAME, "current user not in passwd")
                rc = 1
                continue
        else:
            try:
                entry = pwd.getpwnam(u)
            except KeyError:
                err(NAME, f"{u!r}: no such user")
                rc = 1
                continue

        primary = entry.pw_gid
        gids = [primary]
        for g in grp.getgrall():
            if entry.pw_name in g.gr_mem and g.gr_gid not in gids:
                gids.append(g.gr_gid)

        names = []
        for gid in gids:
            try:
                names.append(grp.getgrgid(gid).gr_name)
            except KeyError:
                names.append(str(gid))

        if len(users) > 1 or u is not None:
            sys.stdout.write(f"{entry.pw_name} : {' '.join(names)}\n")
        else:
            sys.stdout.write(" ".join(names) + "\n")
    return rc
