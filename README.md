<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-light.svg">
  <img alt="Mainsail" src="https://raw.githubusercontent.com/Real-Fruit-Snacks/mainsail/main/docs/assets/logo-dark.svg" width="100%">
</picture>

> [!IMPORTANT]
> **A BusyBox-style multi-call binary in Python** — 84 Unix utilities, one ~6 MB Nuitka executable or a ~148 KB portable zipapp, native on Linux, Windows, and macOS. The reference implementation that the Rust ([`jib`](https://github.com/Real-Fruit-Snacks/jib)), Go ([`topsail`](https://github.com/Real-Fruit-Snacks/topsail)), Zig ([`staysail`](https://github.com/Real-Fruit-Snacks/Staysail)), Lua ([`moonraker`](https://github.com/Real-Fruit-Snacks/Moonraker)), and NASM ([`rill`](https://github.com/Real-Fruit-Snacks/rill)) ports all match against.

> *A mainsail is the central, primary sail on a vessel — the one every other sail trims to. Felt fitting for the canonical Python implementation that defines the applet contract for the rest of the family.*

---

## §1 / Premise

Mainsail is the **reference implementation**. Easy to embed, easy to read, easy to extend — drop a module into `mainsail/applets/` with the four-symbol contract (`NAME`, `ALIASES`, `HELP`, `main`), and auto-discovery picks it up.

The applet roster, flag conventions, exit codes, and stdout byte semantics defined here are what the sister projects ([jib](https://github.com/Real-Fruit-Snacks/jib), [topsail](https://github.com/Real-Fruit-Snacks/topsail), [staysail](https://github.com/Real-Fruit-Snacks/Staysail), [moonraker](https://github.com/Real-Fruit-Snacks/Moonraker), [rill](https://github.com/Real-Fruit-Snacks/rill)) verify against. Mainsail's tradeoff is **interpreter cold-start**; what it gives back is a 148 KB portable `.pyz` that runs anywhere Python 3.8+ does — ESXi, jailbroken routers, exotic architectures, locked-down corporate boxes — and a Python codebase that's the easiest in the family to fork and bend.

---

## §2 / Specs

| KEY      | VALUE                                                                       |
|----------|-----------------------------------------------------------------------------|
| BINARY   | **~6 MB Nuitka onefile** (zstandard) · **~148 KB portable `.pyz`** (Python 3.8+) |
| APPLETS  | **84 POSIX utilities** + `jq` (47 builtins) + `http` + `dig` + `nc` + lifecycle ops |
| BUILDS   | **13 release artifacts** — 5 native + 1 musl + 5 slim native + full + slim `.pyz` |
| LIFECYCLE | `install-aliases` · `completions` (bash/zsh/fish/powershell) · `update` self-update |
| TESTS    | **402 unit tests** + 23-case stress harness (Linux / macOS / Windows)       |
| STACK    | Python **3.10+** · Nuitka onefile · zipapp · zero runtime deps              |

Architecture in §5 below.

---

## §3 / Quickstart

```bash
# From a release — no Python required
curl -LO https://github.com/Real-Fruit-Snacks/mainsail/releases/latest/download/mainsail-linux-x64
chmod +x mainsail-linux-x64
./mainsail-linux-x64 --list

# From source — Python 3.10+
git clone https://github.com/Real-Fruit-Snacks/mainsail && cd mainsail
pip install -e .
mainsail --list

# Or via pipx — isolated venv, mainsail on PATH
pipx install git+https://github.com/Real-Fruit-Snacks/mainsail.git
```

```bash
# Wire up your shell — symlinks, completions, self-update
mainsail install-aliases ~/.local/bin                                # symlink ls/cat/grep/... to mainsail
mainsail completions bash | sudo tee /etc/bash_completion.d/mainsail
mainsail update                                                       # self-update from latest release
mainsail update --check                                               # see what would change
```

```bash
# Portable zipapp — runs anywhere Python 3.8+ does
scp mainsail.pyz host:/tmp/
ssh host 'python3 /tmp/mainsail.pyz find /var/log -mtime -7'

# Build your own — pick exactly the applets you need
python build.py                                    # full Nuitka binary
python build.py --pyz                              # portable zipapp
python build.py --preset slim                      # 39 applets, no archives/hashing
python build.py --pyz --applets ls,cat,grep,sed,awk    # ~36 KB hand-picked zipapp
```

```bash
# Native Windows — no WSL / Cygwin / git-bash
mainsail dir .                                  :: == ls
mainsail type file.txt                          :: == cat
mainsail copy a.txt b.txt                       :: == cp
mainsail del old.txt                            :: == rm
mainsail where python                           :: == which
```

---

## §4 / Reference

```
APPLET CATEGORIES                                       # 84 total

  FILE OPS      ls cp mv rm mkdir touch find chmod ln stat truncate mktemp dd
  TEXT          cat tac rev grep head tail wc nl sort uniq cut paste tr
                sed awk tee xargs printf echo expand unexpand split cmp
                comm diff join fmt fold column od hexdump base64
  JSON          jq (pipes · filters · select/map/sort_by · 47 builtins · -r/-c/-s)
  NETWORK       http (GET/POST/PUT/DELETE/HEAD · headers · @file · --json)
                dig (UDP DNS: A/AAAA/MX/TXT/CNAME/NS/SOA/PTR · +short · -x)
                nc  (TCP: connect · listen · port-scan)
  HASHING       md5sum · sha1sum · sha256sum · sha512sum
  ARCHIVES      tar (gzip/bzip2/xz) · gzip · gunzip · zip · unzip
  FILESYSTEM    du · df
  PATHS         basename · dirname · realpath · pwd · which
  PROCESS       watch · timeout
  SYSTEM        uname · hostname · whoami · id · groups · date · env
                sleep · getopt · uuidgen
  CONTROL       true · false · yes · seq
  LIFECYCLE     install-aliases · completions · update

DISPATCH

  mainsail <applet> [args]                  # subcommand form
  ln -s mainsail <applet>                   # multi-call: argv[0] basename
                                            # both dispatch identically
                                            # Windows aliases: dir/type/copy/del/where

RELEASE ARTIFACTS                                       # 13 per release tag

  Linux x86_64 (glibc 2.35+)               mainsail-linux-x64 · -slim
  Linux ARM64 (glibc 2.39+)                mainsail-linux-arm64 · -slim
  Linux x86_64 musl (Alpine)               mainsail-linux-x64-musl
  Windows x86_64                           mainsail-windows-x64.exe · -slim
  Windows ARM64                            mainsail-windows-arm64.exe · -slim
  macOS ARM64 (Apple Silicon)              mainsail-macos-arm64 · -slim
  Portable zipapp                          mainsail.pyz · mainsail-slim.pyz

NOTABLE FLAG SUPPORT
  find          expression tree · -exec · -prune · -and/-or · parens
                size/time predicates · -delete
  sed           s/// d p q = y/// addresses ranges negation -i in-place BRE+ERE
  awk           BEGIN/END · /regex/ · expressions · ranges · printf · arrays
                length/substr/index/split/sub/gsub/match/toupper/tolower/sprintf
  jq            pipes · comma · alternatives · constructors · slices · iterators
                47 builtins (select/map/sort_by/unique_by/to_entries/with_entries/
                paths/split/join/startswith/...) · -r raw · -c compact · -s slurp
  http          GET/POST/PUT/DELETE/HEAD · -H · -d · @file · --json · --fail
  dig           A/AAAA/MX/TXT/CNAME/NS/SOA/PTR · +short · reverse via -x
  tar           create / extract / list · gzip/bzip2/xz · traditional + dashed flags

BUILD PRESETS
  full       (default)   84 applets       Everything
  slim                   39 applets       POSIX coreutils only
  minimal                18 applets       Scripting essentials
  --applets ls,cat,...                    Hand-picked subset

DEVELOPMENT
  pip install -e ".[dev]"                  Install with test deps
  python -m pytest -q                      402 unit tests
  python scripts/stress.py                 23-case stress harness
  python build.py [--pyz] [--preset ...]   Nuitka onefile or portable zipapp
```

---

## §5 / Architecture

```
mainsail/
  __main__.py     entry → cli.main(argv)
  cli.py          dispatch · argv[0] multi-call + subcommand modes
  registry.py     auto-discovery · pkgutil.iter_modules → NAME + ALIASES → main
  usage.py        per-applet --help bodies
  common.py       shared helpers · err · user_name · should_overwrite
  applets/        one module per applet · 84 modules
    ls.py         → NAME, ALIASES, HELP, main(argv) -> int
    cat.py
    …
```

**Four-layer flow:** `__main__.py` enters `cli.main(argv)`. `cli.py` checks `argv[0]` basename for multi-call (e.g. `ls -la` when symlinked); otherwise treats `argv[1]` as the applet name. Intercepts `--help` long-form only — `-h` stays free for applet flags like `df -h`. `registry.py` lazy-loads `mainsail.applets.*` once via `pkgutil.iter_modules`, mapping `NAME` and `ALIASES` to `main`. Each applet receives `argv` as a list, returns an exit code (`0` success, `1` runtime error, `2` usage error). Reads stdin via `sys.stdin.buffer` for binary safety; writes via `sys.stdout` / `sys.stdout.buffer`.

Adding an applet means dropping a module into `mainsail/applets/` with the four-symbol contract. Auto-discovery picks it up on next launch — no registration table to edit.

---

[License: MIT](LICENSE) · [Changelog](CHANGELOG.md) · Part of [Real-Fruit-Snacks](https://github.com/Real-Fruit-Snacks) — building offensive security tools, one wave at a time. Sibling ports: [jib](https://github.com/Real-Fruit-Snacks/jib) (Rust) · [topsail](https://github.com/Real-Fruit-Snacks/topsail) (Go) · [staysail](https://github.com/Real-Fruit-Snacks/Staysail) (Zig) · [moonraker](https://github.com/Real-Fruit-Snacks/Moonraker) (Lua) · [rill](https://github.com/Real-Fruit-Snacks/rill) (NASM).
