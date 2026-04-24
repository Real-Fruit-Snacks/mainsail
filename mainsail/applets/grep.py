from __future__ import annotations

import os
import re
import sys

from mainsail.common import err, err_path

NAME = "grep"
ALIASES: list[str] = []
HELP = "print lines matching a pattern"


def _parse_count(flag: str, value: str) -> int | None:
    try:
        n = int(value)
        if n < 0:
            raise ValueError
        return n
    except ValueError:
        err(NAME, f"{flag}: invalid number '{value}'")
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    ignore_case = False
    invert = False
    show_line_num = False
    recursive = False
    fixed_string = False
    list_files = False
    count_only = False
    word_match = False
    only_matching = False
    quiet = False
    before_n = 0
    after_n = 0

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break

        # Value-taking flags: -A, -B, -C (with optional attached value)
        if a in ("-A", "-B", "-C"):
            if i + 1 >= len(args):
                err(NAME, f"{a}: missing argument")
                return 2
            n = _parse_count(a, args[i + 1])
            if n is None:
                return 2
            if a == "-A":
                after_n = max(after_n, n)
            elif a == "-B":
                before_n = max(before_n, n)
            else:
                before_n = max(before_n, n)
                after_n = max(after_n, n)
            i += 2
            continue
        if len(a) > 2 and a[:2] in ("-A", "-B", "-C") and a[2:].lstrip("-").isdigit():
            n = _parse_count(a[:2], a[2:])
            if n is None:
                return 2
            if a[:2] == "-A":
                after_n = max(after_n, n)
            elif a[:2] == "-B":
                before_n = max(before_n, n)
            else:
                before_n = max(before_n, n)
                after_n = max(after_n, n)
            i += 1
            continue

        if not a.startswith("-") or len(a) < 2 or a == "-":
            break

        for ch in a[1:]:
            if ch == "i":
                ignore_case = True
            elif ch == "v":
                invert = True
            elif ch == "n":
                show_line_num = True
            elif ch in ("r", "R"):
                recursive = True
            elif ch == "F":
                fixed_string = True
            elif ch == "l":
                list_files = True
            elif ch == "c":
                count_only = True
            elif ch == "w":
                word_match = True
            elif ch == "o":
                only_matching = True
            elif ch == "q":
                quiet = True
            elif ch == "E":
                pass  # Python re is already extended
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    remaining = args[i:]
    if not remaining:
        err(NAME, "missing pattern")
        return 2

    pattern = remaining[0]
    targets = remaining[1:]

    if fixed_string:
        pattern = re.escape(pattern)
    if word_match:
        pattern = rf"\b(?:{pattern})\b"
    flags = re.IGNORECASE if ignore_case else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error as e:
        err(NAME, f"bad pattern: {e}")
        return 2

    if not targets:
        targets = ["-"]

    if recursive:
        expanded: list[str] = []
        for t in targets:
            if os.path.isdir(t):
                for root, _, files in os.walk(t):
                    for f in sorted(files):
                        expanded.append(os.path.join(root, f))
            else:
                expanded.append(t)
        targets = expanded

    show_filename = len(targets) > 1 or recursive
    matched_any = False

    def write_line(path: str, lineno: int, text: str, match_sep: bool) -> None:
        parts: list[str] = []
        if show_filename:
            parts.append(path)
        if show_line_num:
            parts.append(str(lineno))
        parts.append(text)
        sep = ":" if match_sep else "-"
        sys.stdout.write(sep.join(parts) + "\n")

    for t in targets:
        try:
            fh = sys.stdin if t == "-" else open(t, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, t, e)
            continue

        close = t != "-"
        try:
            lines = [(n, ln.rstrip("\n")) for n, ln in enumerate(fh, 1)]
        finally:
            if close:
                fh.close()

        match_map: dict[int, list[re.Match[str]]] = {}
        for n, text in lines:
            found = list(rx.finditer(text))
            is_match = bool(found) != invert
            if is_match:
                match_map[n] = found if not invert else []

        if quiet:
            if match_map:
                return 0
            continue

        if list_files:
            if match_map:
                matched_any = True
                sys.stdout.write(t + "\n")
            continue

        if count_only:
            cnt = len(match_map)
            if show_filename:
                sys.stdout.write(f"{t}:{cnt}\n")
            else:
                sys.stdout.write(f"{cnt}\n")
            if cnt:
                matched_any = True
            continue

        if only_matching:
            for n, _text in lines:
                if n in match_map:
                    for m in match_map[n]:
                        write_line(t, n, m.group(0), True)
            if match_map:
                matched_any = True
            continue

        if not match_map:
            continue
        matched_any = True

        # Expand to context lines
        to_print: dict[int, bool] = {n: True for n in match_map}
        if before_n or after_n:
            match_set = set(match_map.keys())
            total = len(lines)
            for m in match_set:
                for k in range(max(1, m - before_n), min(total, m + after_n) + 1):
                    to_print.setdefault(k, False)

        prev_printed = None
        for n, text in lines:
            if n in to_print:
                if prev_printed is not None and n - prev_printed > 1:
                    sys.stdout.write("--\n")
                write_line(t, n, text, to_print[n])
                prev_printed = n

    return 0 if matched_any else 1
