from __future__ import annotations

import sys

from mainsail.common import err, err_path

NAME = "wc"
ALIASES: list[str] = []
HELP = "print newline, word, and byte counts for each file"


def _count(fh) -> tuple[int, int, int, int]:
    lines = words = bytes_ = chars = 0
    for raw in fh:
        bytes_ += len(raw)
        lines += 1 if raw.endswith(b"\n") else 0
        try:
            text = raw.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
        chars += len(text)
        words += len(text.split())
    return lines, words, bytes_, chars


def main(argv: list[str]) -> int:
    args = argv[1:]
    want_lines = want_words = want_bytes = want_chars = False
    files: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            files.extend(args[i + 1:])
            break
        if a == "-" or not a.startswith("-") or len(a) < 2:
            files.append(a)
        else:
            for ch in a[1:]:
                if ch == "l":
                    want_lines = True
                elif ch == "w":
                    want_words = True
                elif ch == "c":
                    want_bytes = True
                elif ch == "m":
                    want_chars = True
                else:
                    err(NAME, f"invalid option: -{ch}")
                    return 2
        i += 1

    if not (want_lines or want_words or want_bytes or want_chars):
        want_lines = want_words = want_bytes = True

    if not files:
        files = ["-"]

    totals = [0, 0, 0, 0]
    rc = 0
    results: list[tuple[tuple[int, int, int, int], str]] = []

    for f in files:
        try:
            fh = sys.stdin.buffer if f == "-" else open(f, "rb")
        except OSError as e:
            err_path(NAME, f, e)
            rc = 1
            continue
        close = f != "-"
        try:
            counts = _count(fh)
        finally:
            if close:
                fh.close()
        results.append((counts, f))
        for k in range(4):
            totals[k] += counts[k]

    def fmt(counts: tuple[int, int, int, int], label: str) -> str:
        parts: list[str] = []
        if want_lines:
            parts.append(f"{counts[0]:>7}")
        if want_words:
            parts.append(f"{counts[1]:>7}")
        if want_bytes:
            parts.append(f"{counts[2]:>7}")
        if want_chars:
            parts.append(f"{counts[3]:>7}")
        if label and label != "-":
            parts.append(label)
        return " ".join(parts)

    for counts, label in results:
        sys.stdout.write(fmt(counts, label) + "\n")
    if len(results) > 1:
        sys.stdout.write(fmt(tuple(totals), "total") + "\n")  # type: ignore[arg-type]

    return rc
