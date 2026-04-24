# Changelog

All notable changes to mainsail will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Real-Fruit-Snacks/mainsail/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Real-Fruit-Snacks/mainsail/releases/tag/v0.1.0
