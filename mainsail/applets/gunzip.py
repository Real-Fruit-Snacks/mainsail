from __future__ import annotations

from mainsail.applets import gzip as _gzip_applet

NAME = "gunzip"
ALIASES: list[str] = []
HELP = "decompress gzipped (.gz) files"


def main(argv: list[str]) -> int:
    return _gzip_applet.main(["gzip", "-d", *argv[1:]])
