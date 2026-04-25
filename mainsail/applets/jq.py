"""mainsail jq — a practical subset of jq.

Parses a filter expression and runs it over JSON input(s), emitting
zero or more JSON outputs per input. Implemented as a small lexer +
recursive-descent parser + generator-based evaluator.

Supported:
  - Identity (.), field access (.foo, .foo.bar, ."key with spaces")
  - Optional access (.foo?)
  - Array index/slice (.[0], .[-1], .[2:5])
  - Array/object iteration (.[]) and optional iteration (.[]?)
  - Pipes (|) and comma (,) to emit multiple results
  - Parentheses for grouping
  - Comparison and arithmetic operators
  - Boolean operators: and, or, not
  - Literals: numbers, strings, true, false, null
  - Object construction { a: .x, b: .y[] }
  - Array construction [ .[] | .name ]
  - Functions: length, keys, keys_unsorted, values, type, has,
    contains, in, empty, not, select, map, sort, sort_by, unique,
    unique_by, reverse, first, last, min, max, add, to_entries,
    from_entries, with_entries, paths, leaf_paths, tostring,
    tonumber, ascii, explode, implode, split, join, ltrimstr,
    rtrimstr, startswith, endswith, ascii_downcase, ascii_upcase,
    floor, ceil, sqrt
  - Try/catch via `?` (no `try f catch g` syntax)

Not supported (yet):
  - User-defined functions (def)
  - Variable bindings (as $x)
  - Update operators (|=, +=, etc.)
  - Recursive descent (..)
  - Format strings (@csv, @json, etc.)
"""
from __future__ import annotations

import json as _json
import math
import sys
from typing import Iterable, Iterator

from mainsail.common import err

NAME = "jq"
ALIASES: list[str] = []
HELP = "command-line JSON processor"


# ────────────────────────────────────────────────────────────────────
# Errors
# ────────────────────────────────────────────────────────────────────

class JQError(Exception):
    pass


# ────────────────────────────────────────────────────────────────────
# Lexer
# ────────────────────────────────────────────────────────────────────

_KEYWORDS = {"true", "false", "null", "and", "or", "not", "if", "then",
             "else", "elif", "end", "as"}

_MULTI = {"==", "!=", "<=", ">=", "//"}


