# Changelog

All notable changes to mainsail will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.10] - 2026-04-24

### Added
- Fully-static Linux binaries (best-effort): `mainsail-linux-x64-static`
  and `mainsail-linux-arm64-static`, built inside Alpine 3.19, linked
  against musl, with `--static-libpython=yes`. The release-workflow
  step verifies that `ldd` reports no shared-library dependencies and
  fails the build otherwise — anything that ships is genuinely static.
  Runs on distroless containers, embedded systems, exotic distros,
  anywhere a kernel is present.
- `python build.py --static` flag (passes `--static-libpython=yes` to
  Nuitka). Linux + Alpine only — Windows/macOS already get system libs
  for free.

### Notes
- The static job uses `continue-on-error: true` so a flaky musl/static
  toolchain interaction can't block the dynamic glibc release. If a
  given release tag lacks `-static` artifacts, the static build hit a
  snag for that toolchain combo — fall back to the dynamic glibc
  binary or the `mainsail.pyz` zipapp.

## [0.1.9] - 2026-04-24

### Added
- Custom applet subsets in `build.py`:
  - `--preset slim` — 39 applets (drops archives + hashing + disk stats)
  - `--preset minimal` — 18 applets (scripting essentials)
  - `--applets ls,cat,grep,awk` — hand-picked set
  - `--list-presets` — enumerate preset contents
  Non-full builds land as `dist/mainsail-<suffix>` with matching
  `.exe`/`.pyz` extensions. Release workflow now ships **ten native
  binaries** (5 full + 5 slim) and **two zipapps** (`mainsail.pyz` and
  `mainsail-slim.pyz`).

### Notes
- Nuitka binary savings from trimming applets are modest (~3 %) since
  the Python runtime dominates the onefile payload. Zipapp savings are
  meaningful: minimal drops ~44 % (80 KB → 45 KB).

## [0.1.8] - 2026-04-24

### Added
- `awk` applet — a practical POSIX-awk subset built on stdlib only.
  Covers BEGIN/END, /regex/ and expression patterns, range patterns,
  `print`/`printf` with full format specifiers, control flow
  (if/else, while, do/while, for, for-in), associative arrays,
  `delete`, `in`, field manipulation, NR/NF/FS/OFS/ORS/RS/FILENAME,
  `length`/`substr`/`index`/`split`/`sub`/`gsub`/`match`/
  `toupper`/`tolower`/`sprintf`/`int`, and `system`.
  Not implemented: user-defined functions, getline, strnum semantics
  for string-literal comparisons (documented limitation).
  42 new test cases bring the suite to **268 passing**.

### Fixed
- Linux x64 binary now builds on `ubuntu-22.04` (glibc 2.35) instead
  of `ubuntu-latest` (24.04, glibc 2.39). This lowers the runtime
  glibc floor so the binary runs on Ubuntu 22.04 LTS, Debian 12, RHEL 9,
  and WSL defaults — previous v0.1.7 binary required GLIBC 2.38 and
  refused to start on anything older.

## [0.1.7] - 2026-04-23

### Removed
- `mainsail-macos-x64` (Intel Mac) pre-built binary. GitHub's free-tier
  `macos-13` runner queue is effectively unavailable to this project
  (30+ minute queue times across v0.1.4–v0.1.6, never dispatched), so
  the matrix entry was dropped. Apple stopped shipping Intel Macs in
  2023 — the ARM64 binary covers the supported lineup, and Intel Mac
  users can run the portable `mainsail.pyz` (same feature set, needs
  Python 3.8+) or `pip install -e .` from source.

### Fixed
- v0.1.7 is the first release since v0.1.3 to actually produce a
  GitHub Release; v0.1.4 through v0.1.6 were tagged but blocked on the
  Windows-ARM64 Python 3.10 unavailability (v0.1.4), a Defender
  file-lock race during Nuitka's `--remove-output` cleanup (v0.1.5),
  and the `macos-13` queue issue above (v0.1.6). The relevant fixes
  are included here.

## [0.1.6] - 2026-04-23

### Fixed
- Windows ARM64 Nuitka build failed during cleanup of the intermediate
  `.dist` directory — Defender file-locked the freshly-written artifacts
  just long enough for Nuitka's 5-retry cleanup to return FATAL, even
  though the onefile `.exe` was already produced. Dropped
  `--remove-output` from `build.py`; ephemeral CI VMs don't care about
  leftover intermediates, and locals can clean with
  `rm -rf dist/*.dist dist/*.build` if they want a tidy tree.

