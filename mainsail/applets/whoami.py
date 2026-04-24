from __future__ import annotations

import getpass
import sys

from mainsail.common import err

NAME = "whoami"
ALIASES: list[str] = []
HELP = "print effective user name"


def main(argv: list[str]) -> int:
    try:
        sys.stdout.write(getpass.getuser() + "\n")
    except Exception as e:
        err(NAME, str(e))
        return 1
    return 0
