from __future__ import annotations

import socket
import sys

from mainsail.common import err

NAME = "hostname"
ALIASES: list[str] = []
HELP = "show the system's hostname"


def main(argv: list[str]) -> int:
    args = argv[1:]
    short = False
    full = False

    for a in args:
        if a in ("-s", "--short"):
            short = True
        elif a in ("-f", "--fqdn", "--long"):
            full = True
        elif a == "-I":
            # print IP addresses
            try:
                host = socket.gethostname()
                infos = socket.getaddrinfo(host, None)
                ips = sorted({i[4][0] for i in infos})
                sys.stdout.write(" ".join(ips) + "\n")
                return 0
            except OSError as e:
                err(NAME, str(e))
                return 1
        elif a.startswith("-"):
            err(NAME, f"invalid option: {a}")
            return 2
        else:
            err(NAME, "setting hostname is not supported")
            return 2

    try:
        if full:
            sys.stdout.write(socket.getfqdn() + "\n")
        elif short:
            sys.stdout.write(socket.gethostname().split(".")[0] + "\n")
        else:
            sys.stdout.write(socket.gethostname() + "\n")
    except OSError as e:
        err(NAME, str(e))
        return 1
    return 0
