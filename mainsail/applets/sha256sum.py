from __future__ import annotations

from mainsail.applets.md5sum import hashsum_main

NAME = "sha256sum"
ALIASES: list[str] = []
HELP = "compute and check SHA-256 message digests"


def main(argv: list[str]) -> int:
    return hashsum_main(NAME, "sha256", "SHA256", argv)
