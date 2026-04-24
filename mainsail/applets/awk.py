"""mainsail awk applet.

Supports a practical POSIX-awk subset:
  - BEGIN / END blocks
  - /regex/ patterns, expression patterns, range patterns (p1, p2)
  - print, printf with %d %i %o %x %X %f %e %E %g %G %s %c specifiers
  - Control flow: if/else, while, do/while, for(;;), for (k in a),
    break, continue, next, exit
  - Associative arrays, delete, `k in a`
  - Field access ($0, $NF, $(expr)), NR, NF, FS, OFS, ORS, RS, FILENAME
  - String operators (juxtaposition), arithmetic, comparison, ~ !~,
    &&/||/!, ternary ?:, assignments (=, +=, -=, *=, /=, %=, ^=)
  - Built-in functions: length, substr, index, split, sub, gsub,
    match, toupper, tolower, sprintf, int, sqrt, log, exp, sin, cos,
    atan2, rand, srand, system

Not implemented (v1):
  - user-defined functions
  - getline (tokenized, then errors)
  - true multidimensional arrays (SUBSEP)
  - regex FS (FS is a literal single char unless blank, where it
    defaults to awk's split-on-any-whitespace)
"""
from __future__ import annotations

import math
import os
import random
import re
import sys
from pathlib import Path

from mainsail.common import err

NAME = "awk"
ALIASES: list[str] = []
HELP = "pattern-scanning and processing language"


# ────────────────────────────────────────────────────────────────────
# Errors
# ────────────────────────────────────────────────────────────────────

class _AwkError(Exception):
    pass


class _NextRecord(Exception):
    pass


class _ExitProgram(Exception):
    def __init__(self, code: int = 0) -> None:
        self.code = code


class _BreakLoop(Exception):
    pass


class _ContinueLoop(Exception):
    pass


# ────────────────────────────────────────────────────────────────────
# Lexer
# ────────────────────────────────────────────────────────────────────

KEYWORDS = {
    "BEGIN", "END", "if", "else", "while", "for", "do", "in",
    "print", "printf", "next", "exit", "break", "continue",
    "delete", "function", "return", "getline",
}

_MULTI_OPS = {
    "==", "!=", "<=", ">=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "^=", "**", "!~",
}

_SINGLE_OPS = set("+-*%^=<>!~,;(){}[]?:$")


class Lexer:
    def __init__(self, src: str) -> None:
        self.src = src
        self.i = 0
        self.line = 1
        self.tokens: list[tuple[str, object, int]] = []
        self._run()

    def _run(self) -> None:
        prev: str | None = None
        while self.i < len(self.src):
            c = self.src[self.i]
            if c == "#":
                while self.i < len(self.src) and self.src[self.i] != "\n":
                    self.i += 1
                continue
            if c in " \t":
                self.i += 1
                continue
            if c == "\\" and self.i + 1 < len(self.src) and self.src[self.i + 1] == "\n":
                self.i += 2
                self.line += 1
                continue
            if c == "\n":
                self.tokens.append(("NEWLINE", "\n", self.line))
                self.i += 1
                self.line += 1
                prev = "NEWLINE"
                continue
            if c.isdigit() or (c == "." and self.i + 1 < len(self.src) and self.src[self.i + 1].isdigit()):
                self.tokens.append(("NUMBER", self._number(), self.line))
                prev = "NUMBER"
                continue
            if c == '"':
                self.tokens.append(("STRING", self._string(), self.line))
                prev = "STRING"
                continue
            if c.isalpha() or c == "_":
                name = self._name()
                if name in KEYWORDS:
                    self.tokens.append((name, name, self.line))
                    prev = name
                else:
                    self.tokens.append(("NAME", name, self.line))
                    prev = "NAME"
                continue
            if c == "/":
                if self._regex_context(prev):
                    self.tokens.append(("REGEX", self._regex(), self.line))
                    prev = "REGEX"
                    continue
                if self.i + 1 < len(self.src) and self.src[self.i + 1] == "=":
                    self.tokens.append(("/=", "/=", self.line))
                    self.i += 2
                    prev = "/="
                else:
                    self.tokens.append(("/", "/", self.line))
                    self.i += 1
                    prev = "/"
                continue
            two = self.src[self.i:self.i + 2]
            if two in _MULTI_OPS:
                self.tokens.append((two, two, self.line))
                self.i += 2
                prev = two
                continue
            if c in _SINGLE_OPS:
                self.tokens.append((c, c, self.line))
                self.i += 1
                prev = c
                continue
            raise _AwkError(f"unexpected character {c!r} at line {self.line}")
        self.tokens.append(("EOF", None, self.line))

    @staticmethod
    def _regex_context(prev: str | None) -> bool:
        # A slash starts a regex unless immediately after a value-producing
        # token, where it's division.
        if prev is None:
            return True
        if prev in {"NUMBER", "STRING", "NAME", "REGEX", ")", "]"}:
            return False
        if prev in {"++", "--"}:
            # postfix inc/dec -> the ++/-- produced a value
            return False
        return True

    def _number(self) -> float | int:
        start = self.i
        while self.i < len(self.src) and (self.src[self.i].isdigit() or self.src[self.i] == "."):
            self.i += 1
        has_exp = False
        if self.i < len(self.src) and self.src[self.i] in "eE":
            has_exp = True
            self.i += 1
            if self.i < len(self.src) and self.src[self.i] in "+-":
                self.i += 1
            while self.i < len(self.src) and self.src[self.i].isdigit():
                self.i += 1
        s = self.src[start:self.i]
        if "." in s or has_exp:
            return float(s)
        return int(s)

    def _string(self) -> str:
        self.i += 1
        out: list[str] = []
        while self.i < len(self.src) and self.src[self.i] != '"':
            c = self.src[self.i]
            if c == "\\" and self.i + 1 < len(self.src):
                n = self.src[self.i + 1]
                escape = {
                    "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                    '"': '"', "/": "/", "a": "\a", "b": "\b",
                    "f": "\f", "v": "\v",
                }.get(n)
                out.append(escape if escape is not None else n)
                self.i += 2
                continue
            if c == "\n":
                self.line += 1
            out.append(c)
            self.i += 1
        if self.i >= len(self.src):
            raise _AwkError("unterminated string")
        self.i += 1
        return "".join(out)

    def _regex(self) -> str:
        self.i += 1
        out: list[str] = []
        while self.i < len(self.src) and self.src[self.i] != "/":
            c = self.src[self.i]
            if c == "\\" and self.i + 1 < len(self.src):
                n = self.src[self.i + 1]
                if n == "/":
                    out.append("/")
                else:
                    out.append(c)
                    out.append(n)
                self.i += 2
                continue
            if c == "\n":
                raise _AwkError("regex may not span lines")
            out.append(c)
            self.i += 1
        if self.i >= len(self.src):
            raise _AwkError("unterminated regex")
        self.i += 1
        return "".join(out)

    def _name(self) -> str:
        start = self.i
        while self.i < len(self.src) and (self.src[self.i].isalnum() or self.src[self.i] == "_"):
            self.i += 1
        return self.src[start:self.i]


