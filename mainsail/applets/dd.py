"""mainsail dd — convert and copy a file.

POSIX-style operands (key=value), most common forms supported.

  dd if=in of=out bs=1M count=10 conv=notrunc,sync
"""
from __future__ import annotations

import os
import sys
import time

from mainsail.common import err

NAME = "dd"
ALIASES: list[str] = []
HELP = "convert and copy a file"


def _parse_size(s: str) -> int | None:
    if not s:
        return None
    mult = 1
    last = s[-1]
    suffixes_2 = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3,
                  "T": 1024 ** 4, "P": 1024 ** 5, "E": 1024 ** 6}
    suffixes_10 = {"k": 1000, "m": 1000_000, "g": 1000_000_000}
    if last in suffixes_2:
        mult = suffixes_2[last]
        s = s[:-1]
    elif last in suffixes_10:
        mult = suffixes_10[last]
        s = s[:-1]
    elif last == "B":
        mult = 1
        s = s[:-1]
    elif last in "wW":
        mult = 2
        s = s[:-1]
    elif last == "b":
        mult = 512
        s = s[:-1]
    try:
        return int(s) * mult
    except ValueError:
        return None


def _convert(buf: bytes, conv: set[str]) -> bytes:
    if "lcase" in conv:
        buf = buf.lower()
    if "ucase" in conv:
        buf = buf.upper()
    if "swab" in conv and len(buf) >= 2:
        # Swap each pair of bytes.
        ba = bytearray(buf)
        for i in range(0, len(ba) - 1, 2):
            ba[i], ba[i + 1] = ba[i + 1], ba[i]
        buf = bytes(ba)
    return buf


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--help":
        from mainsail.usage import USAGE
        sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
        return 0

    in_path: str | None = None
    out_path: str | None = None
    bs = 512
    ibs: int | None = None
    obs: int | None = None
    count: int | None = None
    skip = 0
    seek = 0
    conv: set[str] = set()
    status_mode = "default"  # default | none | noxfer | progress

    for arg in args:
        if "=" not in arg:
            err(NAME, f"bad operand {arg!r}")
            return 2
        k, v = arg.split("=", 1)
        if k == "if":
            in_path = v
        elif k == "of":
            out_path = v
        elif k == "bs":
            n = _parse_size(v)
            if n is None or n <= 0:
                err(NAME, f"invalid bs: {v}")
                return 2
            bs = n
        elif k == "ibs":
            n = _parse_size(v)
            if n is None or n <= 0:
                err(NAME, f"invalid ibs: {v}")
                return 2
            ibs = n
        elif k == "obs":
            n = _parse_size(v)
            if n is None or n <= 0:
                err(NAME, f"invalid obs: {v}")
                return 2
            obs = n
        elif k == "count":
            try:
                count = int(v)
            except ValueError:
                err(NAME, f"invalid count: {v}")
                return 2
        elif k == "skip":
            try:
                skip = int(v)
            except ValueError:
                err(NAME, f"invalid skip: {v}")
                return 2
        elif k == "seek":
            try:
                seek = int(v)
            except ValueError:
                err(NAME, f"invalid seek: {v}")
                return 2
        elif k == "conv":
            for piece in v.split(","):
                if piece in {"notrunc", "noerror", "sync", "fdatasync",
                             "fsync", "lcase", "ucase", "swab", "excl",
                             "nocreat"}:
                    conv.add(piece)
                else:
                    err(NAME, f"unknown conv: {piece}")
                    return 2
        elif k == "status":
            if v not in {"none", "noxfer", "progress", "default"}:
                err(NAME, f"unknown status: {v}")
                return 2
            status_mode = v
        else:
            err(NAME, f"unknown operand: {k}")
            return 2

    in_bs = ibs if ibs is not None else bs
    out_bs = obs if obs is not None else bs

    try:
        if in_path is None:
            in_fh = sys.stdin.buffer
        else:
            in_fh = open(in_path, "rb")
    except OSError as e:
        err(NAME, f"{in_path}: {e.strerror or e}")
        return 1

    try:
        if out_path is None:
            out_fh = sys.stdout.buffer
        else:
            mode = "rb+" if "notrunc" in conv else "wb"
            try:
                out_fh = open(out_path, mode)
            except FileNotFoundError:
                if "nocreat" in conv:
                    err(NAME, f"{out_path}: cannot create")
                    if in_fh is not sys.stdin.buffer:
                        in_fh.close()
                    return 1
                out_fh = open(out_path, "wb")
    except OSError as e:
        err(NAME, f"{out_path}: {e.strerror or e}")
        if in_fh is not sys.stdin.buffer:
            in_fh.close()
        return 1

    try:
        # Skip / seek
        if skip:
            try:
                in_fh.seek(skip * in_bs)
            except (OSError, AttributeError):
                # Pipe / non-seekable — read and discard
                remaining = skip * in_bs
                while remaining > 0:
                    chunk = in_fh.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
        if seek:
            try:
                out_fh.seek(seek * out_bs)
            except (OSError, AttributeError):
                pass

        records_in_full = 0
        records_in_part = 0
        records_out_full = 0
        records_out_part = 0
        bytes_total = 0
        start = time.monotonic()

        while True:
            if count is not None and records_in_full + records_in_part >= count:
                break
            try:
                buf = in_fh.read(in_bs)
            except OSError as e:
                if "noerror" in conv:
                    err(NAME, str(e))
                    continue
                raise
            if not buf:
                break
            if len(buf) == in_bs:
                records_in_full += 1
            else:
                records_in_part += 1
                if "sync" in conv:
                    buf += b"\x00" * (in_bs - len(buf))

            buf = _convert(buf, conv)

            try:
                out_fh.write(buf)
            except OSError as e:
                err(NAME, str(e))
                return 1
            if len(buf) == out_bs:
                records_out_full += 1
            elif len(buf) % out_bs == 0:
                records_out_full += len(buf) // out_bs
            else:
                records_out_full += len(buf) // out_bs
                records_out_part += 1
            bytes_total += len(buf)

        if "fsync" in conv or "fdatasync" in conv:
            try:
                if hasattr(out_fh, "fileno"):
                    if "fdatasync" in conv and hasattr(os, "fdatasync"):
                        os.fdatasync(out_fh.fileno())
                    else:
                        os.fsync(out_fh.fileno())
            except OSError:
                pass

        elapsed = time.monotonic() - start

        if status_mode != "none":
            sys.stderr.write(f"{records_in_full}+{records_in_part} records in\n")
            sys.stderr.write(f"{records_out_full}+{records_out_part} records out\n")
            if status_mode != "noxfer":
                rate = bytes_total / elapsed if elapsed > 0 else float("inf")
                sys.stderr.write(
                    f"{bytes_total} bytes copied, {elapsed:.4g} s, {rate:.3g} B/s\n"
                )
        return 0
    finally:
        if out_path is not None:
            out_fh.close()
        if in_path is not None:
            in_fh.close()
