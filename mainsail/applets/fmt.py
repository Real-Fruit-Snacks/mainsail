"""mainsail fmt — simple paragraph reflow."""
from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "fmt"
ALIASES: list[str] = []
HELP = "simple optimal text formatter"


def _reflow(paragraph: list[str], width: int, prefix: str = "") -> list[str]:
    """Reflow a list of input lines into paragraphs of at most `width` cols."""
    words: list[str] = []
    for line in paragraph:
        words.extend(line.split())
    if not words:
        return []
    out: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        # +1 for separating space if cur not empty
        new_len = cur_len + len(w) + (1 if cur else 0)
        if cur and new_len > width - len(prefix):
            out.append(prefix + " ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len = new_len
    if cur:
        out.append(prefix + " ".join(cur))
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    width = 75
    uniform = False  # -u: collapse multiple spaces between words
    crown = False  # -c: indent first/second lines like the original
    tagged = False
    split_only = False  # -s: split long lines but don't merge

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-w", "--width"} and i + 1 < len(args):
            try:
                width = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid width: {args[i + 1]}")
                return 2
            i += 2; continue
        if a.startswith("-w"):
            try:
                width = int(a[2:])
            except ValueError:
                err(NAME, f"invalid width: {a[2:]}")
                return 2
            i += 1; continue
        if a == "-u" or a == "--uniform-spacing":
            uniform = True
            i += 1; continue
        if a == "-c" or a == "--crown-margin":
            crown = True
            i += 1; continue
        if a == "-t" or a == "--tagged-paragraph":
            tagged = True
            i += 1; continue
        if a == "-s" or a == "--split-only":
            split_only = True
            i += 1; continue
        if a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            width = int(a[1:])
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    files = args[i:] or ["-"]
    rc = 0
    out_lines: list[str] = []

    for f in files:
        try:
            if f == "-":
                lines = sys.stdin.read().splitlines()
            else:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue

        # Group into paragraphs separated by blank lines.
        paragraph: list[str] = []
        for line in lines:
            if line.strip() == "":
                if paragraph:
                    if split_only:
                        for p_line in paragraph:
                            for sub in _split_long(p_line, width):
                                out_lines.append(sub)
                    else:
                        out_lines.extend(_reflow(paragraph, width))
                    paragraph = []
                out_lines.append("")
            else:
                paragraph.append(line)
        if paragraph:
            if split_only:
                for p_line in paragraph:
                    for sub in _split_long(p_line, width):
                        out_lines.append(sub)
            else:
                out_lines.extend(_reflow(paragraph, width))

    sys.stdout.write("\n".join(out_lines) + ("\n" if out_lines else ""))
    sys.stdout.flush()
    return rc


def _split_long(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    out = []
    cur = ""
    for word in line.split():
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        elif cur:
            cur += " " + word
        else:
            cur = word
    if cur:
        out.append(cur)
    return out