# ────────────────────────────────────────────────────────────────────
# AST nodes (as plain tuples/classes)
# ────────────────────────────────────────────────────────────────────

class Node:
    __slots__ = ()


class Num(Node):
    __slots__ = ("v",)
    def __init__(self, v): self.v = v


class Str(Node):
    __slots__ = ("v",)
    def __init__(self, v): self.v = v


class Regex(Node):
    __slots__ = ("pattern",)
    def __init__(self, p): self.pattern = p


class Name(Node):
    __slots__ = ("name",)
    def __init__(self, n): self.name = n


class Field(Node):
    __slots__ = ("expr",)
    def __init__(self, e): self.expr = e


class Binary(Node):
    __slots__ = ("op", "a", "b")
    def __init__(self, op, a, b): self.op, self.a, self.b = op, a, b


class Unary(Node):
    __slots__ = ("op", "a")
    def __init__(self, op, a): self.op, self.a = op, a


class Inc(Node):
    __slots__ = ("op", "target", "post")
    def __init__(self, op, target, post): self.op, self.target, self.post = op, target, post


class Concat(Node):
    __slots__ = ("a", "b")
    def __init__(self, a, b): self.a, self.b = a, b


class Match(Node):
    __slots__ = ("expr", "regex", "negate")
    def __init__(self, e, r, negate=False): self.expr, self.regex, self.negate = e, r, negate


class InArr(Node):
    __slots__ = ("key", "arr")
    def __init__(self, k, a): self.key, self.arr = k, a


class Cond(Node):
    __slots__ = ("c", "t", "f")
    def __init__(self, c, t, f): self.c, self.t, self.f = c, t, f


class Assign(Node):
    __slots__ = ("target", "op", "value")
    def __init__(self, t, op, v): self.target, self.op, self.value = t, op, v


class Index(Node):
    __slots__ = ("arr", "key")
    def __init__(self, a, k): self.arr, self.key = a, k


class Call(Node):
    __slots__ = ("name", "args")
    def __init__(self, n, a): self.name, self.args = n, a


class Group(Node):
    __slots__ = ("expr",)
    def __init__(self, e): self.expr = e


# Statements

class Print(Node):
    __slots__ = ("args",)
    def __init__(self, args): self.args = args


class Printf(Node):
    __slots__ = ("args",)
    def __init__(self, args): self.args = args


class ExprStmt(Node):
    __slots__ = ("expr",)
    def __init__(self, e): self.expr = e


class If(Node):
    __slots__ = ("cond", "then", "els")
    def __init__(self, c, t, e): self.cond, self.then, self.els = c, t, e


class While(Node):
    __slots__ = ("cond", "body")
    def __init__(self, c, b): self.cond, self.body = c, b


class DoWhile(Node):
    __slots__ = ("body", "cond")
    def __init__(self, b, c): self.body, self.cond = b, c


class For(Node):
    __slots__ = ("init", "cond", "step", "body")
    def __init__(self, i, c, s, b): self.init, self.cond, self.step, self.body = i, c, s, b


class ForIn(Node):
    __slots__ = ("var", "arr", "body")
    def __init__(self, v, a, b): self.var, self.arr, self.body = v, a, b


class Block(Node):
    __slots__ = ("stmts",)
    def __init__(self, s): self.stmts = s


class Next(Node):
    __slots__ = ()


class Exit(Node):
    __slots__ = ("expr",)
    def __init__(self, e): self.expr = e


class Break(Node):
    __slots__ = ()


class Continue(Node):
    __slots__ = ()


class Delete(Node):
    __slots__ = ("target",)
    def __init__(self, t): self.target = t


# Top-level

class Rule(Node):
    __slots__ = ("kind", "pattern", "pattern2", "action")
    # kind: "BEGIN", "END", "main", "range"
    def __init__(self, kind, p, p2, a):
        self.kind, self.pattern, self.pattern2, self.action = kind, p, p2, a


class Program(Node):
    __slots__ = ("rules",)
    def __init__(self, rs): self.rules = rs


# ────────────────────────────────────────────────────────────────────
# Parser
# ────────────────────────────────────────────────────────────────────

_VALUE_START = {"NUMBER", "STRING", "NAME", "REGEX", "$", "(", "!", "-", "+", "++", "--"}


