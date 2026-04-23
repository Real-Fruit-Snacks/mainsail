from __future__ import annotations

import re
import sys

from pybox.common import err

NAME = "printf"
ALIASES: list[str] = []
HELP = "format and print data"

_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
    "a": "\a", "b": "\b", "f": "\f", "v": "\v", "0": "\0",
    "'": "'", '"': '"',
}

_SPEC_RE = re.compile(r"%([-+# 0]*)(\d*)(?:\.(\d+))?([diouxXeEfgGcsb%])")


def _process_escapes(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def _coerce_int(arg: str) -> int:
    if not arg:
        return 0
    try:
        return int(arg, 0)
    except ValueError:
        try:
            return int(float(arg))
        except ValueError:
            return 0


def _coerce_float(arg: str) -> float:
    if not arg:
        return 0.0
    try:
        return float(arg)
    except ValueError:
        return 0.0


def _apply_once(fmt: str, values: list[str]) -> tuple[str, bool, int]:
    out: list[str] = []
    pos = 0
    had_spec = False
    consumed = 0

    for m in _SPEC_RE.finditer(fmt):
        out.append(fmt[pos:m.start()])
        pos = m.end()
        flags, width, precision, spec = m.groups()
        if spec == "%":
            out.append("%")
            continue
        had_spec = True

        if consumed < len(values):
            arg = values[consumed]
            consumed += 1
        else:
            arg = ""

        py_spec = "d" if spec == "u" else spec
        py_fmt = "%" + flags + width + (f".{precision}" if precision else "") + py_spec

        try:
            if spec in "diouxX":
                out.append(py_fmt % _coerce_int(arg))
            elif spec in "eEfgG":
                out.append(py_fmt % _coerce_float(arg))
            elif spec == "c":
                out.append(py_fmt % (arg[0] if arg else ""))
            elif spec == "s":
                out.append(py_fmt % arg)
            elif spec == "b":
                out.append(_process_escapes(arg))
        except (ValueError, TypeError):
            if spec in "diouxXeEfgG":
                out.append("0")
            else:
                out.append(arg)

    out.append(fmt[pos:])
    return "".join(out), had_spec, consumed


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        err(NAME, "missing format")
        return 2
    fmt = _process_escapes(args[0])
    values = list(args[1:])

    text, had_spec, consumed = _apply_once(fmt, values)
    sys.stdout.write(text)
    values = values[consumed:]

    while had_spec and values:
        text, had_spec, consumed = _apply_once(fmt, values)
        sys.stdout.write(text)
        if consumed == 0:
            break
        values = values[consumed:]

    sys.stdout.flush()
    return 0
