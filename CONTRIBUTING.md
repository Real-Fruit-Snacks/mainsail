# Contributing to mainsail

Thanks for your interest in mainsail. This guide covers the development
loop, coding conventions, and what to include in a PR.

## Development setup

**Prerequisites:** Python 3.10 or newer, `git`.

```bash
git clone https://github.com/<your-username>/mainsail.git
cd mainsail
pip install -e ".[dev]"          # editable install with test deps
```

**Verify:**

```bash
python -m pytest -q              # 373 unit tests
python -m mainsail --list        # should print all 75 applets
```

**Stress harness** (slower; exercises large inputs, Unicode, pipelines,
round-trips):

```bash
python scripts/stress.py
```

## Running against a frozen binary

To test real Nuitka builds:

```bash
pip install "Nuitka[onefile]"
python build.py                  # -> dist/mainsail (or .exe)
python scripts/stress.py dist/mainsail --quick
```

The `--quick` flag skips the slowest cases (50 sequential binary
invocations can OOM-kill on WSL).

## Running against the zipapp

The portable `mainsail.pyz` is a stdlib-only build (no Nuitka), useful
for quick packaging checks:

```bash
python build.py --pyz            # -> dist/mainsail.pyz (~125 KB)
python3 dist/mainsail.pyz --version
```

### Custom subsets

Build a smaller binary/zipapp with only the applets you need:

```bash
python build.py --preset slim              # 39 applets, no archives/hashing
python build.py --preset minimal           # 18 applets, scripting essentials
python build.py --applets ls,cat,grep,awk  # hand-picked set
python build.py --list-presets             # show preset contents
```

Savings are real for the zipapp (minimal is ~60 % smaller) but modest
for the Nuitka binary (~10–14 %) — the Python runtime dominates. Non-full
builds land as `dist/mainsail-<suffix>` (binary, `.exe`, or `.pyz`).

The zipapp uses the same code path as `python -m mainsail`, so it's not
a substitute for exercising a real Nuitka binary — but it is a fast way
to confirm the package import graph still works in a zipimport context.

## Adding a new applet

Applets live in `mainsail/applets/`. Each file is a standalone module
exposing:

```python
NAME = "myapplet"                # canonical name
ALIASES: list[str] = []          # alternate invocations (e.g. Windows names)
HELP = "one-line description"    # shown in --list

def main(argv: list[str]) -> int:
    # argv[0] is the applet name; argv[1:] are user args
    # return 0 on success, 1 on runtime error, 2 on usage error
    ...
    return 0
```

The registry auto-discovers the module on next launch. Add per-applet
help text to `mainsail/usage.py`. Add behavior tests to
`tests/test_applets.py`.

## Code style

- **Follow existing patterns** — look at neighbouring applets before
  inventing new conventions.
- **Minimal, POSIX-first flags** — implement the flags people actually
  reach for; don't try to match every GNU coreutils extension on day one.
- **Cross-platform** — Python stdlib first. Reach for `ctypes` only when
  stdlib genuinely can't cover the Linux-specific case (nothing in the
  current applet set needs this).
- **Binary-safe I/O** where semantics allow — read/write
  `sys.stdin.buffer` / `sys.stdout.buffer` for `cat`-like applets so
  null bytes and CRLF survive.
- **Error reporting** — use `from mainsail.common import err, err_path`;
  output goes to stderr with the `<applet>: <msg>` prefix.
- **Exit codes** — `0` success, `1` runtime error (missing file,
  permission denied), `2` usage error (bad flag).
- **No single-letter -h as help** — `-h` is reserved for applet-specific
  human-readable flags (`df -h`, `du -h`, `sort -h`, …). Only `--help`
  is intercepted by the CLI.

## Tests

All changes need tests. The suite runs on Linux, macOS, and Windows via
GitHub Actions on every PR.

```bash
python -m pytest -q              # run full suite
python -m pytest -q -k applet    # run tests whose name contains "applet"
python -m pytest -q -x           # stop on first failure
```

## Commit messages

Short imperative subject, optional body. Group related changes in one
commit; split unrelated changes.

```
grep: add -A/-B/-C context, -o, -w, -q

- -A N / -B N / -C N: after / before / both-sides context lines
- -o: print only the matching substring (one per match)
- -w: word-boundary match
- -q: quiet, exit 0/1 without output
```

## Pull request checklist

- [ ] `python -m pytest -q` passes (361/361)
- [ ] New/changed behavior has tests
- [ ] `mainsail <applet> --help` text updated in `mainsail/usage.py`
      when flags change
- [ ] `README.md` applet table updated when adding an applet
- [ ] `CHANGELOG.md` entry under `[Unreleased]`

## License

By submitting a PR you agree that your contribution will be licensed
under the MIT License (the same license as the rest of the project).
