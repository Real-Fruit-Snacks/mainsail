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
![Tests](https://img.shields.io/badge/tests-373%20passing-brightgreen.svg)

A BusyBox-style multi-call binary in Python — **75 Unix utilities**, one ~5–7 MB executable, native on Linux, Windows, and macOS.

[Download Latest](https://github.com/Real-Fruit-Snacks/mainsail/releases/latest)
&nbsp;·&nbsp;
[GitHub Pages](https://real-fruit-snacks.github.io/mainsail/)
&nbsp;·&nbsp;
[Changelog](CHANGELOG.md)

</div>

---

## Quick Start

**From a release** — no Python required:

```bash
# Linux (glibc — Ubuntu, Debian, RHEL, …)
curl -LO https://github.com/Real-Fruit-Snacks/mainsail/releases/latest/download/mainsail-linux-x64
chmod +x mainsail-linux-x64
./mainsail-linux-x64 --version
```

**From source** — Python 3.10+:

```bash
git clone https://github.com/Real-Fruit-Snacks/mainsail.git
cd mainsail
pip install -e .
mainsail --list
```

**Wire up your shell + stay current:**

```bash
mainsail completions bash | sudo tee /etc/bash_completion.d/mainsail   # tab-complete applets
mainsail update                                                        # self-update from latest GitHub release
mainsail update --check                                                # see what would change without downloading
```

---

## Pre-built artifacts

Every release tag (`v0.x.x`) ships **13 artifacts** built and verified by GitHub Actions:

### Native binaries

| Target                            | Full _(73 applets)_                 | Slim _(39 applets — POSIX coreutils only)_ |
|-----------------------------------|-------------------------------------|-------------------------------------------|
| Linux x86_64 (glibc 2.35+)        | `mainsail-linux-x64`                | `mainsail-linux-x64-slim`                 |
| Linux ARM64 (glibc 2.39+)         | `mainsail-linux-arm64`              | `mainsail-linux-arm64-slim`               |
| Linux x86_64 **musl** (Alpine)    | `mainsail-linux-x64-musl` ✱         | _(use the full one or build slim locally)_ |
| Windows x86_64                    | `mainsail-windows-x64.exe`          | `mainsail-windows-x64-slim.exe`           |
| Windows ARM64                     | `mainsail-windows-arm64.exe`        | `mainsail-windows-arm64-slim.exe`         |
| macOS ARM64 (Apple Silicon)       | `mainsail-macos-arm64`              | `mainsail-macos-arm64-slim`               |

✱ The `-musl` build runs on Alpine and any musl-libc Linux (distroless containers, `gcr.io/distroless/static`, etc.). It does **not** run on glibc systems — use the regular `mainsail-linux-x64` for those.

Drop any binary anywhere on `PATH` and run.

### Portable zipapp

| Artifact            | Size     | Applets | Notes                                         |
|---------------------|----------|---------|-----------------------------------------------|
| `mainsail.pyz`      | ~125 KB  | 73      | runs on any host with Python 3.8+             |
| `mainsail-slim.pyz` | ~70 KB   | 39      | POSIX coreutils only — drops `jq`, `http`, `dig`, `nc`, archives, hashing, parity extras |

Useful for ESXi (which bundles Python 3 since 7.0U3), exotic architectures, jailbroken routers, and corporate machines where installing a native binary isn't practical:

```bash
scp mainsail.pyz host:/tmp/
ssh host 'python3 /tmp/mainsail.pyz find /var/log -mtime -7'
```

### Build your own

Pick exactly the applets you need:

```bash
python build.py --preset slim                      # 39 applets, no archives/hashing
python build.py --preset minimal                   # 18 applets, scripting essentials
python build.py --applets ls,cat,grep,sed,awk      # hand-picked
python build.py --pyz --applets ls,cat,grep,sed    # smallest zipapp (~24 KB for 4 applets; ~36 KB once awk is included)
python build.py --list-presets                     # see what's in each preset
```

Savings are real for the zipapp (full ≈ 127 KB, slim ≈ 72 KB, minimal ≈ 49 KB) and meaningful for the Nuitka binary now that v0.2.x ships 73 applets (slim drops 34 of them, ~10–14 % off the binary). Non-full builds land as `dist/mainsail-<suffix>` (with matching `.exe`/`.pyz` extension).

> **Why no fully-static Linux binary?** We tried. `LDFLAGS=-static` and `--static-libpython=yes` both link cleanly, but Python then refuses to load any C extension at runtime with `ImportError: Dynamic loading not supported` — a fully-static Python interpreter can't `dlopen()`. A truly self-contained Python binary requires baking every extension into `libpython` at compile time, which `python-build-standalone` doesn't ship. So we offer the musl-linked variant for Alpine/distroless users and the dynamic glibc binary for everyone else.
>
> **Why no `linux-arm64-musl`?** GitHub Actions doesn't support Node.js actions inside Alpine containers on ARM64 runners — only x64. Until that changes, ARM64 users have the dynamic glibc binary, the portable `mainsail.pyz`, or can build a musl variant locally on Alpine.
>
> **Why no `mainsail-macos-x64`?** GitHub's free-tier `macos-13` runner queue is effectively unavailable to this project (30+ minute queues, never dispatched). Apple stopped shipping Intel Macs in 2023; the ARM64 binary covers the supported lineup. Intel-Mac users can use the portable `mainsail.pyz` or build from source.

---

## Features

### One binary, seventy-three utilities

Every common POSIX tool you'd reach for in a shell pipeline — plus `jq` for JSON, `http` for HTTP, `dig` for DNS, `nc` for TCP, and the BusyBox parity gap-fillers (`dd`, `od`, `hexdump`, `diff`, `join`, `fmt`, …). Dispatch via `mainsail <applet>` or symlink/hardlink to call the applet directly.

```bash
mainsail ls -la                          # GNU-style flags
mainsail cat file.txt | mainsail grep -C 2 pattern
mainsail find . -name '*.py' -size +1k -mtime -7
mainsail seq 100 | mainsail sort -rn | mainsail head -5
```

### Native Windows

No WSL, no Cygwin, no git-bash. `mainsail.exe` runs on bare Windows and recognises Windows-native command names as aliases.

```cmd
mainsail dir .                           :: == ls
mainsail type file.txt                   :: == cat
mainsail copy a.txt b.txt                :: == cp
mainsail del old.txt                     :: == rm
mainsail where python                    :: == which
```

### Real applets, not stubs

Each applet implements the common POSIX flags and edge cases.

- `find` — expression tree with `-exec`, `-prune`, `-and`/`-or`, parens, size/time predicates, `-delete`
- `sed` — `s///`, `d`, `p`, `q`, `=`, `y///`, addresses, ranges, negation, `-i` in-place edit, BRE + ERE
- `awk` — BEGIN/END, `/regex/` and expression patterns, range patterns, `print`/`printf`, full control flow, associative arrays, the standard built-ins (`length`, `substr`, `index`, `split`, `sub`, `gsub`, `match`, `toupper`, `tolower`, `sprintf`, `int`)
- `jq` — practical subset: pipes, comma, alternatives, comparison/arithmetic, object & array constructors, slices and iterators, `if`/`then`/`elif`/`else`/`end`, **40+ built-in functions** (`select`, `map`, `sort_by`, `unique_by`, `to_entries`, `with_entries`, `paths`, `split`, `join`, `startswith`, …), raw output (`-r`), compact (`-c`), slurp (`-s`)
- `http` — `GET`/`POST`/`PUT`/`DELETE`/`HEAD`, custom headers, body literal or `@file`, `--json` shortcut, redirect-following on by default, `--fail` for HTTP errors
- `dig` — direct UDP DNS queries: A, AAAA, MX, TXT, CNAME, NS, SOA, PTR; `+short`; reverse lookups via `-x`
- `sort` — `-k` key fields, `-t` custom separator, `-o` output file, numeric/reverse/unique
- `tar` — create/extract/list with gzip/bzip2/xz filters; accepts traditional (`cvfz`) and dashed (`-cvfz`) flag forms

```bash
mainsail find . -name '*.tmp' -delete
mainsail sed -i 's/foo/bar/g' *.txt
mainsail awk -F, '{s+=$3} END{print s/NR}' data.csv
mainsail jq '.servers[] | select(.region == "us") | .name' inventory.json
mainsail http -H 'Authorization: Bearer $TOKEN' https://api.example.com/me
mainsail dig MX gmail.com +short
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

Same SHA-256 of `"abc"` (`ba7816bf…015ad`) on every supported platform. `tar` archives are interchangeable. The CI suite runs 361 unit tests on Linux/macOS/Windows and a 23-case stress harness covering large inputs, Unicode, binary-safe streams, deep trees, pipelines, round-trips, and edge cases.

---

## Supported applets

| Category    | Applets |
|-------------|---------|
| File ops    | `ls` `cp` `mv` `rm` `mkdir` `touch` `find` `chmod` `ln` `stat` `truncate` `mktemp` `dd` |
| Text        | `cat` `tac` `rev` `grep` `head` `tail` `wc` `nl` `sort` `uniq` `cut` `paste` `tr` `sed` `awk` `tee` `xargs` `printf` `echo` `expand` `unexpand` `split` `cmp` `comm` `diff` `join` `fmt` `od` `hexdump` |
| **JSON**    | **`jq`** _(practical subset: pipes, filters, select/map/sort_by, object & array constructors, 40+ built-in functions)_ |
| **Network** | **`http`** _(curl-style GET/POST with headers, body, JSON, redirects)_ • **`dig`** _(DNS A/AAAA/MX/TXT/CNAME/NS/SOA/PTR via direct UDP queries)_ • **`nc`** _(TCP netcat: connect, listen, port-scan)_ |
| Hashing     | `md5sum` `sha1sum` `sha256sum` `sha512sum` |
| Archives    | `tar` `gzip` `gunzip` `zip` `unzip` |
| Filesystem  | `du` `df` |
| Paths       | `basename` `dirname` `realpath` `pwd` `which` |
| System      | `uname` `hostname` `whoami` `date` `env` `sleep` `getopt` |
| Control     | `true` `false` `yes` `seq` |
| **Lifecycle** | **`completions`** _(emit bash/zsh/fish/powershell completion scripts)_ • **`update`** _(self-update from the latest GitHub release; atomic replace, keeps `.old` next to the binary)_ |

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
    └── ...          # 73 modules total
```

**Four-layer flow:**

1. **Entry** — `__main__.py` or the installed `mainsail` script enters `cli.main(argv)`.
2. **Dispatch** — `cli.py` checks `argv[0]` basename for multi-call (e.g. `ls -la` when hardlinked); otherwise treats `argv[1]` as the applet name. Intercepts `--help` (long form only — `-h` is reserved for applet flags like `df -h`).
3. **Registry** — `registry.py` lazy-loads `mainsail.applets.*` once via `pkgutil.iter_modules`, registering each module's `NAME` + `ALIASES` → `main` function.
4. **Applet** — receives `argv` as a list, returns an exit code (`0` success, `1` runtime error, `2` usage error). Reads stdin via `sys.stdin.buffer` for binary safety; writes via `sys.stdout` / `sys.stdout.buffer`.

Adding a new applet means dropping a module into `mainsail/applets/` with the four-symbol contract. Auto-discovery picks it up on next launch.

---

## Development

```bash
pip install -e ".[dev]"            # install with test deps
python -m pytest -q                # 361 unit tests
python scripts/stress.py           # 23-case stress harness
python scripts/stress.py dist/mainsail.exe --quick   # against a frozen binary
```

### Building

```bash
pip install "Nuitka[onefile]"
python build.py                                    # full Nuitka binary
python build.py --pyz                              # portable zipapp
python build.py --preset slim                      # binary, slim preset
python build.py --pyz --applets ls,cat,grep,awk    # custom zipapp
python build.py --list-presets                     # show preset contents
```

Output is a single self-contained executable. Approximate sizes for v0.2.1 (full preset): Windows x64 ≈ 5.3 MB, Windows ARM64 ≈ 6.2 MB, Linux x64 (glibc) ≈ 6.2 MB, Linux ARM64 (glibc) ≈ 7.1 MB, macOS ARM64 ≈ 5.7 MB, Linux x64 (Alpine/musl) ≈ 7.2 MB. Compressed with zstandard. No Python needed at runtime.

CI builds **ten native glibc binaries** (five full + five slim), **two zipapps** (full + slim), and **one musl-linked Linux x64 binary** on every release tag.

---

## License

MIT.
