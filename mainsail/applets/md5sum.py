from __future__ import annotations

import hashlib
import re
import sys

from mainsail.common import err, err_path

NAME = "md5sum"
ALIASES: list[str] = []
HELP = "compute and check MD5 message digests"


_BSD_LINE_RE = re.compile(r"^([0-9a-fA-F]+)[ \t]+([ *]?)(.+)$")


def _compute_file(path: str, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _compute_stdin(algo: str) -> str:
    h = hashlib.new(algo)
    while True:
        chunk = sys.stdin.buffer.read(65536)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def _parse_check_line(line: str, label: str) -> tuple[str, str] | None:
    # BSD-tag form: "LABEL (FILE) = HEX"
    prefix = label + " ("
    if line.startswith(prefix):
        rest = line[len(prefix):]
        close = rest.rfind(") = ")
        if close == -1:
            return None
        return rest[close + 4:], rest[:close]
    m = _BSD_LINE_RE.match(line)
    if not m:
        return None
    return m.group(1), m.group(3)


def _do_check(
    applet: str, algo: str, label: str, files: list[str],
    quiet: bool, status: bool, warn: bool, strict: bool,
) -> int:
    ok = bad = unreadable = malformed = 0
    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8")
        except OSError as e:
            err_path(applet, f, e)
            return 1
        close = f != "-"
        try:
            for lineno, raw in enumerate(fh, 1):
                line = raw.rstrip("\n").rstrip("\r")
                if not line or line.startswith("#"):
                    continue
                parsed = _parse_check_line(line, label)
                if parsed is None:
                    malformed += 1
                    if warn:
                        err(applet, f"{f}:{lineno}: improperly formatted {label} checksum line")
                    continue
                expected, target = parsed
                try:
                    actual = _compute_file(target, algo)
                except OSError:
                    unreadable += 1
                    if not status:
                        sys.stdout.write(f"{target}: FAILED open or read\n")
                    continue
                if actual.lower() == expected.lower():
                    ok += 1
                    if not status and not quiet:
                        sys.stdout.write(f"{target}: OK\n")
                else:
                    bad += 1
                    if not status:
                        sys.stdout.write(f"{target}: FAILED\n")
        finally:
            if close:
                fh.close()

    if strict and malformed:
        return 1
    if bad or unreadable:
        if not status:
            if bad:
                sys.stderr.write(f"{applet}: WARNING: {bad} computed checksum did NOT match\n")
            if unreadable:
                sys.stderr.write(f"{applet}: WARNING: {unreadable} listed file could not be read\n")
        return 1
    return 0


def hashsum_main(applet: str, algo: str, label: str, argv: list[str]) -> int:
    args = argv[1:]
    check = False
    binary = False
    tag = False
    quiet = False
    status = False
    warn = False
    strict = False
    zero = False
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a in ("-c", "--check"):
            check = True
        elif a in ("-b", "--binary"):
            binary = True
        elif a in ("-t", "--text"):
            binary = False
        elif a == "--tag":
            tag = True
        elif a == "--quiet":
            quiet = True
        elif a == "--status":
            status = True
        elif a in ("-w", "--warn"):
            warn = True
        elif a == "--strict":
            strict = True
        elif a in ("-z", "--zero"):
            zero = True
        elif a.startswith("-") and a != "-":
            err(applet, f"invalid option: {a}")
            return 2
        else:
            files.append(a)
        i += 1

    if not files:
        files = ["-"]

    if check:
        return _do_check(applet, algo, label, files, quiet, status, warn, strict)

    rc = 0
    end = "\0" if zero else "\n"
    for f in files:
        try:
            digest = _compute_stdin(algo) if f == "-" else _compute_file(f, algo)
        except OSError as e:
            err_path(applet, f, e)
            rc = 1
            continue
        if tag:
            sys.stdout.write(f"{label} ({f}) = {digest}{end}")
        else:
            sep = "*" if binary else " "
            sys.stdout.write(f"{digest} {sep}{f}{end}")
    return rc


def main(argv: list[str]) -> int:
    return hashsum_main(NAME, "md5", "MD5", argv)
