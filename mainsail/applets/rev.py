from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "rev"
ALIASES: list[str] = []
HELP = "reverse lines characterwise"


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--help":
        from mainsail.usage import USAGE
        sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
        return 0

    files = args or ["-"]
    rc = 0

    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8", errors="replace", newline="")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        try:
            for line in fh:
                # Preserve newline structure: reverse only the content, not
                # the trailing \n (or \r\n).
                if line.endswith("\r\n"):
                    body, nl = line[:-2], "\r\n"
                elif line.endswith("\n"):
                    body, nl = line[:-1], "\n"
                else:
                    body, nl = line, ""
                sys.stdout.write(body[::-1] + nl)
        finally:
            if f != "-":
                fh.close()
        sys.stdout.flush()

    return rc