## [0.1.5] - 2026-04-23

### Added
- Portable `mainsail.pyz` zipapp (~66 KB) built with `python build.py --pyz`.
  Runs on any host with Python 3.8+ — intended for ESXi, exotic
  architectures, and restrictive environments where a native binary
  isn't viable.
- Zipapp smoke test in the release workflow (`--version`, `--list`,
  stdout round-trip, exit codes).
- `Portable zipapp (mainsail.pyz)` as a runtime option in the bug
  report template.

### Fixed
- Windows ARM64 release build: `actions/setup-python@v5` has no
  Python 3.10 arm64 build for Windows Enterprise, so the matrix entry
  now uses python-build-standalone via `astral-sh/setup-uv@v6`
  (same source as Linux).

### Changed
- `mainsail.__version__` and `pyproject.toml` bumped to `0.1.5`
  (previously pinned at `0.1.0` across releases).

## [0.1.4] - 2026-04-23

### Added
- Linux ARM64 binary (`mainsail-linux-arm64`) built on `ubuntu-24.04-arm`
- macOS Intel binary (`mainsail-macos-x64`) built on `macos-13`
- Windows ARM64 binary (`mainsail-windows-arm64`) built on `windows-11-arm`

Release now ships six native binaries covering x86_64 and ARM64 for all
three major desktop/server platforms.

## [0.1.0] - 2026-04-23

Initial release.

### Added
- 50 POSIX applets across file ops, text processing, hashing, archives,
  filesystem stats, path helpers, system info, and control flow:
  `basename`, `cat`, `chmod`, `cp`, `cut`, `date`, `df`, `dirname`,
  `du`, `echo`, `env`, `false`, `find`, `grep`, `gunzip`, `gzip`,
  `head`, `hostname`, `ln`, `ls`, `md5sum`, `mkdir`, `mv`, `printf`,
  `pwd`, `realpath`, `rm`, `sed`, `seq`, `sha1sum`, `sha256sum`,
  `sha512sum`, `sleep`, `sort`, `stat`, `tail`, `tar`, `tee`, `touch`,
  `tr`, `true`, `uname`, `uniq`, `unzip`, `wc`, `which`, `whoami`,
  `xargs`, `yes`, `zip`
- Windows-native aliases: `dir`, `type`, `copy`, `del`, `erase`, `md`,
  `move`, `ren`, `rename`, `where`
- Applet registry with auto-discovery via `pkgutil.iter_modules`
- Multi-call dispatch: `mainsail ls` or symlinked/hardlinked `ls`
- `find` expression tree with `-exec`, `-prune`, `-delete`, boolean
  operators, parens, size/time/path predicates
- `sed` subset: `s///`, `d`, `p`, `q`, `=`, `y///`, addresses, ranges,
  negation, `-i` in-place edit, BRE + ERE
- `sort` with `-k` key fields, `-t` custom separator, `-o` output file
- `grep` context (`-A`/`-B`/`-C`), `-o` only-matching, `-w` word,
  `-q` quiet
- `tail -f` follow mode with truncation + rotation detection
- `tar` create/extract/list with gzip/bzip2/xz filters; accepts
  traditional (`cvfz`) and dashed (`-cvfz`) bundled flag forms
- Per-applet `--help` via centralized `usage.py`
- 226 pytest-based unit tests, cross-platform stable
- 23-case stress harness (`scripts/stress.py`) covering large inputs,
  Unicode, binary-safe streams, deep trees, pipelines, round-trips,
  and edge cases
- Nuitka-based `build.py` producing a standalone onefile binary with
  zstandard compression (~7 MB on Windows, ~5.5 MB on Linux)
- GitHub Actions CI matrix: Linux / macOS / Windows × Python 3.10–3.13
- Release workflow that builds and publishes binaries on tag push

[Unreleased]: https://github.com/Real-Fruit-Snacks/mainsail/compare/v0.1.10...HEAD
[0.1.10]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.10
[0.1.9]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.9
[0.1.8]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.8
[0.1.7]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.7
[0.1.6]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.6
[0.1.5]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.5
[0.1.4]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.4
[0.1.0]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.0
