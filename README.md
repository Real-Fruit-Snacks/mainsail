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
![Tests](https://img.shields.io/badge/tests-268%20passing-brightgreen.svg)

**Single-file BusyBox-like multi-call binary, in Python.**

51 POSIX utilities — `ls`, `cat`, `grep`, `sed`, `awk`, `tar`, and friends — bundled into a ~5 MB executable. Native Windows support without WSL, Cygwin, or git-bash. Five native targets (Linux/Windows × x86_64/ARM64, macOS ARM64) plus an ~80 KB portable zipapp that runs anywhere Python 3.8+ is installed — including ESXi.

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
| macOS           | — _(see below)_             | `mainsail-macos-arm64`        |

_Intel Mac support: GitHub's free-tier `macos-13` runner queue is effectively unavailable to this project, so we don't ship a pre-built `mainsail-macos-x64`. Intel Mac users can use the portable **`mainsail.pyz`** (same feature set, needs Python 3.8+) or `pip install -e .` from source._

Drop it anywhere on `PATH` and run.

**Slim variants** — every native binary above is also shipped as `…-slim` (e.g. `mainsail-linux-x64-slim`). Slim drops the archive (`tar`, `gzip`, `gunzip`, `zip`, `unzip`) and hashing (`md5sum`, `sha*sum`) applets. Nuitka-binary savings are modest (~3 %) since the Python runtime dominates the payload — prefer slim only if you truly need fewer utilities.

**Fully static Linux variants** — `mainsail-linux-x64-static` and `mainsail-linux-arm64-static` are built inside Alpine, link against musl, and have **zero shared-library dependencies**. They run on any Linux kernel — distroless containers, embedded systems, glibc-only systems, anything. Slightly larger than the dynamic glibc binary, but maximum portability. (Built best-effort; if a release didn't ship them, the static toolchain hit a snag — file an issue.)

**Or use the portable zipapp** — `mainsail.pyz` (~80 KB full, ~68 KB slim) runs on any host with Python 3.8+, including ESXi, exotic architectures, jailbroken routers, and restrictive corporate machines where installing a native binary isn't practical:

```bash
scp mainsail.pyz host:/tmp/
ssh host 'python3 /tmp/mainsail.pyz ls -la'
```

**Or build your own custom subset** — pick exactly the applets you want:

```bash
python build.py --applets ls,cat,grep,sed,awk        # Nuitka binary
python build.py --pyz --applets ls,cat,grep,sed,awk  # zipapp
python build.py --list-presets                       # show slim/minimal
```

For a zipapp, a 5-applet custom build is well under 20 KB.

---

## Features

### One binary, fifty-one utilities

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

Each applet implements the common POSIX flags and edge cases. `find` has an expression tree with `-exec`, `-prune`, `-and`/`-or`, parens. `sed` has substitution, addresses, in-place edit, BRE/ERE. `awk` covers BEGIN/END, patterns, ranges, arrays, `gsub`, `printf`, and the standard built-ins. `sort` has key fields and separators. `tar` handles `-z`/`-j`/`-xz` compression and traditional + dashed flag forms.

```bash
mainsail find . -name '*.tmp' -delete
mainsail sed -i 's/foo/bar/g' *.txt
mainsail awk -F, '{s+=$3} END{print s/NR}' data.csv
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

Same SHA-256 of `"abc"` (`ba7816bf...015ad`) on every supported platform. `tar` archives are interchangeable. Stress harness verifies 23 scenarios on Linux, Windows, and macOS CI runners.

---

## Supported applets

| Category    | Applets |
|-------------|---------|
| File ops    | `ls` `cp` `mv` `rm` `mkdir` `touch` `find` `chmod` `ln` `stat` |
| Text        | `cat` `grep` `head` `tail` `wc` `sort` `uniq` `cut` `tr` `sed` `awk` `tee` `xargs` `printf` `echo` |
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
    └── ...          # 51 modules total
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
python -m pytest -q                # 268 unit tests
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
# -> dist/mainsail.pyz (~80 KB, runs on any Python 3.8+)
```

No compilation, no dependencies. Useful for ESXi, exotic architectures, and any host that already has Python.

### Custom applet subsets

Trim the build to just the applets you want:

```bash
python build.py --preset slim                           # 39 applets, no archives/hashing
python build.py --preset minimal                        # 18 applets, scripting essentials
python build.py --applets ls,cat,grep,sed,awk           # hand-picked
python build.py --pyz --applets ls,cat,grep,sed,awk     # same but zipapp
python build.py --list-presets                          # see what's in each
```

Non-full builds land as `dist/mainsail-<suffix>` (or `.exe`, or `.pyz`). Savings are meaningful for the zipapp (44% smaller for minimal) but modest for the Nuitka binary (~3–5%) because the Python runtime is the bulk of the payload.

CI matrix builds **ten native binaries** (five full, five slim), **two zipapps** (`mainsail.pyz` full and `mainsail-slim.pyz`), and **two fully-static Linux binaries** (`mainsail-linux-x64-static`, `mainsail-linux-arm64-static`, built in Alpine + musl, no shared-lib dependencies) on every release tag.

---

## License

MIT.
