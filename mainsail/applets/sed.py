from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from mainsail.common import err, err_path

NAME = "sed"
ALIASES: list[str] = []
HELP = "stream editor: basic s///, d, p, q, =, y and addresses"


# ---- Command model ----------------------------------------------------

@dataclass
class Command:
    op: str
    addr1: str | None = None
    addr2: str | None = None
    negate: bool = False
    pattern: str = ""
    replacement: str = ""
    flags: str = ""
    src: str = ""
    dst: str = ""
    # Cached compiled regex per-line
    _compiled: re.Pattern | None = None


class _SedError(Exception):
    pass


# ---- Regex conversion -------------------------------------------------

_BRE_SWAP = set("(){}+?|")


def _bre_to_python(pattern: str) -> str:
    """Translate basic-regex (escaped metas) to Python's extended regex."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            if nxt in _BRE_SWAP:
                out.append(nxt)  # BRE \( becomes Python (
                i += 2
                continue
            out.append(c + nxt)
            i += 2
            continue
        if c in _BRE_SWAP:
            out.append("\\" + c)  # BRE bare ( is literal
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---- Replacement string handling --------------------------------------

def _sed_replace(match: re.Match, repl: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(repl):
        c = repl[i]
        if c == "\\" and i + 1 < len(repl):
            nxt = repl[i + 1]
            if nxt.isdigit():
                idx = int(nxt)
                if idx == 0:
                    out.append(match.group(0))
                else:
                    try:
                        g = match.group(idx)
                        if g is not None:
                            out.append(g)
                    except (IndexError, re.error):
                        pass
                i += 2
                continue
            if nxt in ("n", "t", "r"):
                out.append({"n": "\n", "t": "\t", "r": "\r"}[nxt])
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            if nxt == "&":
                out.append("&")
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        if c == "&":
            out.append(match.group(0))
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---- Script parser ----------------------------------------------------

def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\n;":
        i += 1
    return i


def _read_delim_part(s: str, i: int, delim: str) -> tuple[str, int]:
    start = i
    while i < len(s) and s[i] != delim:
        if s[i] == "\\" and i + 1 < len(s):
            i += 2
            continue
        i += 1
    return s[start:i], i


def _parse_address(s: str, i: int) -> tuple[str | None, int]:
    if i >= len(s):
        return None, i
    c = s[i]
    if c.isdigit():
        start = i
        while i < len(s) and s[i].isdigit():
            i += 1
        return s[start:i], i
    if c == "$":
        return "$", i + 1
    if c == "/":
        i += 1
        pat, i = _read_delim_part(s, i, "/")
        if i < len(s):
            i += 1
        return "/" + pat + "/", i
    return None, i


def _parse_script(script: str, extended: bool) -> list[Command]:
    cmds: list[Command] = []
    i = 0
    while i < len(script):
        i = _skip_ws(script, i)
        if i >= len(script):
            break

        addr1, i = _parse_address(script, i)
        addr2: str | None = None
        if i < len(script) and script[i] == ",":
            i += 1
            addr2, i = _parse_address(script, i)

        while i < len(script) and script[i] in " \t":
            i += 1
        negate = False
        if i < len(script) and script[i] == "!":
            negate = True
            i += 1
            while i < len(script) and script[i] in " \t":
                i += 1

        if i >= len(script):
            break
        op = script[i]
        i += 1
        cmd = Command(op=op, addr1=addr1, addr2=addr2, negate=negate)

        if op == "s":
            if i >= len(script):
                raise _SedError("s command: missing delimiter")
            delim = script[i]
            i += 1
            cmd.pattern, i = _read_delim_part(script, i, delim)
            if i < len(script):
                i += 1
            cmd.replacement, i = _read_delim_part(script, i, delim)
            if i < len(script):
                i += 1
            fstart = i
            while i < len(script) and script[i] not in " \t\n;":
                i += 1
            cmd.flags = script[fstart:i]
            try:
                py_pat = cmd.pattern if extended else _bre_to_python(cmd.pattern)
                rxflags = re.IGNORECASE if ("i" in cmd.flags or "I" in cmd.flags) else 0
                cmd._compiled = re.compile(py_pat, rxflags)
            except re.error as e:
                raise _SedError(f"bad regex '{cmd.pattern}': {e}")
        elif op == "y":
            if i >= len(script):
                raise _SedError("y command: missing delimiter")
            delim = script[i]
            i += 1
            cmd.src, i = _read_delim_part(script, i, delim)
            if i < len(script):
                i += 1
            cmd.dst, i = _read_delim_part(script, i, delim)
            if i < len(script):
                i += 1
        elif op in ("d", "p", "q", "="):
            pass
        else:
            raise _SedError(f"unsupported command: '{op}'")

        cmds.append(cmd)
    return cmds


# ---- Address evaluation -----------------------------------------------

def _match_addr(addr: str, lineno: int, line: str, last_lineno: int | None) -> bool:
    if addr == "$":
        return last_lineno is not None and lineno == last_lineno
    if addr.isdigit():
        return lineno == int(addr)
    if addr.startswith("/") and addr.endswith("/") and len(addr) >= 2:
        pat = addr[1:-1]
        try:
            return bool(re.search(pat, line))
        except re.error:
            return False
    return False


def _active_for(cmd: Command, lineno: int, line: str, last: int | None, state: dict) -> bool:
    if cmd.addr1 is None:
        base = True
    elif cmd.addr2 is None:
        base = _match_addr(cmd.addr1, lineno, line, last)
    else:
        key = id(cmd)
        in_range = state.get(key, False)
        if not in_range and _match_addr(cmd.addr1, lineno, line, last):
            in_range = True
            state[key] = True
        base = in_range
        if in_range and _match_addr(cmd.addr2, lineno, line, last):
            state[key] = False
    if cmd.negate:
        return not base
    return base


# ---- Execution --------------------------------------------------------

def _run(cmds: list[Command], lines: list[str], quiet: bool) -> list[str]:
    output: list[str] = []
    state: dict = {}
    total = len(lines)
    quitting = False

    for lineno, raw in enumerate(lines, 1):
        if quitting:
            break
        # Ensure each line ends with \n for output consistency; strip for processing
        if raw.endswith("\n"):
            pattern_space = raw[:-1]
            had_nl = True
        else:
            pattern_space = raw
            had_nl = False

        deleted = False

        for cmd in cmds:
            if deleted or quitting:
                break
            if not _active_for(cmd, lineno, pattern_space, total, state):
                continue

            if cmd.op == "s":
                count = 0 if "g" in cmd.flags else 1
                new_space, nsubs = cmd._compiled.subn(
                    lambda m: _sed_replace(m, cmd.replacement),
                    pattern_space,
                    count=count,
                )
                pattern_space = new_space
                if "p" in cmd.flags and nsubs > 0:
                    output.append(pattern_space + "\n")
            elif cmd.op == "d":
                deleted = True
                break
            elif cmd.op == "p":
                output.append(pattern_space + "\n")
            elif cmd.op == "q":
                if not quiet:
                    output.append(pattern_space + ("\n" if had_nl else ""))
                quitting = True
                break
            elif cmd.op == "=":
                output.append(f"{lineno}\n")
            elif cmd.op == "y":
                if len(cmd.src) != len(cmd.dst):
                    raise _SedError("y: source and destination differ in length")
                table = dict(zip(cmd.src, cmd.dst))
                pattern_space = "".join(table.get(c, c) for c in pattern_space)

        if not deleted and not quitting and not quiet:
            output.append(pattern_space + ("\n" if had_nl else ""))

    return output


# ---- Main --------------------------------------------------------------

def main(argv: list[str]) -> int:
    args = argv[1:]
    quiet = False
    in_place = False
    extended = False
    scripts: list[str] = []
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "-n" or a == "--quiet" or a == "--silent":
            quiet = True
            i += 1
            continue
        if a in ("-E", "-r", "--regexp-extended"):
            extended = True
            i += 1
            continue
        if a == "-i" or a == "--in-place":
            in_place = True
            i += 1
            continue
        if a == "-e":
            if i + 1 >= len(args):
                err(NAME, "-e: missing argument")
                return 2
            scripts.append(args[i + 1])
            i += 2
            continue
        if a.startswith("-e"):
            scripts.append(a[2:])
            i += 1
            continue
        if a == "-f":
            if i + 1 >= len(args):
                err(NAME, "-f: missing argument")
                return 2
            try:
                with open(args[i + 1], "r", encoding="utf-8") as fh:
                    scripts.append(fh.read())
            except OSError as e:
                err_path(NAME, args[i + 1], e)
                return 1
            i += 2
            continue
        if a.startswith("-") and len(a) > 1 and a != "-":
            err(NAME, f"invalid option: {a}")
            return 2
        break

    positional = args[i:]
    if not scripts:
        if not positional:
            err(NAME, "missing script")
            return 2
        scripts.append(positional[0])
        positional = positional[1:]
    files.extend(positional)

    script = "\n".join(scripts)

    try:
        cmds = _parse_script(script, extended)
    except _SedError as e:
        err(NAME, str(e))
        return 2

    if not files:
        files = ["-"]

    rc = 0
    if in_place and "-" in files:
        err(NAME, "-i cannot be used with stdin")
        return 2

    for f in files:
        try:
            if f == "-":
                lines = sys.stdin.readlines()
            else:
                with open(f, "r", encoding="utf-8", errors="replace", newline="") as fh:
                    lines = fh.readlines()
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue

        try:
            out_lines = _run(cmds, lines, quiet)
        except _SedError as e:
            err(NAME, str(e))
            return 2

        if in_place:
            tmp = Path(f).with_suffix(Path(f).suffix + ".mainsail_tmp")
            try:
                with open(tmp, "w", encoding="utf-8", newline="") as wh:
                    wh.writelines(out_lines)
                os.replace(tmp, f)
            except OSError as e:
                err_path(NAME, f, e)
                try:
                    tmp.unlink()
                except OSError:
                    pass
                rc = 1
        else:
            for line in out_lines:
                sys.stdout.write(line)

    return rc