class Parser:
    def __init__(self, tokens: list[tuple[str, object, int]]) -> None:
        self.t = tokens
        self.i = 0

    def peek(self, off: int = 0) -> str:
        return self.t[self.i + off][0]

    def peek_val(self) -> object:
        return self.t[self.i][1]

    def line(self) -> int:
        return self.t[self.i][2]

    def advance(self) -> tuple[str, object, int]:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def eat(self, kind: str) -> tuple[str, object, int]:
        if self.peek() != kind:
            raise _AwkError(f"expected {kind!r}, got {self.peek()!r} at line {self.line()}")
        return self.advance()

    def accept(self, *kinds: str) -> bool:
        if self.peek() in kinds:
            self.advance()
            return True
        return False

    def skip_terminators(self) -> None:
        while self.peek() in {"NEWLINE", ";"}:
            self.advance()

    # ---- program ---------------------------------------------------

    def parse_program(self) -> Program:
        rules: list[Rule] = []
        self.skip_terminators()
        while self.peek() != "EOF":
            rules.append(self._parse_rule())
            self.skip_terminators()
        return Program(rules)

    def _parse_rule(self) -> Rule:
        # Rule forms:
        #   BEGIN { ... }
        #   END { ... }
        #   /re/ [{ ... }]
        #   expr [{ ... }]
        #   expr , expr [{ ... }]
        #   { ... }          (no pattern = always)
        if self.peek() == "BEGIN":
            self.advance()
            return Rule("BEGIN", None, None, self._parse_action(required=True))
        if self.peek() == "END":
            self.advance()
            return Rule("END", None, None, self._parse_action(required=True))
        if self.peek() == "{":
            return Rule("main", None, None, self._parse_action(required=True))
        # pattern
        p1 = self._parse_expr()
        p2 = None
        kind = "main"
        if self.peek() == ",":
            self.advance()
            p2 = self._parse_expr()
            kind = "range"
        action = self._parse_action(required=False)
        return Rule(kind, p1, p2, action)

    def _parse_action(self, *, required: bool) -> list[Node] | None:
        if self.peek() != "{":
            if required:
                raise _AwkError(f"expected {{ at line {self.line()}")
            return None
        self.eat("{")
        stmts = self._parse_stmts()
        self.eat("}")
        return stmts

    # ---- statements -------------------------------------------------

    def _parse_stmts(self) -> list[Node]:
        stmts: list[Node] = []
        self.skip_terminators()
        while self.peek() not in {"}", "EOF"}:
            stmts.append(self._parse_stmt())
            if self.peek() in {";", "NEWLINE"}:
                self.skip_terminators()
            elif self.peek() in {"}", "EOF"}:
                pass
            else:
                # statements can butt up against } without terminator
                pass
        return stmts

    def _parse_stmt(self) -> Node:
        tok = self.peek()
        if tok == "{":
            self.advance()
            body = self._parse_stmts()
            self.eat("}")
            return Block(body)
        if tok == "if":
            return self._parse_if()
        if tok == "while":
            return self._parse_while()
        if tok == "do":
            return self._parse_do()
        if tok == "for":
            return self._parse_for()
        if tok == "print":
            self.advance()
            return self._parse_print_args(printf=False)
        if tok == "printf":
            self.advance()
            return self._parse_print_args(printf=True)
        if tok == "next":
            self.advance()
            return Next()
        if tok == "exit":
            self.advance()
            e = None
            if self.peek() not in {";", "NEWLINE", "}", "EOF"}:
                e = self._parse_expr()
            return Exit(e)
        if tok == "break":
            self.advance()
            return Break()
        if tok == "continue":
            self.advance()
            return Continue()
        if tok == "delete":
            self.advance()
            target = self._parse_primary_lhs()
            return Delete(target)
        if tok == "getline":
            raise _AwkError("getline is not supported in this awk")
        # fallback: expression statement
        e = self._parse_expr()
        return ExprStmt(e)

    def _parse_if(self) -> Node:
        self.eat("if")
        self.eat("(")
        cond = self._parse_expr()
        self.eat(")")
        self.skip_terminators()
        then = self._parse_stmt()
        els = None
        # allow ; or newline before else
        saved = self.i
        while self.peek() in {";", "NEWLINE"}:
            self.advance()
        if self.peek() == "else":
            self.advance()
            self.skip_terminators()
            els = self._parse_stmt()
        else:
            self.i = saved
        return If(cond, then, els)

    def _parse_while(self) -> Node:
        self.eat("while")
        self.eat("(")
        cond = self._parse_expr()
        self.eat(")")
        self.skip_terminators()
        body = self._parse_stmt()
        return While(cond, body)

    def _parse_do(self) -> Node:
        self.eat("do")
        self.skip_terminators()
        body = self._parse_stmt()
        while self.peek() in {";", "NEWLINE"}:
            self.advance()
        self.eat("while")
        self.eat("(")
        cond = self._parse_expr()
        self.eat(")")
        return DoWhile(body, cond)

    def _parse_for(self) -> Node:
        self.eat("for")
        self.eat("(")
        # Two forms: for (k in arr) body OR for (init; cond; step) body
        saved = self.i
        # Try for-in: NAME in NAME )
        if self.peek() == "NAME" and self.peek(1) == "in" and self.peek(2) == "NAME" and self.peek(3) == ")":
            var = self.advance()[1]
            self.advance()  # in
            arrtok = self.advance()
            self.eat(")")
            self.skip_terminators()
            body = self._parse_stmt()
            return ForIn(var, arrtok[1], body)
        # also for ((k in arr)) body
        if self.peek() == "(" and self.peek(1) == "NAME" and self.peek(2) == "in" and self.peek(3) == "NAME" and self.peek(4) == ")" and self.peek(5) == ")":
            self.advance()
            var = self.advance()[1]
            self.advance()
            arrtok = self.advance()
            self.eat(")")
            self.eat(")")
            self.skip_terminators()
            body = self._parse_stmt()
            return ForIn(var, arrtok[1], body)
        self.i = saved
        init = None
        if self.peek() != ";":
            init = self._parse_expr()
        self.eat(";")
        cond = None
        if self.peek() != ";":
            cond = self._parse_expr()
        self.eat(";")
        step = None
        if self.peek() != ")":
            step = self._parse_expr()
        self.eat(")")
        self.skip_terminators()
        body = self._parse_stmt()
        return For(init, cond, step, body)

    def _parse_print_args(self, *, printf: bool) -> Node:
        args: list[Node] = []
        if self.peek() not in {";", "NEWLINE", "}", "EOF"}:
            args.append(self._parse_expr())
            while self.peek() == ",":
                self.advance()
                args.append(self._parse_expr())
        if printf:
            return Printf(args)
        return Print(args)

    # ---- expressions: precedence climbing --------------------------
    # Precedence (low to high):
    #   1. assignment (right)
    #   2. conditional ?:  (right)
    #   3. logical ||
    #   4. logical &&
    #   5. `in` (key in arr)
    #   6. match ~, !~
    #   7. relational  < <= > >= == !=
    #   8. concat (juxtaposition)
    #   9. additive + -
    #  10. multiplicative * / %
    #  11. unary !, unary +/-, prefix ++/--
    #  12. power ^ **   (right)
    #  13. postfix ++/--
    #  14. field $
    #  15. primary

    def _parse_expr(self) -> Node:
        return self._parse_assign()

    def _parse_assign(self) -> Node:
        left = self._parse_cond()
        if self.peek() in {"=", "+=", "-=", "*=", "/=", "%=", "^="}:
            op = self.advance()[0]
            value = self._parse_assign()
            if not isinstance(left, (Name, Field, Index)):
                raise _AwkError("invalid assignment target")
            return Assign(left, op, value)
        return left

    def _parse_cond(self) -> Node:
        c = self._parse_or()
        if self.peek() == "?":
            self.advance()
            t = self._parse_assign()
            self.eat(":")
            f = self._parse_assign()
            return Cond(c, t, f)
        return c

    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self.peek() == "||":
            self.advance()
            right = self._parse_and()
            left = Binary("||", left, right)
        return left

    def _parse_and(self) -> Node:
        left = self._parse_in()
        while self.peek() == "&&":
            self.advance()
            right = self._parse_in()
            left = Binary("&&", left, right)
        return left

    def _parse_in(self) -> Node:
        left = self._parse_match()
        while self.peek() == "in":
            self.advance()
            arrtok = self.eat("NAME")
            left = InArr(left, arrtok[1])
        return left

    def _parse_match(self) -> Node:
        left = self._parse_rel()
        while self.peek() in {"~", "!~"}:
            op = self.advance()[0]
            right = self._parse_rel()
            left = Match(left, right, negate=(op == "!~"))
        return left

    def _parse_rel(self) -> Node:
        left = self._parse_concat()
        if self.peek() in {"<", "<=", ">", ">=", "==", "!="}:
            op = self.advance()[0]
            right = self._parse_concat()
            left = Binary(op, left, right)
        return left

    def _parse_concat(self) -> Node:
        left = self._parse_add()
        while self.peek() in _VALUE_START and self.peek() not in {"-", "+", "!"}:
            # concat is juxtaposition; don't consume -/+ which could be
            # start of additive (already handled) — avoid ambiguity.
            # The only runs we concat are those starting with NUMBER,
            # STRING, NAME, REGEX, $, (, ++, --.
            right = self._parse_add()
            left = Concat(left, right)
        return left

    def _parse_add(self) -> Node:
        left = self._parse_mul()
        while self.peek() in {"+", "-"}:
            op = self.advance()[0]
            right = self._parse_mul()
            left = Binary(op, left, right)
        return left

    def _parse_mul(self) -> Node:
        left = self._parse_unary()
        while self.peek() in {"*", "/", "%"}:
            op = self.advance()[0]
            right = self._parse_unary()
            left = Binary(op, left, right)
        return left

    def _parse_unary(self) -> Node:
        if self.peek() == "!":
            self.advance()
            return Unary("!", self._parse_unary())
        if self.peek() == "-":
            self.advance()
            return Unary("-", self._parse_unary())
        if self.peek() == "+":
            self.advance()
            return Unary("+", self._parse_unary())
        if self.peek() in {"++", "--"}:
            op = self.advance()[0]
            target = self._parse_unary()
            return Inc(op, target, post=False)
        return self._parse_pow()

    def _parse_pow(self) -> Node:
        left = self._parse_postfix()
        if self.peek() in {"^", "**"}:
            self.advance()
            right = self._parse_unary()  # right-associative
            return Binary("^", left, right)
        return left

    def _parse_postfix(self) -> Node:
        left = self._parse_field()
        while self.peek() in {"++", "--"}:
            op = self.advance()[0]
            left = Inc(op, left, post=True)
        return left

    def _parse_field(self) -> Node:
        if self.peek() == "$":
            self.advance()
            # $ binds to a single primary / field — no unary ops
            inner = self._parse_field()
            return Field(inner)
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        t = self.peek()
        if t == "NUMBER":
            return Num(self.advance()[1])
        if t == "STRING":
            return Str(self.advance()[1])
        if t == "REGEX":
            return Regex(self.advance()[1])
        if t == "(":
            self.advance()
            e = self._parse_expr()
            self.eat(")")
            return Group(e)
        if t == "NAME":
            name = self.advance()[1]
            if self.peek() == "(":
                self.advance()
                args: list[Node] = []
                if self.peek() != ")":
                    args.append(self._parse_expr())
                    while self.peek() == ",":
                        self.advance()
                        args.append(self._parse_expr())
                self.eat(")")
                return Call(name, args)
            if self.peek() == "[":
                self.advance()
                key = self._parse_expr()
                while self.peek() == ",":
                    # multidim: join with SUBSEP (chr 28)
                    self.advance()
                    more = self._parse_expr()
                    key = Binary("CONCAT_SUBSEP", key, more)
                self.eat("]")
                return Index(name, key)
            return Name(name)
        raise _AwkError(f"unexpected token {t!r} at line {self.line()}")

    def _parse_primary_lhs(self) -> Node:
        # for `delete`: target is NAME or NAME[k]
        name = self.eat("NAME")[1]
        if self.peek() == "[":
            self.advance()
            key = self._parse_expr()
            while self.peek() == ",":
                self.advance()
                more = self._parse_expr()
                key = Binary("CONCAT_SUBSEP", key, more)
            self.eat("]")
            return Index(name, key)
        return Name(name)


