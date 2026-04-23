from __future__ import annotations

import fnmatch
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

from pybox.common import err, err_path

NAME = "find"
ALIASES: list[str] = []
HELP = "search for files in a directory hierarchy"


class Ctx:
    """Evaluation context shared across a single tree walk."""

    def __init__(self, now: float) -> None:
        self.now = now
        self.pruned = False


# ---- AST nodes ---------------------------------------------------------

class Node:
    def eval(self, p: Path, st: os.stat_result, ctx: Ctx) -> bool:
        raise NotImplementedError

    def finalize(self, ctx: Ctx) -> None:
        return None


class AndNode(Node):
    def __init__(self, left: Node, right: Node) -> None:
        self.left, self.right = left, right

    def eval(self, p, st, ctx):
        return self.left.eval(p, st, ctx) and self.right.eval(p, st, ctx)

    def finalize(self, ctx):
        self.left.finalize(ctx)
        self.right.finalize(ctx)


class OrNode(Node):
    def __init__(self, left: Node, right: Node) -> None:
        self.left, self.right = left, right

    def eval(self, p, st, ctx):
        return self.left.eval(p, st, ctx) or self.right.eval(p, st, ctx)

    def finalize(self, ctx):
        self.left.finalize(ctx)
        self.right.finalize(ctx)


class NotNode(Node):
    def __init__(self, inner: Node) -> None:
        self.inner = inner

    def eval(self, p, st, ctx):
        return not self.inner.eval(p, st, ctx)

    def finalize(self, ctx):
        self.inner.finalize(ctx)


class TrueNode(Node):
    def eval(self, p, st, ctx):
        return True


# ---- Tests (predicates) -----------------------------------------------

class NameTest(Node):
    def __init__(self, pat: str, ci: bool = False) -> None:
        self.pat, self.ci = pat, ci

    def eval(self, p, st, ctx):
        n = p.name
        if self.ci:
            return fnmatch.fnmatchcase(n.lower(), self.pat.lower())
        return fnmatch.fnmatchcase(n, self.pat)


class PathTest(Node):
    def __init__(self, pat: str, ci: bool = False) -> None:
        self.pat, self.ci = pat, ci

    def eval(self, p, st, ctx):
        s = str(p)
        if self.ci:
            return fnmatch.fnmatchcase(s.lower(), self.pat.lower())
        return fnmatch.fnmatchcase(s, self.pat)


class TypeTest(Node):
    def __init__(self, t: str) -> None:
        self.t = t

    def eval(self, p, st, ctx):
        if self.t == "f":
            return stat.S_ISREG(st.st_mode)
        if self.t == "d":
            return stat.S_ISDIR(st.st_mode)
        if self.t == "l":
            return stat.S_ISLNK(st.st_mode)
        return False


