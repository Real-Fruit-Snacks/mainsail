"""mainsail install-aliases — bulk-create per-applet symlinks.

After running this, the user can type `ls`, `cat`, `grep` etc. and
mainsail's multi-call dispatch handles the request — no need to type
`mainsail` every time.

  mainsail install-aliases                         # default ~/.local/bin
  mainsail install-aliases ~/bin                   # custom dir
  mainsail install-aliases --aliases ~/.local/bin  # also link ALIASES
  mainsail install-aliases --dry-run               # preview
  mainsail install-aliases --force                 # overwrite existing

Lifecycle applets (`completions`, `update`, `install-aliases`) are
skipped by default — typing `update` to mean "self-update mainsail"
isn't obvious. Use `--all` to include them.

On POSIX we prefer symlinks; on Windows we fall back to hardlinks
(symlinks need admin or developer-mode), then to a binary copy as a
last resort.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from mainsail.common import err

NAME = "install-aliases"
ALIASES: list[str] = []
HELP = "create per-applet symlinks (so `ls` runs mainsail's ls)"


_LIFECYCLE_APPLETS = {"completions", "update", "install-aliases"}


def _running_binary_path() -> Path | None:
    arg0 = sys.argv[0] if sys.argv else ""
    if not arg0:
        return None
    p = Path(arg0).resolve()
    if not p.exists():
        return None
    name = p.name.lower()
    if name in {"__main__.py", "cli.py"}:
        return None
    return p


def _default_target() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(local) / "mainsail" / "bin"
    return Path.home() / ".local" / "bin"


def _link(source: Path, target: Path) -> tuple[str, str | None]:
    """Create target -> source. Try symlink first, fall back to hardlink,
    then copy. Returns (method, error). method is "symlink" / "hardlink"
    / "copy" / "skip" / "fail"."""
    try:
        os.symlink(source, target)
        return "symlink", None
    except (OSError, NotImplementedError) as e:
        sym_err = str(e)
    try:
        os.link(source, target)
        return "hardlink", None
    except OSError as e:
        link_err = str(e)
    try:
        shutil.copy2(source, target)
        return "copy", None
    except OSError as e:
        return "fail", f"symlink: {sym_err}; hardlink: {link_err}; copy: {e}"


def main(argv: list[str]) -> int:
    args = argv[1:]
    target_dir: Path | None = None
    include_aliases = False
    include_all = False
    dry_run = False
    force = False
    quiet = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a == "--aliases":
            include_aliases = True
            i += 1; continue
        if a == "--all":
            include_all = True
            i += 1; continue
        if a in {"-n", "--dry-run", "--check"}:
            dry_run = True
            i += 1; continue
        if a in {"-f", "--force"}:
            force = True
            i += 1; continue
        if a in {"-q", "--quiet"}:
            quiet = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        if target_dir is not None:
            err(NAME, "too many arguments")
            return 2
        target_dir = Path(a).expanduser().resolve()
        i += 1

    if target_dir is None:
        target_dir = _default_target()

    self_path = _running_binary_path()
    if self_path is None:
        err(NAME, "install-aliases needs a single-file binary; "
                  "this looks like a `python -m mainsail` invocation. "
                  "Run from a frozen binary or the portable .pyz.")
        return 2

    # Collect applet names
    from mainsail.registry import _REGISTRY, load_all_applets
    load_all_applets()
    canonical: dict[str, tuple[str, ...]] = {}
    for applet in _REGISTRY.values():
        # _REGISTRY maps both name and alias to the same Applet, dedup here
        canonical.setdefault(applet.name, applet.aliases)

    names_to_link: list[str] = []
    for name, aliases in sorted(canonical.items()):
        if name == NAME:
            continue
        if not include_all and name in _LIFECYCLE_APPLETS:
            continue
        names_to_link.append(name)
        if include_aliases:
            names_to_link.extend(aliases)

    # Sanity check: ensure target dir exists (or create)
    if not dry_run:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            err(NAME, f"cannot create {target_dir}: {e.strerror or e}")
            return 1

    if not quiet:
        sys.stdout.write(f"source: {self_path}\n")
        sys.stdout.write(f"target: {target_dir}\n")
        if dry_run:
            sys.stdout.write("(dry-run; no files created)\n")
        sys.stdout.write("\n")

    # On Windows, symlinks need .exe suffix to actually launch
    suffix = ".exe" if sys.platform == "win32" and self_path.suffix.lower() == ".exe" else ""

    skipped = 0
    created = 0
    failed = 0
    method_count: dict[str, int] = {}

    for name in names_to_link:
        link_path = target_dir / f"{name}{suffix}"
        if link_path.exists() or link_path.is_symlink():
            if not force:
                if not quiet:
                    sys.stdout.write(f"skip   {name:<14}  (exists; pass --force to overwrite)\n")
                skipped += 1
                continue
            if not dry_run:
                try:
                    link_path.unlink()
                except OSError as e:
                    err(NAME, f"{link_path}: cannot remove existing: {e.strerror or e}")
                    failed += 1
                    continue
        if dry_run:
            if not quiet:
                sys.stdout.write(f"would  {name:<14}  -> {link_path}\n")
            created += 1
            continue
        method, error = _link(self_path, link_path)
        if method == "fail":
            err(NAME, f"{link_path}: {error}")
            failed += 1
            continue
        method_count[method] = method_count.get(method, 0) + 1
        created += 1
        if not quiet:
            sys.stdout.write(f"{method:<8} {name:<14}  -> {link_path}\n")

    if not quiet:
        sys.stdout.write("\n")
        if dry_run:
            sys.stdout.write(f"would create {created}, skip {skipped}\n")
        else:
            parts = [f"{k}={v}" for k, v in sorted(method_count.items())]
            sys.stdout.write(
                f"created {created} ({', '.join(parts) or '0'}), "
                f"skipped {skipped}, failed {failed}\n"
            )
        if created and not dry_run:
            sys.stdout.write(
                f"\nMake sure {target_dir} is on your PATH:\n"
                f"  echo 'export PATH=\"{target_dir}:$PATH\"' >> ~/.bashrc\n"
            )

    return 0 if failed == 0 else 1