# ────────────────────────────────────────────────────────────────────
# Interpreter
# ────────────────────────────────────────────────────────────────────

SUBSEP = "\x1c"


def to_num(v) -> float:
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    # Parse longest numeric prefix
    m = re.match(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", s)
    if not m:
        return 0.0
    try:
        return float(m.group(0))
    except ValueError:
        return 0.0


def to_str(v, ofmt: str = "%.6g") -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e16:
            return str(int(v))
        return ofmt % v
    return str(v)


def to_bool(v) -> bool:
    if v is None or v == "":
        return False
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v)
    if s == "":
        return False
    # In awk, a numeric-string that looks like a number is truthy only
    # if its numeric value is nonzero. For plain strings, nonempty = true.
    return True


class Interp:
    def __init__(self, program: Program, *, fs: str | None = None,
                 vars_preset: dict[str, object] | None = None,
                 files: list[str] | None = None) -> None:
        self.program = program
        self.globals: dict[str, object] = {}
        self.arrays: dict[str, dict[str, object]] = {}
        self.fields: list[str] = [""]  # fields[0] = $0, fields[1] = $1, ...
        self.NR = 0
        self.NF = 0
        self.FNR = 0
        self.FILENAME = ""
        self.FS = fs if fs is not None else " "
        self.OFS = " "
        self.ORS = "\n"
        self.RS = "\n"
        self.SUBSEP = SUBSEP
        self.OFMT = "%.6g"
        self.CONVFMT = "%.6g"
        self.range_active: dict[int, bool] = {}
        self.exit_code: int | None = None
        self.files = files or []
        if vars_preset:
            for k, v in vars_preset.items():
                self.globals[k] = v

    # ---- field / record --------------------------------------------

    def set_record(self, line: str) -> None:
        self.fields = [line] + self._split_fields(line)
        self.NF = len(self.fields) - 1

    def _split_fields(self, line: str) -> list[str]:
        if self.FS == " ":
            # default: split on runs of whitespace, strip leading/trailing
            return line.split() if line else []
        if len(self.FS) == 1:
            return line.split(self.FS) if line != "" else [""]
        # multi-char FS: treat as regex (POSIX awk)
        if self.FS == "":
            return list(line)
        try:
            return re.split(self.FS, line)
        except re.error:
            return line.split(self.FS)

    def rebuild_line(self) -> None:
        self.fields[0] = self.OFS.join(self.fields[1:])

    def set_field(self, n: int, val) -> None:
        s = to_str(val, self.OFMT)
        if n == 0:
            self.set_record(s)
            return
        while len(self.fields) <= n:
            self.fields.append("")
        self.fields[n] = s
        self.NF = len(self.fields) - 1
        self.rebuild_line()

    def get_field(self, n: int) -> str:
        if n == 0:
            return self.fields[0]
        if n < 0:
            raise _AwkError(f"negative field index: {n}")
        if n >= len(self.fields):
            return ""
        return self.fields[n]

    # ---- execution --------------------------------------------------

    def run(self) -> int:
        try:
            # BEGIN rules
            for rule in self.program.rules:
                if rule.kind == "BEGIN":
                    self._exec_stmts(rule.action or [])

            # Main loop (only if there are non-BEGIN/END rules OR files OR stdin)
            has_main = any(r.kind in {"main", "range"} for r in self.program.rules)

            if has_main or (not self.files and self._any_end()):
                self._process_input()
            elif has_main:
                self._process_input()

            # Even with no main rules, if files are given we still iterate
            if not has_main and self.files:
                self._process_input()

            # END rules
            for rule in self.program.rules:
                if rule.kind == "END":
                    self._exec_stmts(rule.action or [])
        except _ExitProgram as ex:
            # END still runs after exit in awk
            if self.exit_code is None:
                self.exit_code = ex.code
            try:
                for rule in self.program.rules:
                    if rule.kind == "END":
                        self._exec_stmts(rule.action or [])
            except _ExitProgram as ex2:
                self.exit_code = ex2.code
        return self.exit_code if self.exit_code is not None else 0

    def _any_end(self) -> bool:
        return any(r.kind == "END" for r in self.program.rules)

    def _process_input(self) -> None:
        # BEGIN may have set output buffering expectations; we always
        # write to sys.stdout as text.
        sources: list[tuple[str, any]] = []
        if not self.files:
            sources.append(("-", sys.stdin))
        else:
            for f in self.files:
                sources.append((f, None))
        for name, handle in sources:
            self.FILENAME = name
            self.FNR = 0
            if handle is None:
                try:
                    fh = open(name, "r", encoding="utf-8", newline="", errors="replace")
                except OSError as e:
                    err("awk", f"{name}: {e.strerror or e}")
                    self.exit_code = 2
                    continue
                close_it = True
            else:
                fh = handle
                close_it = False
            try:
                # Record splitting: awk default RS is newline.
                # Use readline() rather than iteration so the test stdin
                # mock (no __iter__) still works.
                if self.RS == "\n":
                    while True:
                        raw = fh.readline()
                        if not raw:
                            break
                        line = raw.rstrip("\n").rstrip("\r")
                        self._process_record(line)
                else:
                    data = fh.read()
                    records = data.split(self.RS) if self.RS else list(data)
                    if records and records[-1] == "":
                        records.pop()
                    for rec in records:
                        self._process_record(rec)
            finally:
                if close_it:
                    fh.close()

    def _process_record(self, line: str) -> None:
        self.NR += 1
        self.FNR += 1
        self.set_record(line)
        try:
            for idx, rule in enumerate(self.program.rules):
                if rule.kind == "main":
                    if rule.pattern is None or to_bool(self._eval(rule.pattern)):
                        if rule.action is None:
                            # pattern with no action → print
                            sys.stdout.write(self.fields[0] + self.ORS)
                        else:
                            self._exec_stmts(rule.action)
                elif rule.kind == "range":
                    active = self.range_active.get(idx, False)
                    fired = False
                    if not active:
                        if to_bool(self._eval(rule.pattern)):
                            self.range_active[idx] = True
                            active = True
                            fired = True
                    if active:
                        if rule.action is None:
                            sys.stdout.write(self.fields[0] + self.ORS)
                        else:
                            self._exec_stmts(rule.action)
                        if to_bool(self._eval(rule.pattern2)):
                            self.range_active[idx] = False
        except _NextRecord:
            pass

    # ---- statement evaluation --------------------------------------

    def _exec_stmts(self, stmts: list[Node]) -> None:
        for s in stmts:
            self._exec(s)

    def _exec(self, s: Node) -> None:
        if isinstance(s, Print):
            self._exec_print(s)
            return
        if isinstance(s, Printf):
            self._exec_printf(s)
            return
        if isinstance(s, ExprStmt):
            self._eval(s.expr)
            return
        if isinstance(s, Block):
            self._exec_stmts(s.stmts)
            return
        if isinstance(s, If):
            if to_bool(self._eval(s.cond)):
                self._exec(s.then)
            elif s.els is not None:
                self._exec(s.els)
            return
        if isinstance(s, While):
            while to_bool(self._eval(s.cond)):
                try:
                    self._exec(s.body)
                except _BreakLoop:
                    return
                except _ContinueLoop:
                    continue
            return
        if isinstance(s, DoWhile):
            while True:
                try:
                    self._exec(s.body)
                except _BreakLoop:
                    return
                except _ContinueLoop:
                    pass
                if not to_bool(self._eval(s.cond)):
                    return
        if isinstance(s, For):
            if s.init is not None:
                self._eval(s.init)
            while True:
                if s.cond is not None and not to_bool(self._eval(s.cond)):
                    return
                try:
                    self._exec(s.body)
                except _BreakLoop:
                    return
                except _ContinueLoop:
                    pass
                if s.step is not None:
                    self._eval(s.step)
        if isinstance(s, ForIn):
            arr = self.arrays.setdefault(s.arr, {})
            for k in list(arr.keys()):
                self.globals[s.var] = k
                try:
                    self._exec(s.body)
                except _BreakLoop:
                    return
                except _ContinueLoop:
                    continue
            return
        if isinstance(s, Next):
            raise _NextRecord()
        if isinstance(s, Exit):
            code = 0
            if s.expr is not None:
                code = int(to_num(self._eval(s.expr)))
            raise _ExitProgram(code)
        if isinstance(s, Break):
            raise _BreakLoop()
        if isinstance(s, Continue):
            raise _ContinueLoop()
        if isinstance(s, Delete):
            t = s.target
            if isinstance(t, Name):
                self.arrays[t.name] = {}
                return
            if isinstance(t, Index):
                arr = self.arrays.setdefault(t.arr, {})
                key = self._eval_key(t.key)
                arr.pop(key, None)
                return
            raise _AwkError("invalid delete target")
        # expression as statement (shouldn't reach; ExprStmt handles)
        raise _AwkError(f"unknown statement node {type(s).__name__}")

    def _exec_print(self, s: Print) -> None:
        if not s.args:
            sys.stdout.write(self.fields[0] + self.ORS)
            return
        parts = [to_str(self._eval(a), self.OFMT) for a in s.args]
        sys.stdout.write(self.OFS.join(parts) + self.ORS)

    def _exec_printf(self, s: Printf) -> None:
        if not s.args:
            raise _AwkError("printf: missing format string")
        fmt = to_str(self._eval(s.args[0]))
        args = [self._eval(a) for a in s.args[1:]]
        sys.stdout.write(_awk_printf(fmt, args, self.OFMT))

    # ---- expression evaluation --------------------------------------

    def _eval(self, e: Node):
        if isinstance(e, Num):
            return e.v
        if isinstance(e, Str):
            return e.v
        if isinstance(e, Regex):
            # A bare regex evaluates as a match against $0
            return 1 if re.search(e.pattern, self.fields[0]) else 0
        if isinstance(e, Name):
            if e.name in self.arrays:
                raise _AwkError(f"array {e.name!r} used in scalar context")
            return self._builtin_var(e.name)
        if isinstance(e, Group):
            return self._eval(e.expr)
        if isinstance(e, Field):
            n = int(to_num(self._eval(e.expr)))
            return self.get_field(n)
        if isinstance(e, Index):
            arr = self.arrays.setdefault(e.arr, {})
            key = self._eval_key(e.key)
            # Auto-vivify: awk creates "" on first access
            if key not in arr:
                arr[key] = ""
            return arr[key]
        if isinstance(e, Binary):
            return self._eval_binary(e)
        if isinstance(e, Unary):
            v = self._eval(e.a)
            if e.op == "!":
                return 0 if to_bool(v) else 1
            if e.op == "-":
                return -to_num(v)
            if e.op == "+":
                return to_num(v)
            raise _AwkError(f"bad unary op {e.op}")
        if isinstance(e, Inc):
            # target must be lvalue
            cur = to_num(self._eval(e.target))
            new = cur + 1 if e.op == "++" else cur - 1
            self._assign_lvalue(e.target, _num_value(new))
            return _num_value(cur if e.post else new)
        if isinstance(e, Concat):
            return to_str(self._eval(e.a), self.OFMT) + to_str(self._eval(e.b), self.OFMT)
        if isinstance(e, Match):
            s = to_str(self._eval(e.expr), self.OFMT)
            pat = self._regex_pattern(e.regex)
            hit = re.search(pat, s) is not None
            if e.negate:
                hit = not hit
            return 1 if hit else 0
        if isinstance(e, InArr):
            # key in arr
            arr = self.arrays.setdefault(e.arr, {})
            key = self._eval_key(e.key)
            return 1 if key in arr else 0
        if isinstance(e, Cond):
            if to_bool(self._eval(e.c)):
                return self._eval(e.t)
            return self._eval(e.f)
        if isinstance(e, Assign):
            v = self._eval(e.value)
            if e.op == "=":
                self._assign_lvalue(e.target, v)
                return v
            cur = self._eval(e.target)
            if e.op == "+=":
                nv = to_num(cur) + to_num(v)
            elif e.op == "-=":
                nv = to_num(cur) - to_num(v)
            elif e.op == "*=":
                nv = to_num(cur) * to_num(v)
            elif e.op == "/=":
                nv = to_num(cur) / to_num(v)
            elif e.op == "%=":
                nv = math.fmod(to_num(cur), to_num(v))
            elif e.op == "^=":
                nv = to_num(cur) ** to_num(v)
            else:
                raise _AwkError(f"bad assign op {e.op}")
            out = _num_value(nv)
            self._assign_lvalue(e.target, out)
            return out
        if isinstance(e, Call):
            return self._call_builtin(e.name, e.args)
        raise _AwkError(f"unknown expression node {type(e).__name__}")

    def _regex_pattern(self, node: Node) -> str:
        if isinstance(node, Regex):
            return node.pattern
        return to_str(self._eval(node), self.OFMT)

    def _eval_key(self, node: Node) -> str:
        if isinstance(node, Binary) and node.op == "CONCAT_SUBSEP":
            a = self._eval_key(node.a)
            b = self._eval_key(node.b)
            return a + self.SUBSEP + b
        return to_str(self._eval(node), self.OFMT)

    def _eval_binary(self, e: Binary):
        op = e.op
        if op in {"&&", "||"}:
            la = to_bool(self._eval(e.a))
            if op == "&&":
                if not la:
                    return 0
                return 1 if to_bool(self._eval(e.b)) else 0
            if la:
                return 1
            return 1 if to_bool(self._eval(e.b)) else 0
        a = self._eval(e.a)
        b = self._eval(e.b)
        if op == "+": return to_num(a) + to_num(b)
        if op == "-": return to_num(a) - to_num(b)
        if op == "*": return to_num(a) * to_num(b)
        if op == "/":
            d = to_num(b)
            if d == 0:
                raise _AwkError("division by zero")
            return to_num(a) / d
        if op == "%":
            d = to_num(b)
            if d == 0:
                raise _AwkError("division by zero in %")
            return math.fmod(to_num(a), d)
        if op == "^":
            return to_num(a) ** to_num(b)
        if op in {"==", "!=", "<", "<=", ">", ">="}:
            # If either side is a "pure string" (not numeric-looking),
            # compare as strings. Otherwise compare numerically.
            if _is_numeric_value(a) and _is_numeric_value(b):
                na, nb = to_num(a), to_num(b)
                cmp_v = (na > nb) - (na < nb)
            else:
                sa = to_str(a, self.OFMT)
                sb = to_str(b, self.OFMT)
                cmp_v = (sa > sb) - (sa < sb)
            if op == "==": return 1 if cmp_v == 0 else 0
            if op == "!=": return 1 if cmp_v != 0 else 0
            if op == "<":  return 1 if cmp_v < 0 else 0
            if op == "<=": return 1 if cmp_v <= 0 else 0
            if op == ">":  return 1 if cmp_v > 0 else 0
            if op == ">=": return 1 if cmp_v >= 0 else 0
        if op == "CONCAT_SUBSEP":
            return to_str(a, self.OFMT) + self.SUBSEP + to_str(b, self.OFMT)
        raise _AwkError(f"bad binary op {op}")

    def _assign_lvalue(self, node: Node, value) -> None:
        if isinstance(node, Name):
            if node.name in self.arrays:
                raise _AwkError(f"cannot assign scalar to array {node.name!r}")
            self._set_builtin_var(node.name, value)
            return
        if isinstance(node, Field):
            n = int(to_num(self._eval(node.expr)))
            self.set_field(n, value)
            return
        if isinstance(node, Index):
            arr = self.arrays.setdefault(node.arr, {})
            key = self._eval_key(node.key)
            arr[key] = value
            return
        raise _AwkError("invalid lvalue")

    # ---- variable accessors ----------------------------------------

    _BUILTINS = {"NR", "NF", "FNR", "FILENAME", "FS", "OFS", "ORS", "RS",
                 "SUBSEP", "OFMT", "CONVFMT"}

    def _builtin_var(self, name: str):
        if name == "NR": return self.NR
        if name == "NF": return self.NF
        if name == "FNR": return self.FNR
        if name == "FILENAME": return self.FILENAME
        if name == "FS": return self.FS
        if name == "OFS": return self.OFS
        if name == "ORS": return self.ORS
        if name == "RS": return self.RS
        if name == "SUBSEP": return self.SUBSEP
        if name == "OFMT": return self.OFMT
        if name == "CONVFMT": return self.CONVFMT
        return self.globals.get(name, "")

    def _set_builtin_var(self, name: str, value) -> None:
        if name == "NR": self.NR = int(to_num(value)); return
        if name == "NF":
            n = int(to_num(value))
            if n < 0: raise _AwkError("NF must be non-negative")
            cur = self.NF
            if n > cur:
                while len(self.fields) - 1 < n:
                    self.fields.append("")
            elif n < cur:
                self.fields = self.fields[:n + 1]
            self.NF = n
            self.rebuild_line()
            return
        if name == "FNR": self.FNR = int(to_num(value)); return
        if name == "FILENAME": self.FILENAME = to_str(value); return
        if name == "FS": self.FS = to_str(value); return
        if name == "OFS": self.OFS = to_str(value); return
        if name == "ORS": self.ORS = to_str(value); return
        if name == "RS": self.RS = to_str(value); return
        if name == "SUBSEP": self.SUBSEP = to_str(value); return
        if name == "OFMT": self.OFMT = to_str(value); return
        if name == "CONVFMT": self.CONVFMT = to_str(value); return
        self.globals[name] = value

    # ---- built-in functions ----------------------------------------

    def _call_builtin(self, name: str, arg_nodes: list[Node]):
        if name == "length":
            if not arg_nodes:
                return len(self.fields[0])
            # Check for array argument BEFORE evaluating, since
            # Name-eval on an array raises "used in scalar context".
            if isinstance(arg_nodes[0], Name) and arg_nodes[0].name in self.arrays:
                return len(self.arrays[arg_nodes[0].name])
            v = self._eval(arg_nodes[0])
            return len(to_str(v, self.OFMT))
        if name == "substr":
            if len(arg_nodes) < 2 or len(arg_nodes) > 3:
                raise _AwkError("substr takes 2 or 3 args")
            s = to_str(self._eval(arg_nodes[0]), self.OFMT)
            start = int(to_num(self._eval(arg_nodes[1])))
            # awk substr is 1-based; index before 1 is clamped
            if len(arg_nodes) == 3:
                length = int(to_num(self._eval(arg_nodes[2])))
                if length < 0:
                    return ""
                begin = max(start, 1) - 1
                end = start - 1 + length
                end = min(end, len(s))
                if begin >= end:
                    return ""
                return s[begin:end]
            begin = max(start, 1) - 1
            return s[begin:]
        if name == "index":
            if len(arg_nodes) != 2:
                raise _AwkError("index takes 2 args")
            s = to_str(self._eval(arg_nodes[0]), self.OFMT)
            t = to_str(self._eval(arg_nodes[1]), self.OFMT)
            if t == "":
                return 0
            i = s.find(t)
            return i + 1 if i >= 0 else 0
        if name == "split":
            if len(arg_nodes) < 2 or len(arg_nodes) > 3:
                raise _AwkError("split takes 2 or 3 args")
            s = to_str(self._eval(arg_nodes[0]), self.OFMT)
            if not isinstance(arg_nodes[1], Name):
                raise _AwkError("split: second arg must be array name")
            arr_name = arg_nodes[1].name
            self.arrays[arr_name] = {}
            if len(arg_nodes) == 3:
                sep = self._regex_pattern(arg_nodes[2])
            else:
                sep = self.FS
            if not s:
                return 0
            if sep == " ":
                parts = s.split()
            elif len(sep) == 1:
                parts = s.split(sep)
            elif sep == "":
                parts = list(s)
            else:
                try:
                    parts = re.split(sep, s)
                except re.error:
                    parts = s.split(sep)
            arr = self.arrays[arr_name]
            for i, p in enumerate(parts, start=1):
                arr[str(i)] = p
            return len(parts)
        if name == "sub":
            return self._sub_gsub(arg_nodes, all_matches=False)
        if name == "gsub":
            return self._sub_gsub(arg_nodes, all_matches=True)
        if name == "match":
            if len(arg_nodes) != 2:
                raise _AwkError("match takes 2 args")
            s = to_str(self._eval(arg_nodes[0]), self.OFMT)
            pat = self._regex_pattern(arg_nodes[1])
            m = re.search(pat, s)
            if m:
                self.globals["RSTART"] = m.start() + 1
                self.globals["RLENGTH"] = m.end() - m.start()
                return m.start() + 1
            self.globals["RSTART"] = 0
            self.globals["RLENGTH"] = -1
            return 0
        if name == "toupper":
            return to_str(self._eval(arg_nodes[0]), self.OFMT).upper()
        if name == "tolower":
            return to_str(self._eval(arg_nodes[0]), self.OFMT).lower()
        if name == "sprintf":
            if not arg_nodes:
                raise _AwkError("sprintf: missing format")
            fmt = to_str(self._eval(arg_nodes[0]), self.OFMT)
            args = [self._eval(a) for a in arg_nodes[1:]]
            return _awk_printf(fmt, args, self.OFMT)
        if name == "int":
            return int(to_num(self._eval(arg_nodes[0])))
        if name == "sqrt":
            return math.sqrt(to_num(self._eval(arg_nodes[0])))
        if name == "log":
            return math.log(to_num(self._eval(arg_nodes[0])))
        if name == "exp":
            return math.exp(to_num(self._eval(arg_nodes[0])))
        if name == "sin":
            return math.sin(to_num(self._eval(arg_nodes[0])))
        if name == "cos":
            return math.cos(to_num(self._eval(arg_nodes[0])))
        if name == "atan2":
            return math.atan2(to_num(self._eval(arg_nodes[0])),
                              to_num(self._eval(arg_nodes[1])))
        if name == "rand":
            return random.random()
        if name == "srand":
            if arg_nodes:
                random.seed(int(to_num(self._eval(arg_nodes[0]))))
            else:
                random.seed()
            return 0
        if name == "system":
            cmd = to_str(self._eval(arg_nodes[0]), self.OFMT)
            return os.system(cmd)
        raise _AwkError(f"unknown function {name!r}")

    def _sub_gsub(self, arg_nodes: list[Node], *, all_matches: bool) -> int:
        if len(arg_nodes) < 2 or len(arg_nodes) > 3:
            raise _AwkError(f"{'gsub' if all_matches else 'sub'} takes 2 or 3 args")
        pat = self._regex_pattern(arg_nodes[0])
        repl = to_str(self._eval(arg_nodes[1]), self.OFMT)
        # awk & in replacement = whole match; \& = literal &
        def _py_repl(m: re.Match) -> str:
            out: list[str] = []
            i = 0
            while i < len(repl):
                c = repl[i]
                if c == "\\" and i + 1 < len(repl):
                    n = repl[i + 1]
                    if n == "&":
                        out.append("&")
                        i += 2
                        continue
                    if n == "\\":
                        out.append("\\")
                        i += 2
                        continue
                    out.append(n)
                    i += 2
                    continue
                if c == "&":
                    out.append(m.group(0))
                    i += 1
                    continue
                out.append(c)
                i += 1
            return "".join(out)

        if len(arg_nodes) == 3:
            target_node = arg_nodes[2]
        else:
            target_node = Field(Num(0))
        src = to_str(self._eval(target_node), self.OFMT)
        try:
            compiled = re.compile(pat)
        except re.error as ex:
            raise _AwkError(f"bad regex {pat!r}: {ex}")
        count = 0
        if all_matches:
            def _count_and_sub(m: re.Match) -> str:
                nonlocal count
                count += 1
                return _py_repl(m)
            new = compiled.sub(_count_and_sub, src)
        else:
            def _count_and_sub_once(m: re.Match) -> str:
                nonlocal count
                if count == 0:
                    count = 1
                    return _py_repl(m)
                return m.group(0)
            new = compiled.sub(_count_and_sub_once, src, count=1)
        if count:
            self._assign_lvalue(target_node, new)
        return count


