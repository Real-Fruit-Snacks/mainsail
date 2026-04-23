from __future__ import annotations

import sys

NAME = "yes"
ALIASES: list[str] = []
HELP = "repeatedly output a line with the given STRING (or 'y')"


def main(argv: list[str]) -> int:
    args = argv[1:]
    text = " ".join(args) if args else "y"
    line = (text + "\n").encode("utf-8")
    out = sys.stdout.buffer
    # Chunk writes for throughput but flush often so consumers on a pipe see data.
    chunk = line * 64
    try:
        while True:
            out.write(chunk)
            out.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    except OSError:
        pass
    return 0
