from __future__ import annotations

import shutil
import sys

from pybox.common import err, err_path

NAME = "df"
ALIASES: list[str] = []
HELP = "report filesystem disk space usage"


def _format_human(n: int) -> str:
    units = ("", "K", "M", "G", "T", "P")
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if i == 0:
        return str(int(v))
    return f"{v:.1f}{units[i]}"


def main(argv: list[str]) -> int:
    args = argv[1:]
    human = False
    block_size = 1024

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if not a.startswith("-") or len(a) < 2 or a == "-":
            break
        if not all(ch in "hkm" for ch in a[1:]):
            err(NAME, f"invalid option: {a}")
            return 2
        for ch in a[1:]:
            if ch == "h":
                human = True
            elif ch == "k":
                block_size = 1024
            elif ch == "m":
                block_size = 1024 * 1024
        i += 1

    paths = args[i:] or ["."]

    def fmt(n: int) -> str:
        if human:
            return _format_human(n)
        return str((n + block_size - 1) // block_size)

    header_units = "Size" if human else f"{block_size // 1024}K-blocks"
    sys.stdout.write(
        f"{'Filesystem':<20} {header_units:>10} {'Used':>10} {'Avail':>10} {'Use%':>5}  Mounted on\n"
    )

    rc = 0
    for p in paths:
        try:
            usage = shutil.disk_usage(p)
        except OSError as e:
            err_path(NAME, p, e)
            rc = 1
            continue
        used_pct = (100 * usage.used / usage.total) if usage.total else 0
        sys.stdout.write(
            f"{p:<20} {fmt(usage.total):>10} {fmt(usage.used):>10} "
            f"{fmt(usage.free):>10} {used_pct:>4.0f}%  {p}\n"
        )
    return rc