def _tokenize(src: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c.isdigit() or (c == "-" and i + 1 < n and src[i + 1].isdigit()
                           and (not tokens or tokens[-1][0] not in
                                {"NUMBER", "STRING", "NAME", ")", "]", "}", "."})):
            j = i
            if src[j] == "-":
                j += 1
            while j < n and src[j].isdigit():
                j += 1
            if j < n and src[j] == ".":
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
            if j < n and src[j] in "eE":
                j += 1
                if j < n and src[j] in "+-":
                    j += 1
                while j < n and src[j].isdigit():
                    j += 1
            tokens.append(("NUMBER", float(src[i:j]) if any(c in src[i:j] for c in ".eE") else int(src[i:j])))
            i = j
            continue
        if c == '"':
            j = i + 1
            out: list[str] = []
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    nxt = src[j + 1]
                    if nxt == "n": out.append("\n")
                    elif nxt == "t": out.append("\t")
                    elif nxt == "r": out.append("\r")
                    elif nxt == "\\": out.append("\\")
                    elif nxt == '"': out.append('"')
                    elif nxt == "/": out.append("/")
                    elif nxt == "b": out.append("\b")
                    elif nxt == "f": out.append("\f")
                    elif nxt == "u" and j + 5 < n:
                        try:
                            out.append(chr(int(src[j + 2:j + 6], 16)))
                            j += 4
                        except ValueError:
                            out.append(nxt)
                    else:
                        out.append(nxt)
                    j += 2
                    continue
                out.append(src[j])
                j += 1
            if j >= n:
                raise JQError("unterminated string")
            tokens.append(("STRING", "".join(out)))
            i = j + 1
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            if word in _KEYWORDS:
                tokens.append((word, word))
            else:
                tokens.append(("NAME", word))
            i = j
            continue
        if c == "$":
            raise JQError("variables ($x) not supported")
        # Multi-char operators
        two = src[i:i + 2]
        if two in _MULTI:
            tokens.append((two, two))
            i += 2
            continue
        if c in "+-*/%=<>!,|:;?()[]{}.":
            tokens.append((c, c))
            i += 1
            continue
        raise JQError(f"unexpected character {c!r} at position {i}")
    tokens.append(("EOF", None))
    return tokens


# ────────────────────────────────────────────────────────────────────
# AST nodes (tuples for compactness)
# ────────────────────────────────────────────────────────────────────

# We represent AST as ("Kind", *children). Each filter is a function:
#   eval(node, value) -> Iterator[value]


class Parser:
    def __init__(self, tokens: list[tuple[str, object]]) -> None:
        self.t = tokens
        self.i = 0

    def peek(self, off: int = 0) -> str:
        return self.t[self.i + off][0]

    def peek_val(self):
        return self.t[self.i][1]

    def eat(self, kind: str):
        if self.peek() != kind:
            raise JQError(f"expected {kind!r}, got {self.peek()!r}")
        tok = self.t[self.i]
        self.i += 1
        return tok

    def accept(self, *kinds: str) -> bool:
        if self.peek() in kinds:
            self.i += 1
            return True
        return False

    def parse(self):
        node = self.parse_pipe()
        if self.peek() != "EOF":
            raise JQError(f"unexpected token {self.peek()!r}")
        return node

    def parse_pipe(self):
        left = self.parse_comma()
        while self.peek() == "|":
            self.i += 1
            right = self.parse_comma()
            left = ("Pipe", left, right)
        return left

    def parse_comma(self):
        first = self.parse_or()
        if self.peek() == ",":
            items = [first]
            while self.peek() == ",":
                self.i += 1
                items.append(self.parse_or())
            return ("Comma", items)
        return first

    def parse_or(self):
        left = self.parse_and()
        while self.peek() == "or":
            self.i += 1
            right = self.parse_and()
            left = ("Binop", "or", left, right)
        return left

    def parse_and(self):
        left = self.parse_compare()
        while self.peek() == "and":
            self.i += 1
            right = self.parse_compare()
            left = ("Binop", "and", left, right)
        return left

    def parse_compare(self):
        left = self.parse_alt()
        if self.peek() in {"==", "!=", "<", "<=", ">", ">="}:
            op = self.t[self.i][0]
            self.i += 1
            right = self.parse_alt()
            return ("Binop", op, left, right)
        return left

    def parse_alt(self):
        left = self.parse_add()
        while self.peek() == "//":
            self.i += 1
            right = self.parse_add()
            left = ("Alt", left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.peek() in {"+", "-"}:
            op = self.t[self.i][0]
            self.i += 1
            right = self.parse_mul()
            left = ("Binop", op, left, right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.peek() in {"*", "/", "%"}:
            op = self.t[self.i][0]
            self.i += 1
            right = self.parse_unary()
            left = ("Binop", op, left, right)
        return left

    def parse_unary(self):
        if self.peek() == "-":
            self.i += 1
            return ("Neg", self.parse_unary())
        if self.peek() == "not":
            self.i += 1
            return ("Not", self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.peek() == "?":
                self.i += 1
                node = ("Try", node)
                continue
            if self.peek() == "." and self.peek(1) == "NAME":
                # chained field access: foo().bar
                self.i += 1
                name = self.t[self.i][1]
                self.i += 1
                node = ("Pipe", node, ("Field", name, False))
                continue
            if self.peek() == "[":
                self.i += 1
                if self.peek() == "]":
                    self.i += 1
                    node = ("Pipe", node, ("Iter", False))
                    continue
                # index or slice
                start_expr = None
                end_expr = None
                if self.peek() != ":":
                    start_expr = self.parse_pipe()
                if self.peek() == ":":
                    self.i += 1
                    if self.peek() != "]":
                        end_expr = self.parse_pipe()
                    self.eat("]")
                    node = ("Pipe", node, ("Slice", start_expr, end_expr))
                    continue
                self.eat("]")
                node = ("Pipe", node, ("Index", start_expr))
                continue
            break
        return node

    def parse_primary(self):
        t = self.peek()
        if t == "NUMBER":
            v = self.t[self.i][1]
            self.i += 1
            return ("Lit", v)
        if t == "STRING":
            v = self.t[self.i][1]
            self.i += 1
            return ("Lit", v)
        if t in {"true", "false", "null"}:
            self.i += 1
            return ("Lit", {"true": True, "false": False, "null": None}[t])
        if t == ".":
            return self.parse_path()
        if t == "(":
            self.i += 1
            node = self.parse_pipe()
            self.eat(")")
            return node
        if t == "[":
            self.i += 1
            if self.peek() == "]":
                self.i += 1
                return ("Lit", [])
            inner = self.parse_pipe()
            self.eat("]")
            return ("ArrayCtor", inner)
        if t == "{":
            return self.parse_object()
        if t == "if":
            return self.parse_if()
        if t == "NAME":
            name = self.t[self.i][1]
            self.i += 1
            args: list = []
            if self.peek() == "(":
                self.i += 1
                args.append(self.parse_pipe())
                while self.peek() == ";":
                    self.i += 1
                    args.append(self.parse_pipe())
                self.eat(")")
            return ("Call", name, args)
        raise JQError(f"unexpected token {t!r}")

    def parse_path(self):
        # Already at "."
        self.eat(".")
        if self.peek() == "NAME":
            name = self.t[self.i][1]
            self.i += 1
            optional = False
            if self.peek() == "?":
                self.i += 1
                optional = True
            return ("Field", name, optional)
        if self.peek() == "STRING":
            name = self.t[self.i][1]
            self.i += 1
            return ("Field", name, False)
        if self.peek() == "[":
            # .[ ... ] handled by postfix; rewind so it picks up Identity then [
            return ("Identity",)
        return ("Identity",)

    def parse_object(self):
        self.eat("{")
        pairs = []
        if self.peek() != "}":
            while True:
                key, value = self._parse_obj_entry()
                pairs.append((key, value))
                if self.peek() == ",":
                    self.i += 1
                    continue
                break
        self.eat("}")
        return ("ObjectCtor", pairs)

    def _parse_obj_entry(self):
        if self.peek() == "NAME":
            key = ("Lit", self.t[self.i][1])
            self.i += 1
        elif self.peek() == "STRING":
            key = ("Lit", self.t[self.i][1])
            self.i += 1
        elif self.peek() == "(":
            self.i += 1
            key = self.parse_pipe()
            self.eat(")")
        else:
            raise JQError(f"unexpected key token {self.peek()!r}")
        if self.peek() == ":":
            self.i += 1
            value = self.parse_or()
        else:
            # Shorthand { foo } means { foo: .foo }
            if key[0] == "Lit" and isinstance(key[1], str):
                value = ("Field", key[1], False)
            else:
                raise JQError("missing ':' in object literal")
        return key, value

    def parse_if(self):
        self.eat("if")
        cond = self.parse_pipe()
        self.eat("then")
        then_branch = self.parse_pipe()
        elifs = []
        while self.peek() == "elif":
            self.i += 1
            c = self.parse_pipe()
            self.eat("then")
            b = self.parse_pipe()
            elifs.append((c, b))
        else_branch = ("Identity",)
        if self.peek() == "else":
            self.i += 1
            else_branch = self.parse_pipe()
        self.eat("end")
        # Build nested if/elif/else as a chain
        result = else_branch
        for c, b in reversed(elifs):
            result = ("If", c, b, result)
        return ("If", cond, then_branch, result)


# ────────────────────────────────────────────────────────────────────
# Evaluator
# ────────────────────────────────────────────────────────────────────

def _truthy(v) -> bool:
    return v is not None and v is not False


def _typestr(v) -> str:
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, (int, float)): return "number"
    if isinstance(v, str): return "string"
    if isinstance(v, list): return "array"
    if isinstance(v, dict): return "object"
    return "unknown"


def evaluate(node, value) -> Iterator:
    kind = node[0]

    if kind == "Lit":
        yield node[1]
        return
    if kind == "Identity":
        yield value
        return
    if kind == "Field":
        _, name, optional = node
        if isinstance(value, dict):
            yield value.get(name)
        elif value is None:
            yield None
        else:
            if optional:
                return
            raise JQError(f"Cannot index {_typestr(value)} with \"{name}\"")
        return
    if kind == "Iter":
        _, optional = node
        if isinstance(value, list):
            for item in value:
                yield item
            return
        if isinstance(value, dict):
            for v in value.values():
                yield v
            return
        if optional or value is None:
            return
        raise JQError(f"Cannot iterate over {_typestr(value)}")
    if kind == "Index":
        _, key_expr = node
        for k in evaluate(key_expr, value):
            if isinstance(value, list):
                if not isinstance(k, int):
                    raise JQError(f"array index must be number, got {_typestr(k)}")
                if -len(value) <= k < len(value):
                    yield value[k]
                else:
                    yield None
            elif isinstance(value, dict):
                if not isinstance(k, str):
                    raise JQError(f"object key must be string, got {_typestr(k)}")
                yield value.get(k)
            elif value is None:
                yield None
            else:
                raise JQError(f"Cannot index {_typestr(value)}")
        return
    if kind == "Slice":
        _, start_expr, end_expr = node
        if value is None:
            yield None
            return
        if not isinstance(value, (list, str)):
            raise JQError(f"Cannot slice {_typestr(value)}")
        starts = list(evaluate(start_expr, value)) if start_expr else [None]
        ends = list(evaluate(end_expr, value)) if end_expr else [None]
        for s in starts:
            for e in ends:
                yield value[(s or 0):(e if e is not None else len(value))]
        return
    if kind == "Pipe":
        _, left, right = node
        for v in evaluate(left, value):
            for r in evaluate(right, v):
                yield r
        return
    if kind == "Comma":
        _, items = node
        for it in items:
            for v in evaluate(it, value):
                yield v
        return
    if kind == "Try":
        _, inner = node
        try:
            for v in evaluate(inner, value):
                yield v
        except JQError:
            return
        return
    if kind == "Neg":
        _, inner = node
        for v in evaluate(inner, value):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise JQError(f"cannot negate {_typestr(v)}")
            yield -v
        return
    if kind == "Not":
        _, inner = node
        for v in evaluate(inner, value):
            yield not _truthy(v)
        return
    if kind == "Binop":
        _, op, left, right = node
        for la in evaluate(left, value):
            for ra in evaluate(right, value):
                yield _binop(op, la, ra)
        return
    if kind == "Alt":
        _, left, right = node
        produced = False
        for v in evaluate(left, value):
            if v is not None and v is not False:
                produced = True
                yield v
        if not produced:
            for v in evaluate(right, value):
                yield v
        return
    if kind == "If":
        _, cond, then_b, else_b = node
        for c in evaluate(cond, value):
            if _truthy(c):
                for v in evaluate(then_b, value):
                    yield v
            else:
                for v in evaluate(else_b, value):
                    yield v
        return
    if kind == "ArrayCtor":
        _, inner = node
        yield list(evaluate(inner, value))
        return
    if kind == "ObjectCtor":
        _, pairs = node
        # Cross-product of multi-output keys/values
        results: list[dict] = [{}]
        for key_expr, val_expr in pairs:
            new_results: list[dict] = []
            for partial in results:
                for k in evaluate(key_expr, value):
                    for v in evaluate(val_expr, value):
                        copy = dict(partial)
                        copy[k] = v
                        new_results.append(copy)
            results = new_results
        for r in results:
            yield r
        return
    if kind == "Call":
        _, name, args = node
        yield from _call(name, args, value)
        return
    raise JQError(f"unknown AST node: {kind}")


def _binop(op: str, a, b):
    if op == "==": return a == b
    if op == "!=": return a != b
    if op == "and": return _truthy(a) and _truthy(b)
    if op == "or": return _truthy(a) or _truthy(b)
    if op in {"<", "<=", ">", ">="}:
        try:
            r = _compare(a, b)
        except TypeError:
            raise JQError(f"cannot compare {_typestr(a)} and {_typestr(b)}")
        if op == "<": return r < 0
        if op == "<=": return r <= 0
        if op == ">": return r > 0
        if op == ">=": return r >= 0
    if op == "+":
        if a is None: return b
        if b is None: return a
        if isinstance(a, list) and isinstance(b, list): return a + b
        if isinstance(a, str) and isinstance(b, str): return a + b
        if isinstance(a, dict) and isinstance(b, dict):
            return {**a, **b}
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a + b
        raise JQError(f"{_typestr(a)} and {_typestr(b)} cannot be added")
    if op == "-":
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a - b
        if isinstance(a, list) and isinstance(b, list):
            return [x for x in a if x not in b]
        raise JQError(f"{_typestr(a)} and {_typestr(b)} cannot be subtracted")
    if op == "*":
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a * b
        if isinstance(a, str) and isinstance(b, (int, float)):
            return a * int(b)
        raise JQError(f"{_typestr(a)} and {_typestr(b)} cannot be multiplied")
    if op == "/":
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if b == 0:
                raise JQError("division by zero")
            return a / b
        if isinstance(a, str) and isinstance(b, str):
            return a.split(b)
        raise JQError(f"{_typestr(a)} and {_typestr(b)} cannot be divided")
    if op == "%":
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return int(a) % int(b)
        raise JQError(f"{_typestr(a)} and {_typestr(b)} cannot be modulo'd")
    raise JQError(f"unknown operator: {op}")


_TYPE_RANK = {"null": 0, "boolean": 1, "number": 2, "string": 3, "array": 4, "object": 5}


def _compare(a, b) -> int:
    ta = _typestr(a)
    tb = _typestr(b)
    if ta != tb:
        return (_TYPE_RANK[ta] > _TYPE_RANK[tb]) - (_TYPE_RANK[ta] < _TYPE_RANK[tb])
    if ta == "null":
        return 0
    if ta in ("number", "boolean", "string"):
        return (a > b) - (a < b)
    if ta == "array":
        for ai, bi in zip(a, b):
            r = _compare(ai, bi)
            if r != 0:
                return r
        return (len(a) > len(b)) - (len(a) < len(b))
    if ta == "object":
        ak = sorted(a.keys())
        bk = sorted(b.keys())
        if ak != bk:
            return (ak > bk) - (ak < bk)
        for k in ak:
            r = _compare(a[k], b[k])
            if r != 0:
                return r
        return 0
    return 0


# ────────────────────────────────────────────────────────────────────
# Built-in functions
# ────────────────────────────────────────────────────────────────────

def _call(name: str, args: list, value):
    if name == "length":
        if value is None: yield 0; return
        if isinstance(value, (list, str, dict)): yield len(value); return
        if isinstance(value, (int, float)): yield abs(value); return
        raise JQError(f"length: cannot get length of {_typestr(value)}")
    if name == "keys":
        if isinstance(value, dict): yield sorted(value.keys()); return
        if isinstance(value, list): yield list(range(len(value))); return
        raise JQError(f"keys: requires object or array, got {_typestr(value)}")
    if name == "keys_unsorted":
        if isinstance(value, dict): yield list(value.keys()); return
        if isinstance(value, list): yield list(range(len(value))); return
        raise JQError(f"keys_unsorted: requires object or array")
    if name == "values":
        if isinstance(value, dict): yield list(value.values()); return
        if isinstance(value, list): yield list(value); return
        raise JQError(f"values: requires object or array")
    if name == "type":
        yield _typestr(value); return
    if name == "has":
        if not args:
            raise JQError("has: needs an argument")
        for k in evaluate(args[0], value):
            if isinstance(value, dict):
                yield k in value
            elif isinstance(value, list):
                if not isinstance(k, int):
                    raise JQError("has: array key must be number")
                yield 0 <= k < len(value)
            else:
                raise JQError(f"has: requires object or array")
        return
    if name == "in":
        if not args: raise JQError("in: needs argument")
        for cont in evaluate(args[0], value):
            if isinstance(cont, dict):
                yield value in cont
            elif isinstance(cont, list):
                yield isinstance(value, int) and 0 <= value < len(cont)
            else:
                raise JQError("in: argument must be object or array")
        return
    if name == "contains":
        if not args: raise JQError("contains: needs argument")
        for sub in evaluate(args[0], value):
            yield _contains(value, sub)
        return
    if name == "empty":
        return
    if name == "not":
        yield not _truthy(value); return
    if name == "select":
        if not args:
            raise JQError("select: needs predicate")
        for ok in evaluate(args[0], value):
            if _truthy(ok):
                yield value
        return
    if name == "map":
        if not args:
            raise JQError("map: needs argument")
        if not isinstance(value, list):
            raise JQError(f"map: requires array")
        out = []
        for v in value:
            for r in evaluate(args[0], v):
                out.append(r)
        yield out
        return
    if name == "map_values":
        if not args:
            raise JQError("map_values: needs argument")
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                results = list(evaluate(args[0], v))
                if results:
                    out[k] = results[0]
            yield out
            return
        if isinstance(value, list):
            out_l = []
            for v in value:
                results = list(evaluate(args[0], v))
                if results:
                    out_l.append(results[0])
            yield out_l
            return
        raise JQError("map_values: requires object or array")
    if name == "sort":
        if not isinstance(value, list):
            raise JQError("sort: requires array")
        try:
            yield sorted(value, key=_sort_key)
        except TypeError:
            raise JQError("sort: incompatible elements")
        return
    if name == "sort_by":
        if not args: raise JQError("sort_by: needs argument")
        if not isinstance(value, list):
            raise JQError("sort_by: requires array")
        keyed = []
        for v in value:
            ks = list(evaluate(args[0], v))
            keyed.append((ks[0] if ks else None, v))
        keyed.sort(key=lambda p: _sort_key(p[0]))
        yield [v for _, v in keyed]
        return
    if name == "unique":
        if not isinstance(value, list):
            raise JQError("unique: requires array")
        seen = []
        for v in sorted(value, key=_sort_key):
            if not seen or seen[-1] != v:
                seen.append(v)
        yield seen
        return
    if name == "unique_by":
        if not args: raise JQError("unique_by: needs argument")
        if not isinstance(value, list):
            raise JQError("unique_by: requires array")
        keyed = []
        for v in value:
            ks = list(evaluate(args[0], v))
            keyed.append((ks[0] if ks else None, v))
        keyed.sort(key=lambda p: _sort_key(p[0]))
        out = []
        prev = object()
        for k, v in keyed:
            if k != prev:
                out.append(v)
                prev = k
        yield out
        return
    if name == "reverse":
        if isinstance(value, list): yield list(reversed(value)); return
        if isinstance(value, str): yield value[::-1]; return
        raise JQError("reverse: requires array or string")
    if name == "first":
        if isinstance(value, list):
            yield value[0] if value else None
            return
        # first(stream) form: take first element
        if args:
            for v in evaluate(args[0], value):
                yield v
                return
            yield None
            return
        raise JQError("first: requires array")
    if name == "last":
        if isinstance(value, list):
            yield value[-1] if value else None
            return
        raise JQError("last: requires array")
    if name == "min":
        if not isinstance(value, list):
            raise JQError("min: requires array")
        yield min(value, key=_sort_key) if value else None
        return
    if name == "max":
        if not isinstance(value, list):
            raise JQError("max: requires array")
        yield max(value, key=_sort_key) if value else None
        return
    if name == "add":
        if value is None or value == []:
            yield None
            return
        if not isinstance(value, list):
            raise JQError("add: requires array")
        result = value[0]
        for v in value[1:]:
            result = _binop("+", result, v)
        yield result
        return
    if name == "to_entries":
        if not isinstance(value, dict):
            raise JQError("to_entries: requires object")
        yield [{"key": k, "value": v} for k, v in value.items()]
        return
    if name == "from_entries":
        if not isinstance(value, list):
            raise JQError("from_entries: requires array")
        out = {}
        for entry in value:
            if isinstance(entry, dict):
                k = entry.get("key", entry.get("k", entry.get("name")))
                v = entry.get("value", entry.get("v"))
                if k is None:
                    raise JQError("from_entries: missing key")
                out[str(k)] = v
            else:
                raise JQError("from_entries: array elements must be objects")
        yield out
        return
    if name == "with_entries":
        if not args: raise JQError("with_entries: needs argument")
        if not isinstance(value, dict):
            raise JQError("with_entries: requires object")
        entries = [{"key": k, "value": v} for k, v in value.items()]
        new_entries = []
        for e in entries:
            for r in evaluate(args[0], e):
                new_entries.append(r)
        out = {}
        for e in new_entries:
            if isinstance(e, dict) and "key" in e:
                out[str(e["key"])] = e.get("value")
        yield out
        return
    if name == "paths":
        yield list(_iter_paths(value))
        return
    if name == "leaf_paths":
        yield [p for p in _iter_paths(value) if _is_leaf(value, p)]
        return
    if name == "tostring":
        if isinstance(value, str): yield value; return
        yield _json.dumps(value, ensure_ascii=False)
        return
    if name == "tonumber":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            yield value; return
        if isinstance(value, str):
            try:
                v = int(value)
            except ValueError:
                try:
                    v = float(value)
                except ValueError:
                    raise JQError(f"tonumber: cannot parse {value!r}")
            yield v
            return
        raise JQError(f"tonumber: cannot convert {_typestr(value)}")
    if name == "ascii":
        if isinstance(value, (int, float)):
            yield chr(int(value)); return
        raise JQError("ascii: requires number")
    if name == "explode":
        if not isinstance(value, str):
            raise JQError("explode: requires string")
        yield [ord(c) for c in value]
        return
    if name == "implode":
        if not isinstance(value, list):
            raise JQError("implode: requires array")
        yield "".join(chr(int(c)) for c in value)
        return
    if name == "split":
        if not args: raise JQError("split: needs argument")
        if not isinstance(value, str):
            raise JQError("split: requires string")
        for sep in evaluate(args[0], value):
            if not isinstance(sep, str):
                raise JQError("split: separator must be string")
            yield value.split(sep)
        return
    if name == "join":
        if not args: raise JQError("join: needs argument")
        if not isinstance(value, list):
            raise JQError("join: requires array")
        for sep in evaluate(args[0], value):
            if not isinstance(sep, str):
                raise JQError("join: separator must be string")
            yield sep.join(_json.dumps(x) if not isinstance(x, str) and x is not None else (x or "") for x in value)
        return
    if name == "ltrimstr":
        if not args: raise JQError("ltrimstr: needs argument")
        if not isinstance(value, str):
            yield value; return
        for prefix in evaluate(args[0], value):
            if isinstance(prefix, str) and value.startswith(prefix):
                yield value[len(prefix):]
            else:
                yield value
        return
    if name == "rtrimstr":
        if not args: raise JQError("rtrimstr: needs argument")
        if not isinstance(value, str):
            yield value; return
        for suffix in evaluate(args[0], value):
            if isinstance(suffix, str) and value.endswith(suffix):
                yield value[:-len(suffix)] if suffix else value
            else:
                yield value
        return
    if name == "startswith":
        if not args: raise JQError("startswith: needs argument")
        for prefix in evaluate(args[0], value):
            yield isinstance(value, str) and value.startswith(prefix)
        return
    if name == "endswith":
        if not args: raise JQError("endswith: needs argument")
        for suffix in evaluate(args[0], value):
            yield isinstance(value, str) and value.endswith(suffix)
        return
    if name == "ascii_downcase":
        if not isinstance(value, str): raise JQError("ascii_downcase: requires string")
        yield value.lower(); return
    if name == "ascii_upcase":
        if not isinstance(value, str): raise JQError("ascii_upcase: requires string")
        yield value.upper(); return
    if name == "floor":
        if not isinstance(value, (int, float)): raise JQError("floor: requires number")
        yield math.floor(value); return
    if name == "ceil":
        if not isinstance(value, (int, float)): raise JQError("ceil: requires number")
        yield math.ceil(value); return
    if name == "sqrt":
        if not isinstance(value, (int, float)): raise JQError("sqrt: requires number")
        yield math.sqrt(value); return
    if name == "any":
        if not isinstance(value, list):
            raise JQError("any: requires array")
        yield any(_truthy(v) for v in value); return
    if name == "all":
        if not isinstance(value, list):
            raise JQError("all: requires array")
        yield all(_truthy(v) for v in value); return
    if name == "isempty":
        # isempty(f) — true iff f produces no output
        if not args: raise JQError("isempty: needs argument")
        for _ in evaluate(args[0], value):
            yield False
            return
        yield True
        return
    raise JQError(f"unknown function: {name}")


def _sort_key(v):
    """Total order: null < false < true < number < string < array < object."""
    rank = _TYPE_RANK[_typestr(v)]
    if isinstance(v, bool):
        return (rank, 0 if not v else 1)
    if isinstance(v, (int, float, str)):
        return (rank, v)
    if isinstance(v, list):
        return (rank, tuple(_sort_key(x) for x in v))
    if isinstance(v, dict):
        return (rank, tuple(sorted((k, _sort_key(val)) for k, val in v.items())))
    return (rank, 0)


def _contains(big, small) -> bool:
    if _typestr(big) != _typestr(small):
        return False
    if isinstance(big, str):
        return small in big
    if isinstance(big, list):
        return all(any(_contains(b, s) for b in big) for s in small)
    if isinstance(big, dict):
        return all(k in big and _contains(big[k], v) for k, v in small.items())
    return big == small


def _iter_paths(value, prefix=None) -> Iterator[list]:
    prefix = prefix or []
    if isinstance(value, list):
        for i, v in enumerate(value):
            yield prefix + [i]
            yield from _iter_paths(v, prefix + [i])
    elif isinstance(value, dict):
        for k, v in value.items():
            yield prefix + [k]
            yield from _iter_paths(v, prefix + [k])


def _is_leaf(root, path) -> bool:
    cur = root
    for p in path:
        cur = cur[p]
    return not isinstance(cur, (list, dict))


# ────────────────────────────────────────────────────────────────────
# Output formatting
# ────────────────────────────────────────────────────────────────────

def _format(value, *, raw: bool, compact: bool, sort_keys: bool, tab: bool) -> str:
    if raw and isinstance(value, str):
        return value
    indent: int | str | None = None
    sep = (", ", ": ") if not compact else (",", ":")
    if not compact:
        indent = "\t" if tab else 2
    return _json.dumps(value, indent=indent, separators=sep, sort_keys=sort_keys,
                       ensure_ascii=False)


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

def _read_inputs(files: list[str], slurp: bool, raw_input: bool):
    """Yield parsed JSON values from each file (or stdin)."""
    sources: list[tuple[str, object]] = []
    if not files:
        sources.append(("-", sys.stdin))
    else:
        for f in files:
            sources.append((f, None))

    if raw_input:
        if slurp:
            data = ""
            for name, handle in sources:
                if handle is None:
                    try:
                        with open(name, "r", encoding="utf-8") as fh:
                            data += fh.read()
                    except OSError as e:
                        raise JQError(f"{name}: {e.strerror or e}")
                else:
                    data += handle.read()
            yield data
        else:
            for name, handle in sources:
                if handle is None:
                    try:
                        with open(name, "r", encoding="utf-8") as fh:
                            for line in fh:
                                yield line.rstrip("\n").rstrip("\r")
                    except OSError as e:
                        raise JQError(f"{name}: {e.strerror or e}")
                else:
                    for line in handle:
                        yield line.rstrip("\n").rstrip("\r")
        return

    text_buffers: list[str] = []
    for name, handle in sources:
        if handle is None:
            try:
                with open(name, "r", encoding="utf-8") as fh:
                    text_buffers.append(fh.read())
            except OSError as e:
                raise JQError(f"{name}: {e.strerror or e}")
        else:
            text_buffers.append(handle.read())

    text = "".join(text_buffers)
    decoder = _json.JSONDecoder()
    pos = 0
    items: list = []
    while pos < len(text):
        # Skip whitespace
        while pos < len(text) and text[pos] in " \t\r\n":
            pos += 1
        if pos >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
        except _json.JSONDecodeError as e:
            raise JQError(f"parse error: {e.msg} at line {e.lineno} column {e.colno}")
        items.append(obj)
        pos = end

    if slurp:
        yield items
    else:
        for item in items:
            yield item


def main(argv: list[str]) -> int:
    args = argv[1:]
    raw_output = False
    compact = False
    tab = False
    sort_keys = False
    slurp = False
    null_input = False
    raw_input = False
    exit_status = False
    filter_expr: str | None = None
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            files.extend(args[i:])
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-r", "--raw-output"}:
            raw_output = True
            i += 1; continue
        if a in {"-c", "--compact-output"}:
            compact = True
            i += 1; continue
        if a == "--tab":
            tab = True
            i += 1; continue
        if a in {"-S", "--sort-keys"}:
            sort_keys = True
            i += 1; continue
        if a in {"-s", "--slurp"}:
            slurp = True
            i += 1; continue
        if a in {"-n", "--null-input"}:
            null_input = True
            i += 1; continue
        if a in {"-R", "--raw-input"}:
            raw_input = True
            i += 1; continue
        if a in {"-e", "--exit-status"}:
            exit_status = True
            i += 1; continue
        if a == "-j":
            # join: like -r but no trailing newlines. We just track raw.
            raw_output = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        if filter_expr is None:
            filter_expr = a
        else:
            files.append(a)
        i += 1

    if filter_expr is None:
        err(NAME, "missing filter expression")
        return 2

    try:
        tokens = _tokenize(filter_expr)
        program = Parser(tokens).parse()
    except JQError as e:
        err(NAME, f"compile error: {e}")
        return 3

    last_value = None
    produced_any = False
    try:
        if null_input:
            inputs = [None]
        else:
            inputs = list(_read_inputs(files, slurp, raw_input))
        for inp in inputs:
            for v in evaluate(program, inp):
                produced_any = True
                last_value = v
                sys.stdout.write(_format(v, raw=raw_output, compact=compact,
                                         sort_keys=sort_keys, tab=tab))
                sys.stdout.write("\n")
    except JQError as e:
        err(NAME, str(e))
        return 5
    sys.stdout.flush()

    if exit_status:
        if not produced_any:
            return 1
        if last_value is None or last_value is False:
            return 1
    return 0