class SizeTest(Node):
    def __init__(self, cmp_: str, n: int, unit_bytes: int) -> None:
        self.cmp, self.n, self.unit = cmp_, n, unit_bytes

    def eval(self, p, st, ctx):
        size_units = -(-st.st_size // self.unit)  # ceil division
        if self.cmp == "+":
            return size_units > self.n
        if self.cmp == "-":
            return size_units < self.n
        return size_units == self.n


class TimeTest(Node):
    def __init__(self, which: str, unit: str, cmp_: str, n: int) -> None:
        self.which, self.unit, self.cmp, self.n = which, unit, cmp_, n

    def eval(self, p, st, ctx):
        t = {"m": st.st_mtime, "a": st.st_atime, "c": st.st_ctime}[self.which]
        diff = ctx.now - t
        units = int(diff // (86400 if self.unit == "day" else 60))
        if self.cmp == "+":
            return units > self.n
        if self.cmp == "-":
            return units < self.n
        return units == self.n


class NewerTest(Node):
    def __init__(self, ref_mtime: float) -> None:
        self.ref = ref_mtime

    def eval(self, p, st, ctx):
        return st.st_mtime > self.ref


class EmptyTest(Node):
    def eval(self, p, st, ctx):
        if stat.S_ISREG(st.st_mode):
            return st.st_size == 0
        if stat.S_ISDIR(st.st_mode):
            try:
                return not any(True for _ in os.scandir(p))
            except OSError:
                return False
        return False


# ---- Actions -----------------------------------------------------------

class PrintAction(Node):
    def __init__(self, null_sep: bool = False) -> None:
        self.null = null_sep

    def eval(self, p, st, ctx):
        end = "\0" if self.null else "\n"
        sys.stdout.write(str(p) + end)
        return True


class DeleteAction(Node):
    def eval(self, p, st, ctx):
        try:
            if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
                os.rmdir(p)
            else:
                p.unlink()
        except OSError as e:
            err_path(NAME, str(p), e)
            return False
        return True


class PruneAction(Node):
    def eval(self, p, st, ctx):
        ctx.pruned = True
        return True


class ExecAction(Node):
    def __init__(self, cmd: list[str], mode: str) -> None:
        self.cmd = cmd
        self.mode = mode
        self.batch: list[Path] = []

    def eval(self, p, st, ctx):
        if self.mode == ";":
            argv = [str(p) if tok == "{}" else tok for tok in self.cmd]
            try:
                rc = subprocess.call(argv)
            except OSError as e:
                err(NAME, f"exec: {e}")
                return False
            return rc == 0
        self.batch.append(p)
        if len(self.batch) >= 1000:
            self._flush()
        return True

    def _flush(self) -> None:
        if not self.batch:
            return
        argv: list[str] = []
        placeholder = False
        for tok in self.cmd:
            if tok == "{}":
                argv.extend(str(x) for x in self.batch)
                placeholder = True
            else:
                argv.append(tok)
        if not placeholder:
            argv.extend(str(x) for x in self.batch)
        try:
            subprocess.call(argv)
        except OSError as e:
            err(NAME, f"exec: {e}")
        self.batch.clear()

    def finalize(self, ctx):
        if self.mode == "+":
            self._flush()


# ---- Parser ------------------------------------------------------------

class _ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.toks = tokens
        self.i = 0
        self.has_action = False

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def consume(self) -> str:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, tok: str) -> None:
        if self.peek() != tok:
            raise _ParseError(f"expected '{tok}', got '{self.peek()}'")
        self.consume()

    def parse_expr(self) -> Node:
        return self.parse_or()

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.peek() in ("-o", "-or"):
            self.consume()
            right = self.parse_and()
            left = OrNode(left, right)
        return left

    def parse_and(self) -> Node:
        left = self.parse_not()
        while True:
            nxt = self.peek()
            if nxt in ("-a", "-and"):
                self.consume()
                left = AndNode(left, self.parse_not())
            elif nxt is None or nxt in ("-o", "-or", ")"):
                break
            else:
                left = AndNode(left, self.parse_not())
        return left

    def parse_not(self) -> Node:
        if self.peek() in ("-not", "!"):
            self.consume()
            return NotNode(self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> Node:
        if self.peek() == "(":
            self.consume()
            inner = self.parse_expr()
            self.expect(")")
            return inner
        tok = self.consume()

        if tok == "-name":
            return NameTest(self._need_arg(tok))
        if tok == "-iname":
            return NameTest(self._need_arg(tok), ci=True)
        if tok == "-path":
            return PathTest(self._need_arg(tok))
        if tok == "-ipath":
            return PathTest(self._need_arg(tok), ci=True)
        if tok == "-type":
            v = self._need_arg(tok)
            if v not in ("f", "d", "l"):
                raise _ParseError(f"-type: unsupported type '{v}'")
            return TypeTest(v)
        if tok == "-size":
            return self._parse_size()
        if tok in ("-mtime", "-mmin", "-atime", "-amin", "-ctime", "-cmin"):
            return self._parse_time(tok)
        if tok == "-newer":
            ref = self._need_arg(tok)
            try:
                return NewerTest(os.stat(ref).st_mtime)
            except OSError as e:
                raise _ParseError(f"-newer: {ref}: {e.strerror}")
        if tok == "-empty":
            return EmptyTest()
        if tok == "-true":
            return TrueNode()

        # Actions
        if tok == "-print":
            self.has_action = True
            return PrintAction()
        if tok == "-print0":
            self.has_action = True
            return PrintAction(null_sep=True)
        if tok == "-delete":
            self.has_action = True
            return DeleteAction()
        if tok == "-prune":
            return PruneAction()
        if tok == "-exec":
            self.has_action = True
            return self._parse_exec()
        raise _ParseError(f"unknown predicate: '{tok}'")

    def _need_arg(self, flag: str) -> str:
        if self.peek() is None:
            raise _ParseError(f"{flag}: missing argument")
        return self.consume()

    def _parse_size(self) -> Node:
        v = self._need_arg("-size")
        cmp_ = "="
        if v and v[0] in "+-":
            cmp_ = v[0]
            v = v[1:]
        j = 0
        while j < len(v) and v[j].isdigit():
            j += 1
        if j == 0:
            raise _ParseError("-size: invalid value")
        n = int(v[:j])
        suffix = v[j:]
        unit = {
            "": 512, "b": 512, "c": 1, "w": 2,
            "k": 1024, "M": 1024 ** 2, "G": 1024 ** 3,
        }.get(suffix)
        if unit is None:
            raise _ParseError(f"-size: unknown unit '{suffix}'")
        return SizeTest(cmp_, n, unit)

    def _parse_time(self, tok: str) -> Node:
        v = self._need_arg(tok)
        cmp_ = "="
        if v and v[0] in "+-":
            cmp_ = v[0]
            v = v[1:]
        try:
            n = int(v)
        except ValueError:
            raise _ParseError(f"{tok}: invalid value '{v}'")
        which = tok[1]
        unit = "min" if tok.endswith("min") else "day"
        return TimeTest(which, unit, cmp_, n)

    def _parse_exec(self) -> Node:
        cmd: list[str] = []
        while True:
            if self.peek() is None:
                raise _ParseError("-exec: unterminated (expected ';' or '+')")
            t = self.consume()
            if t in (";", "+"):
                return ExecAction(cmd, t)
            cmd.append(t)


def _extract_globals(tokens: list[str]) -> tuple[list[str], int, int] | None:
    mindepth, maxdepth = 0, -1
    remaining: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "-maxdepth" and i + 1 < len(tokens):
            try:
                maxdepth = int(tokens[i + 1])
            except ValueError:
                err(NAME, f"-maxdepth: invalid value '{tokens[i + 1]}'")
                return None
            i += 2
            continue
        if t == "-mindepth" and i + 1 < len(tokens):
            try:
                mindepth = int(tokens[i + 1])
            except ValueError:
                err(NAME, f"-mindepth: invalid value '{tokens[i + 1]}'")
                return None
            i += 2
            continue
        remaining.append(t)
        i += 1
    return remaining, mindepth, maxdepth


def _walk(root: Path, expr: Node, mindepth: int, maxdepth: int, ctx: Ctx) -> int:
    rc = 0

    def visit(p: Path, depth: int) -> None:
        nonlocal rc
        try:
            st = p.lstat()
        except OSError as e:
            err_path(NAME, str(p), e)
            rc = 1
            return
        ctx.pruned = False
        if depth >= mindepth and (maxdepth < 0 or depth <= maxdepth):
            try:
                expr.eval(p, st, ctx)
            except OSError as e:
                err_path(NAME, str(p), e)
                rc = 1
        if ctx.pruned:
            return
        if maxdepth >= 0 and depth >= maxdepth:
            return
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return
        try:
            entries = sorted(os.listdir(p))
        except OSError as e:
            err_path(NAME, str(p), e)
            rc = 1
            return
        for entry in entries:
            visit(p / entry, depth + 1)

    visit(root, 0)
    return rc


def main(argv: list[str]) -> int:
    args = argv[1:]
    paths: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("-") or a in ("(", ")", "!"):
            break
        paths.append(a)
        i += 1
    expr_tokens = args[i:]

    if not paths:
        paths = ["."]

    result = _extract_globals(expr_tokens)
    if result is None:
        return 2
    tokens, mindepth, maxdepth = result

    parser = Parser(tokens)
    try:
        expr: Node = TrueNode() if not tokens else parser.parse_expr()
    except _ParseError as e:
        err(NAME, str(e))
        return 2
    if parser.i != len(tokens):
        err(NAME, f"unexpected token: '{tokens[parser.i]}'")
        return 2

    if not parser.has_action:
        expr = AndNode(expr, PrintAction())

    ctx = Ctx(now=time.time())
    rc = 0
    for p in paths:
        root = Path(p)
        if not root.exists() and not root.is_symlink():
            err_path(NAME, p, FileNotFoundError(2, "No such file or directory"))
            rc = 1
            continue
        r = _walk(root, expr, mindepth, maxdepth, ctx)
        if r != 0:
            rc = r

    expr.finalize(ctx)
    return rc
