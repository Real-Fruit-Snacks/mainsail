<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-light.svg">
  <img alt="mainsail" src="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-dark.svg" width="560">
</picture>

![Python](https://img.shields.io/badge/language-Python-3776ab.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)
![Arch](https://img.shields.io/badge/arch-x86__64%20%7C%20ARM64-blue)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Tests](https://img.shields.io/badge/tests-226%20passing-brightgreen.svg)

**Single-file BusyBox-like multi-call binary, in Python.**

50 POSIX utilities — `ls`, `cat`, `grep`, `sed`, `tar`, and friends — bundled into a 7 MB executable. Native Windows support without WSL, Cygwin, or git-bash. Pure Python; freezable to a standalone binary with Nuitka.

</div>

---

## Quick Start

**Prerequisites:** Python 3.10+

```bash
git clone https://github.com/Real-Fruit-Snacks/mainsail.git
cd mainsail
pip install -e .
```

**Verify:**

```bash
mainsail --version
mainsail --list
mainsail ls --help
```

**Or grab a pre-built binary** — no Python required:

| Platform        | x86_64                      | ARM64                         |
|-----------------|-----------------------------|-------------------------------|
| Linux           | `mainsail-linux-x64`        | `mainsail-linux-arm64`        |
| Windows         | `mainsail-windows-x64.exe`  | `mainsail-windows-arm64.exe`  |
| macOS           | `mainsail-macos-x64`        | `mainsail-macos-arm64`        |

Drop it anywhere on `PATH` and run.

**Or use the portable zipapp** — `mainsail.pyz` (~66 KB) runs on any host with Python 3.8+, including ESXi, exotic architectures, jailbroken routers, and restrictive corporate machines where installing a native binary isn't practical:

```bash
scp mainsail.pyz host:/tmp/
ssh host 'python3 /tmp/mainsail.pyz ls -la'
```

---

## Features

### One binary, fifty utilities

Every common POSIX tool you'd reach for in a shell pipeline. Dispatch via `mainsail <applet>` or symlink/hardlink to call directly.

```bash
mainsail ls -la                          # GNU-style flags
mainsail cat file.txt | mainsail grep -C 2 pattern
mainsail find . -name '*.py' -size +1k -mtime -7
mainsail seq 100 | mainsail sort -rn | mainsail head -5
```

### Native Windows

No WSL, no Cygwin. `mainsail.exe` runs on bare Windows and recognizes Windows-native command names as aliases.

```cmd
mainsail dir .                           :: == ls
mainsail type file.txt                   :: == cat
mainsail copy a.txt b.txt                :: == cp
mainsail del old.txt                     :: == rm
mainsail where python                    :: == which
```

### Real applets, not stubs

Each applet implements the common POSIX flags and edge cases. `find` has an expression tree with `-exec`, `-prune`, `-and`/`-or`, parens. `sed` has substitution, addresses, in-place edit, BRE/ERE. `sort` has key fields and separators. `tar` handles `-z`/`-j`/`-xz` compression and traditional + dashed flag forms.

```bash
mainsail find . -name '*.tmp' -delete
mainsail sed -i 's/foo/bar/g' *.txt
mainsail sort -k 3,3n -t , data.csv
mainsail tar -czf src.tar.gz src/ --exclude='*.pyc'
```

### Pipeline-grade I/O

Binary-safe through `cat`/`tee`/`gzip`. CRLF survives Windows text-mode round-trips. `tail -f` follows files and detects rotation. `xargs` accepts `-print0`/`-0` to handle Windows backslashes.

```bash
mainsail find . -type f -print0 | mainsail xargs -0 mainsail sha256sum
mainsail tail -f /var/log/app.log
mainsail gzip -c data.bin | mainsail gunzip > data.bin.copy
```

### Cross-platform integrity

Same SHA-256 of `"abc"` (`ba7816bf...015ad`) on Windows and Linux. `tar` archives are interchangeable. Stress harness verifies 23 scenarios across both platforms.

---

## Supported applets

| Category    | Applets |
|-------------|---------|
| File ops    | `ls` `cp` `mv` `rm` `mkdir` `touch` `find` `chmod` `ln` `stat` |
| Text        | `cat` `grep` `head` `tail` `wc` `sort` `uniq` `cut` `tr` `sed` `tee` `xargs` `printf` `echo` |
| Hashing     | `md5sum` `sha1sum` `sha256sum` `sha512sum` |
| Archives    | `tar` `gzip` `gunzip` `zip` `unzip` |
| Filesystem  | `du` `df` |
| Paths       | `basename` `dirname` `realpath` `pwd` `which` |
| System      | `uname` `hostname` `whoami` `date` `env` `sleep` |
| Control     | `true` `false` `yes` `seq` |

Run `mainsail --list` for the full set with one-line descriptions, or `mainsail <applet> --help` for per-applet usage and flags.

---

## Architecture

```
mainsail/
├── __main__.py      # python -m mainsail
├── cli.py           # dispatch: argv[0] multi-call + subcommand modes
├── registry.py      # auto-discovery of applet modules
├── usage.py         # per-applet --help text
├── common.py        # shared helpers: err, user_name, should_overwrite
└── applets/         # one module per applet, all implement
    ├── ls.py        #   NAME, ALIASES, HELP, main(argv) -> int
    ├── cat.py
    └── ...          # 50 modules total
```

**Four-layer flow:**

1. **Entry** — `__main__.py` or installed `mainsail` script enters `cli.main(argv)`.
2. **Dispatch** — `cli.py` checks `argv[0]` basename for multi-call (e.g. `ls -la` when hardlinked); otherwise treats `argv[1]` as the applet name. Intercepts `--help` (long form only — `-h` is reserved for applet flags like `df -h`).
3. **Registry** — `registry.py` lazy-loads `mainsail.applets.*` once, registering each module's `NAME` + `ALIASES` → `main` function.
4. **Applet** — receives `argv` as a list, returns an exit code (0 success, 1 runtime error, 2 usage error). Reads stdin via `sys.stdin.buffer` for binary safety; writes via `sys.stdout` / `sys.stdout.buffer`.

Adding a new applet means dropping a module into `mainsail/applets/` with the four-symbol contract. Auto-discovery picks it up on next launch.

---

## Development

```bash
pip install -e ".[dev]"            # install with test deps
python -m pytest -q                # 226 unit tests
python scripts/stress.py           # 23-case stress harness
python scripts/stress.py dist/mainsail.exe --quick   # against frozen binary
```

### Building a standalone binary

```bash
pip install "Nuitka[onefile]"
python build.py
# -> dist/mainsail (Linux/macOS) or dist/mainsail.exe (Windows)
```

Output is a single self-contained executable: ~4.5 MB on Windows, ~6 MB on Linux. Compressed with zstandard. No Python needed at runtime.

### Building the portable zipapp

```bash
python build.py --pyz
# -> dist/mainsail.pyz (~66 KB, runs on any Python 3.8+)
```

No compilation, no dependencies. Useful for ESXi, exotic architectures, and any host that already has Python.

CI matrix builds **six native binaries** (Linux/Windows/macOS × x86_64/ARM64) plus the portable `mainsail.pyz` on every release tag.

---

## License

MIT.
