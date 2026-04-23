from __future__ import annotations

import subprocess
import sys

from pybox.common import err, err_path

NAME = "xargs"
ALIASES: list[str] = []
HELP = "build and execute command lines from standard input"


def _tokenize_shell_like(data: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    in_single = False
    in_double = False
    i = 0
    while i < len(data):
        c = data[i]
        if in_single:
            if c == "'":
                in_single = False
            else:
                current.append(c)
        elif in_double:
            if c == '"':
                in_double = False
            elif c == "\\" and i + 1 < len(data):
                current.append(data[i + 1])
                i += 1
            else:
                current.append(c)
        else:
            if c in " \t\n":
                flush()
            elif c == "'":
                in_single = True
            elif c == '"':
                in_double = True
            elif c == "\\" and i + 1 < len(data):
                current.append(data[i + 1])
                i += 1
            else:
                current.append(c)
        i += 1
    flush()
    return tokens


def main(argv: list[str]) -> int:
    args = argv[1:]
    n_per_call: int | None = None
    lines_per_call: int | None = None
    replace_str: str | None = None
    null_sep = False
    delimiter: str | None = None
    no_run_empty = False
    trace = False
    input_file: str | None = None

    def _take(flag: str, a: str, idx: int) -> tuple[str | None, int]:
        if len(a) > len(flag):
            return a[len(flag):], idx + 1
        if idx + 1 >= len(args):
            err(NAME, f"{flag}: missing argument")
            return None, idx
        return args[idx + 1], idx + 2

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a == "-n" or (a.startswith("-n") and a[2:].isdigit()):
            v, i = _take("-n", a, i)
            if v is None:
                return 2
            n_per_call = int(v)
            continue
        if a == "-L" or (a.startswith("-L") and a[2:].isdigit()):
            v, i = _take("-L", a, i)
            if v is None:
                return 2
            lines_per_call = int(v)
            continue
        if a == "-I":
            v, i = _take("-I", a, i)
            if v is None:
                return 2
            replace_str = v
            continue
        if a == "-d" or a.startswith("-d"):
            v, i = _take("-d", a, i)
            if v is None:
                return 2
            delimiter = v[0] if v else None
            continue
        if a == "-a":
            v, i = _take("-a", a, i)
            if v is None:
                return 2
            input_file = v
            continue
        if a == "-0" or a == "--null":
            null_sep = True
            i += 1
            continue
        if a in ("-r", "--no-run-if-empty"):
            no_run_empty = True
            i += 1
            continue
        if a == "-t":
            trace = True
            i += 1
            continue
        if not a.startswith("-"):
            break
        err(NAME, f"invalid option: {a}")
        return 2

    cmd_template = args[i:]
    if not cmd_template:
        cmd_template = ["echo"]

    # Read input
    if input_file:
        try:
            with open(input_file, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
        except OSError as e:
            err_path(NAME, input_file, e)
            return 1
    else:
        data = sys.stdin.read()

    # Tokenize
    if null_sep:
        tokens = [t for t in data.split("\0") if t]
    elif delimiter is not None:
        tokens = [t for t in data.split(delimiter) if t]
    elif lines_per_call is not None:
        tokens = [ln for ln in data.splitlines() if ln]
    else:
        tokens = _tokenize_shell_like(data)

    if not tokens and no_run_empty:
        return 0

    # With -I, one invocation per token
    if replace_str is not None:
        rc = 0
        for tok in tokens:
            argv_to_run = [a.replace(replace_str, tok) for a in cmd_template]
            if trace:
                sys.stderr.write(" ".join(argv_to_run) + "\n")
            try:
                r = subprocess.call(argv_to_run)
            except OSError as e:
                err(NAME, f"{argv_to_run[0]}: {e}")
                return 127
            if r != 0:
                rc = r
        return rc

    # Group by -n or -L
    batch_size = n_per_call or lines_per_call
    if batch_size is not None and batch_size > 0:
        groups = [tokens[j:j + batch_size] for j in range(0, len(tokens), batch_size)]
    else:
        groups = [tokens] if tokens else ([] if no_run_empty else [[]])

    rc = 0
    for group in groups:
        argv_to_run = cmd_template + list(group)
        if trace:
            sys.stderr.write(" ".join(argv_to_run) + "\n")
        try:
            r = subprocess.call(argv_to_run)
        except OSError as e:
            err(NAME, f"{argv_to_run[0]}: {e}")
            return 127
        if r != 0:
            rc = r
    return rc
