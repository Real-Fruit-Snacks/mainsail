from __future__ import annotations

import sys
from dataclasses import dataclass

from pybox.common import err, err_path

NAME = "sort"
ALIASES: list[str] = []
HELP = "sort lines of text files"


@dataclass
class KeySpec:
    start: int  # 1-based field number
    end: int | None  # 1-based, inclusive; None = to end of line
    numeric: bool = False


def _parse_key_spec(s: str) -> KeySpec | None:
    i = 0
    while i < len(s) and (s[i].isdigit() or s[i] == ","):
        i += 1
    field_part = s[:i]
    opts = s[i:]
    if not field_part:
        return None
    if "," in field_part:
        a, b = field_part.split(",", 1)
        start = int(a) if a else 1
        end = int(b) if b else None
    else:
        start = int(field_part)
        end = None
    return KeySpec(start=start, end=end, numeric=("n" in opts))


def _extract_field(line: str, spec: KeySpec, sep: str | None) -> str:
    if sep is None:
        fields = line.split()
        joiner = " "
    else:
        fields = line.split(sep)
        joiner = sep
    start = max(1, spec.start) - 1
    end = spec.end if spec.end is not None else len(fields)
    return joiner.join(fields[start:end])


def _numeric_key(s: str) -> tuple[int, float, str]:
    stripped = s.lstrip()
    end = 0
    if end < len(stripped) and stripped[end] in "+-":
        end += 1
    saw_digit = False
    saw_dot = False
    while end < len(stripped):
        c = stripped[end]
        if c.isdigit():
            saw_digit = True
            end += 1
        elif c == "." and not saw_dot:
            saw_dot = True
            end += 1
        else:
            break
    if not saw_digit:
        return (1, 0.0, s)
    try:
        val = float(stripped[:end])
    except ValueError:
        return (1, 0.0, s)
    return (0, val, s)


def main(argv: list[str]) -> int:
    args = argv[1:]
    reverse = False
    numeric = False
    unique = False
    ignore_case = False
    ignore_leading_blanks = False
    separator: str | None = None
    output_path: str | None = None
    key_specs: list[KeySpec] = []
    files: list[str] = []

    def _take_value(flag: str, attached: str, idx: int) -> tuple[str | None, int]:
        """Return (value, new_idx) for a value-taking flag. None on error."""
        if attached:
            return attached, idx + 1
        if idx + 1 >= len(args):
            err(NAME, f"{flag}: missing argument")
            return None, idx
        return args[idx + 1], idx + 2

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "-" or not a.startswith("-") or len(a) < 2:
            files.append(a)
            i += 1
            continue

        if a == "-k" or a.startswith("-k"):
            value, new_i = _take_value("-k", a[2:], i)
            if value is None:
                return 2
            spec = _parse_key_spec(value)
            if spec is None:
                err(NAME, f"invalid -k spec: '{value}'")
                return 2
            key_specs.append(spec)
            i = new_i
            continue

        if a == "-t" or a.startswith("-t"):
            value, new_i = _take_value("-t", a[2:], i)
            if value is None:
                return 2
            if len(value) != 1:
                err(NAME, f"separator must be a single character: '{value}'")
                return 2
            separator = value
            i = new_i
            continue

        if a == "-o" or a.startswith("-o"):
            value, new_i = _take_value("-o", a[2:], i)
            if value is None:
                return 2
            output_path = value
            i = new_i
            continue

        for ch in a[1:]:
            if ch == "r":
                reverse = True
            elif ch == "n":
                numeric = True
            elif ch == "u":
                unique = True
            elif ch == "f":
                ignore_case = True
            elif ch == "b":
                ignore_leading_blanks = True
            else:
                err(NAME, f"invalid option: -{ch}")
                return 2
        i += 1

    if not files:
        files = ["-"]

    lines: list[str] = []
    rc = 0
    for f in files:
        try:
            fh = sys.stdin if f == "-" else open(f, "r", encoding="utf-8", errors="replace")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        try:
            for line in fh:
                lines.append(line.rstrip("\n"))
        finally:
            if close:
                fh.close()

    def base_transform(s: str) -> str:
        if ignore_leading_blanks:
            s = s.lstrip()
        if ignore_case:
            s = s.lower()
        return s

    def key_fn(s: str):
        if key_specs:
            parts: list = []
            for spec in key_specs:
                v = _extract_field(s, spec, separator)
                v = base_transform(v)
                if spec.numeric:
                    parts.append(_numeric_key(v))
                else:
                    parts.append(v)
            return tuple(parts)
        v = base_transform(s)
        return _numeric_key(v) if numeric else v

    lines.sort(key=key_fn, reverse=reverse)

    if unique:
        seen = set()
        deduped: list[str] = []
        for line in lines:
            k = key_fn(line)
            if k in seen:
                continue
            seen.add(k)
            deduped.append(line)
        lines = deduped

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as out_fh:
                for line in lines:
                    out_fh.write(line + "\n")
        except OSError as e:
            err_path(NAME, output_path, e)
            return 1
    else:
        for line in lines:
            sys.stdout.write(line + "\n")
    return rc
