from __future__ import annotations

import time

from mainsail.common import err

NAME = "sleep"
ALIASES: list[str] = []
HELP = "delay for a specified amount of time"

_MULT = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}


def _parse_duration(s: str) -> float | None:
    if not s:
        return None
    suffix = s[-1]
    if suffix in _MULT:
        body = s[:-1]
        mult = _MULT[suffix]
    else:
        body = s
        mult = 1.0
    try:
        return float(body) * mult
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        err(NAME, "missing operand")
        return 2
    total = 0.0
    for a in args:
        d = _parse_duration(a)
        if d is None or d < 0:
            err(NAME, f"invalid time interval: '{a}'")
            return 2
        total += d
    try:
        time.sleep(total)
    except KeyboardInterrupt:
        return 130
    return 0