def _is_numeric_value(v) -> bool:
    if isinstance(v, (int, float)):
        return True
    if not isinstance(v, str):
        return False
    if v == "":
        return False
    return bool(re.fullmatch(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*", v))


def _num_value(x: float):
    if x == int(x) and abs(x) < 1e16:
        return int(x)
    return x


# ────────────────────────────────────────────────────────────────────
# printf
# ────────────────────────────────────────────────────────────────────

_PRINTF_SPEC = re.compile(r"%([-+ #0]*)(\d+|\*)?(?:\.(\d+|\*))?([diouxXfeEgGsc%])")


def _awk_printf(fmt: str, args: list, ofmt: str) -> str:
    out: list[str] = []
    i = 0
    ai = 0
    while i < len(fmt):
        c = fmt[i]
        if c != "%":
            if c == "\\" and i + 1 < len(fmt):
                n = fmt[i + 1]
                escape = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                          "/": "/", '"': '"', "a": "\a", "b": "\b",
                          "f": "\f", "v": "\v"}.get(n)
                if escape is not None:
                    out.append(escape)
                    i += 2
                    continue
                out.append(n)
                i += 2
                continue
            out.append(c)
            i += 1
            continue
        m = _PRINTF_SPEC.match(fmt, i)
        if not m:
            if i + 1 < len(fmt) and fmt[i + 1] == "%":
                out.append("%")
                i += 2
                continue
            raise _AwkError(f"bad printf format at position {i}")
        flags, width, prec, conv = m.groups()
        if conv == "%":
            out.append("%")
            i = m.end()
            continue
        w = ""
        if width == "*":
            w = str(int(to_num(args[ai])))
            ai += 1
        elif width is not None:
            w = width
        p = ""
        if prec == "*":
            p = f".{int(to_num(args[ai]))}"
            ai += 1
        elif prec is not None:
            p = f".{prec}"
        if ai >= len(args):
            val = ""
        else:
            val = args[ai]
            ai += 1
        py_flags = flags or ""
        spec = f"%{py_flags}{w}{p}{conv}"
        try:
            if conv in {"d", "i"}:
                out.append(spec.replace("i", "d") % int(to_num(val)))
            elif conv == "o":
                out.append(spec % int(to_num(val)))
            elif conv in {"x", "X"}:
                out.append(spec % int(to_num(val)))
            elif conv == "u":
                out.append(spec.replace("u", "d") % int(to_num(val)))
            elif conv in {"f", "e", "E", "g", "G"}:
                out.append(spec % to_num(val))
            elif conv == "s":
                out.append(spec % to_str(val, ofmt))
            elif conv == "c":
                if isinstance(val, (int, float)):
                    out.append(chr(int(val)))
                else:
                    s = to_str(val, ofmt)
                    out.append(s[:1])
            else:
                raise _AwkError(f"unsupported printf conversion {conv}")
        except (TypeError, ValueError) as e:
            raise _AwkError(f"printf error: {e}")
        i = m.end()
    return "".join(out)


# ────────────────────────────────────────────────────────────────────
# CLI entry point
# ────────────────────────────────────────────────────────────────────

_HELP_TEXT = (
    "awk - pattern-scanning and processing language\n"
    "\n"
    "Usage: awk [-F sep] [-v var=val]... [-f file | 'program'] [file...]\n"
)


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    fs: str | None = None
    preset: dict[str, object] = {}
    program_parts: list[str] = []
    files: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--help":
            sys.stdout.write(_HELP_TEXT)
            return 0
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "-F":
            i += 1
            if i >= len(args):
                err("awk", "-F requires an argument")
                return 2
            fs = args[i]
            i += 1
            continue
        if a.startswith("-F") and len(a) > 2:
            fs = a[2:]
            i += 1
            continue
        if a == "-v":
            i += 1
            if i >= len(args):
                err("awk", "-v requires var=val")
                return 2
            if "=" not in args[i]:
                err("awk", "-v: expected var=val")
                return 2
            k, v = args[i].split("=", 1)
            preset[k] = v
            i += 1
            continue
        if a.startswith("-v") and len(a) > 2 and "=" in a[2:]:
            k, v = a[2:].split("=", 1)
            preset[k] = v
            i += 1
            continue
        if a == "-f":
            i += 1
            if i >= len(args):
                err("awk", "-f requires a file")
                return 2
            try:
                program_parts.append(Path(args[i]).read_text(encoding="utf-8"))
            except OSError as e:
                err("awk", f"{args[i]}: {e.strerror or e}")
                return 2
            i += 1
            continue
        if a == "-":
            # stdin as input file
            files.append("-")
            i += 1
            continue
        if a.startswith("-") and a != "-":
            err("awk", f"unknown option: {a}")
            return 2
        # first non-flag: program string (unless we already have -f)
        if not program_parts:
            program_parts.append(a)
            i += 1
            continue
        files.append(a)
        i += 1

    if not program_parts:
        err("awk", "missing program")
        return 2

    source = "\n".join(program_parts)
    try:
        tokens = Lexer(source).tokens
        program = Parser(tokens).parse_program()
    except _AwkError as e:
        err("awk", f"parse: {e}")
        return 2

    # "-" inside files means stdin
    real_files: list[str] = []
    for f in files:
        if f == "-":
            real_files.append("-")
        else:
            real_files.append(f)

    interp = Interp(program, fs=fs, vars_preset=preset, files=real_files)
    try:
        return interp.run()
    except _AwkError as e:
        err("awk", str(e))
        return 2
