from __future__ import annotations

from pybox.applets.md5sum import hashsum_main

NAME = "sha512sum"
ALIASES: list[str] = []
HELP = "compute and check SHA-512 message digests"


def main(argv: list[str]) -> int:
    return hashsum_main(NAME, "sha512", "SHA512", argv)
