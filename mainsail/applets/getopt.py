"""mainsail getopt — POSIX/GNU-style option parser for shell scripts.

Designed to be source-quoted into shell scripts:

    PARSED=$(mainsail getopt -o vh:o:: --long verbose,help:,output:: -- "$@")
    eval set -- "$PARSED"

We implement the GNU enhanced (default) form. The output is
shell-quoted via Python's shlex.quote so it can be `eval`-ed safely.
"""
from __future__ import annotations

import shlex
import sys

from mainsail.common import err

NAME = "getopt"
ALIASES: list[str] = []
HELP = "parse command-line options for shell scripts"


def main(argv: list[str]) -> int:
    args = argv[1:]
    short_opts = ""
    long_opts: list[str] = []
    options_first = False
    quoted_style = "shell"  # we always shell-quote the output

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-o", "--options"} and i + 1 < len(args):
            short_opts = args[i + 1]
            i += 2
            continue
        if a.startswith("-o"):
            short_opts = a[2:]
            i += 1
            continue
        if a in {"-l", "--longoptions", "--long"} and i + 1 < len(args):
            long_opts.extend(p for p in args[i + 1].split(",") if p)
            i += 2
            continue
        if a.startswith("--longoptions=") or a.startswith("--long="):
            long_opts.extend(p for p in a.split("=", 1)[1].split(",") if p)
            i += 1
            continue
        if a == "--":
            i += 1
            break
        if a == "-q" or a == "--quiet":
            i += 1
            continue
        if a == "-T" or a == "--test":
            # GNU: exit 4 to signal "enhanced getopt is available"
            return 4
        if a == "-a" or a == "--alternative":
            # accept; we don't strictly require -- to start long
            i += 1
            continue
        if a == "-u" or a == "--unquoted":
            quoted_style = "raw"
            i += 1
            continue
        if a == "-s" or a == "--shell":
            i += 2 if i + 1 < len(args) else 1
            continue
        if a == "+":
            options_first = True
            i += 1
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    inputs = args[i:]
    parsed_opts: list[tuple[str, str | None]] = []
    operands: list[str] = []
    short_map = _parse_short(short_opts)
    long_map = _parse_long(long_opts)

    j = 0
    while j < len(inputs):
        arg = inputs[j]
        if arg == "--":
            operands.extend(inputs[j + 1:])
            break
        if arg.startswith("--") and len(arg) > 2:
            name = arg[2:]
            value = None
            if "=" in name:
                name, value = name.split("=", 1)
            arg_kind = long_map.get(name)
            if arg_kind is None:
                # Try prefix match
                matches = [k for k in long_map if k.startswith(name)]
                if len(matches) == 1:
                    name = matches[0]
                    arg_kind = long_map[name]
                else:
                    err(NAME, f"unrecognized option '--{name}'")
                    return 1
            if arg_kind == "required":
                if value is None:
                    if j + 1 >= len(inputs):
                        err(NAME, f"option '--{name}' requires an argument")
                        return 1
                    j += 1
                    value = inputs[j]
                parsed_opts.append((f"--{name}", value))
            elif arg_kind == "optional":
                parsed_opts.append((f"--{name}", value))
            else:
                if value is not None:
                    err(NAME, f"option '--{name}' doesn't allow an argument")
                    return 1
                parsed_opts.append((f"--{name}", None))
            j += 1
            continue
        if arg.startswith("-") and len(arg) > 1 and arg != "-":
            # Bundled short opts
            k = 1
            while k < len(arg):
                ch = arg[k]
                kind = short_map.get(ch)
                if kind is None:
                    err(NAME, f"invalid option -- '{ch}'")
                    return 1
                if kind == "required":
                    if k + 1 < len(arg):
                        parsed_opts.append((f"-{ch}", arg[k + 1:]))
                        k = len(arg)
                    else:
                        if j + 1 >= len(inputs):
                            err(NAME, f"option requires an argument -- '{ch}'")
                            return 1
                        j += 1
                        parsed_opts.append((f"-{ch}", inputs[j]))
                        k = len(arg)
                elif kind == "optional":
                    if k + 1 < len(arg):
                        parsed_opts.append((f"-{ch}", arg[k + 1:]))
                        k = len(arg)
                    else:
                        parsed_opts.append((f"-{ch}", None))
                        k += 1
                else:
                    parsed_opts.append((f"-{ch}", None))
                    k += 1
            j += 1
            continue
        # Non-option argument
        if options_first:
            operands.extend(inputs[j:])
            break
        operands.append(arg)
        j += 1

    # Emit
    parts: list[str] = []
    for name, value in parsed_opts:
        parts.append(name)
        if value is not None:
            parts.append(value)
    parts.append("--")
    parts.extend(operands)

    if quoted_style == "shell":
        sys.stdout.write(" ".join(shlex.quote(p) for p in parts) + "\n")
    else:
        sys.stdout.write(" ".join(parts) + "\n")
    sys.stdout.flush()
    return 0


def _parse_short(spec: str) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch == ":":
            i += 1
            continue
        kind = "none"
        if i + 1 < len(spec) and spec[i + 1] == ":":
            if i + 2 < len(spec) and spec[i + 2] == ":":
                kind = "optional"
                i += 3
            else:
                kind = "required"
                i += 2
        else:
            i += 1
        out[ch] = kind
    return out


def _parse_long(opts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for o in opts:
        if o.endswith("::"):
            out[o[:-2]] = "optional"
        elif o.endswith(":"):
            out[o[:-1]] = "required"
        else:
            out[o] = "none"
    return out
