from __future__ import annotations

from pybox.applets.md5sum import hashsum_main

NAME = "sha1sum"
ALIASES: list[str] = []
HELP = "compute and check SHA-1 message digests"


def main(argv: list[str]) -> int:
    return hashsum_main(NAME, "sha1", "SHA1", argv)
