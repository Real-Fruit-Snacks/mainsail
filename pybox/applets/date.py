from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from pybox.common import err, err_path

NAME = "date"
ALIASES: list[str] = []
HELP = "print or format the date and time"


def _parse_date_string(s: str) -> datetime | None:
    s = s.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1] + "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    utc = False
    d_arg: str | None = None
    r_arg: str | None = None
    fmt: str | None = None
    iso_spec: str | None = None
    rfc_2822 = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            break
        if a in ("-u", "--utc", "--universal"):
            utc = True
            i += 1
            continue
        if a in ("-d", "--date"):
            if i + 1 >= len(args):
                err(NAME, f"{a}: missing argument")
                return 2
            d_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--date="):
            d_arg = a[len("--date="):]
            i += 1
            continue
        if a == "-r":
            if i + 1 >= len(args):
                err(NAME, "-r: missing argument")
                return 2
            r_arg = args[i + 1]
            i += 2
            continue
        if a.startswith("--reference="):
            r_arg = a[len("--reference="):]
            i += 1
            continue
        if a in ("-R", "--rfc-2822", "--rfc-email"):
            rfc_2822 = True
            i += 1
            continue
        if a == "-I":
            iso_spec = "date"
            i += 1
            continue
        if a.startswith("-I"):
            spec = a[2:]
            if spec not in ("date", "hours", "minutes", "seconds", "ns"):
                err(NAME, f"invalid --iso-8601 arg: {spec}")
                return 2
            iso_spec = spec
            i += 1
            continue
        if a.startswith("--iso-8601"):
            if "=" in a:
                spec = a.split("=", 1)[1]
            else:
                spec = "date"
            if spec not in ("date", "hours", "minutes", "seconds", "ns"):
                err(NAME, f"invalid --iso-8601 arg: {spec}")
                return 2
            iso_spec = spec
            i += 1
            continue
        if a.startswith("+"):
            fmt = a[1:]
            i += 1
            continue
        if a.startswith("-"):
            err(NAME, f"invalid option: {a}")
            return 2
        break

    # Pick the datetime to format
    if r_arg is not None:
        try:
            mtime = os.stat(r_arg).st_mtime
        except OSError as e:
            err_path(NAME, r_arg, e)
            return 1
        dt = datetime.fromtimestamp(mtime, tz=timezone.utc if utc else None)
    elif d_arg is not None:
        parsed = _parse_date_string(d_arg)
        if parsed is None:
            err(NAME, f"invalid date: '{d_arg}'")
            return 1
        dt = parsed
        if utc and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = datetime.now(tz=timezone.utc if utc else None)

    if utc and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)

    if fmt:
        output = dt.strftime(fmt)
    elif rfc_2822:
        output = dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    elif iso_spec:
        patterns = {
            "date": "%Y-%m-%d",
            "hours": "%Y-%m-%dT%H%z",
            "minutes": "%Y-%m-%dT%H:%M%z",
            "seconds": "%Y-%m-%dT%H:%M:%S%z",
            "ns": "%Y-%m-%dT%H:%M:%S.%f%z",
        }
        output = dt.strftime(patterns[iso_spec])
    else:
        output = dt.strftime("%a %b %d %H:%M:%S %Y")

    sys.stdout.write(output + "\n")
    return 0
