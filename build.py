"""Build mainsail artifacts.

Usage:
    python build.py                              # Nuitka onefile binary (default)
    python build.py --onefile                    # same as above, explicit
    python build.py --pyz                        # portable Python zipapp (mainsail.pyz)
    python build.py --all                        # both binary and zipapp

Applet selection:
    python build.py --preset slim                # trim archives + hashing
    python build.py --preset minimal             # bare-essentials set
    python build.py --applets ls,cat,grep,awk    # only those applets
    python build.py --pyz --preset slim          # preset applies to pyz too
    python build.py --list-presets               # show preset contents

Static linking (Linux only — meant for Alpine/musl runs in CI):
    python build.py --static                     # pass --static-libpython=yes

The artifact name gains a `-<preset>` suffix for non-full builds
(e.g. `dist/mainsail-slim`, `dist/mainsail-slim.pyz`). When using
--applets directly, the suffix is `-custom`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


# Curated presets. Keep these sets small and meaningful — the savings
# on a Nuitka binary are modest (Python runtime dominates) but the pyz
# can drop substantially.
PRESETS: dict[str, set[str] | None] = {
    "full": None,  # every applet
    "slim": {
        # File ops
        "ls", "cp", "mv", "rm", "mkdir", "touch", "find", "chmod",
        "stat", "ln",
        # Text
        "cat", "grep", "head", "tail", "wc", "sort", "uniq", "cut",
        "tr", "sed", "awk", "tee", "xargs", "printf", "echo",
        # Paths
        "basename", "dirname", "realpath", "pwd", "which",
        # System
        "uname", "hostname", "whoami", "date", "env", "sleep",
        # Control
        "true", "false", "seq",
    },
    "minimal": {
        "ls", "cat", "cp", "mv", "rm", "mkdir", "find", "grep",
        "sed", "awk", "head", "tail", "wc", "echo", "true", "false",
        "env", "pwd",
    },
}


def _resolve_applet_modules(names: set[str]) -> tuple[set[str], list[str]]:
    """Resolve applet NAME and ALIAS inputs to the set of module filenames
    that need to survive the applets/ prune.

    Returns (module_filenames_to_keep, unknown_inputs).
    """
    # Load registry (importing applets is cheap)
    sys.path.insert(0, str(ROOT))
    try:
        from mainsail.registry import _REGISTRY, load_all_applets  # type: ignore
    finally:
        sys.path.pop(0)
    load_all_applets()
    keep: set[str] = set()
    unknown: list[str] = []
    for n in names:
        applet = _REGISTRY.get(n)
        if applet is None:
            unknown.append(n)
            continue
        # applet.main.__module__ is e.g. "mainsail.applets.ls"; the module
        # filename == the canonical NAME for every current applet, but use
        # the actual module path for future-proofness.
        mod_name = applet.main.__module__.rsplit(".", 1)[-1]
        keep.add(mod_name)
    return keep, unknown


def _prune_applets(package_dir: Path, keep_modules: set[str]) -> None:
    """Remove every .py from package_dir/applets/ not in keep_modules.
    __init__.py is always preserved."""
    applets_dir = package_dir / "applets"
    for f in applets_dir.iterdir():
        if f.name == "__init__.py":
            continue
        if f.suffix == ".py" and f.stem not in keep_modules:
            f.unlink()


def _stage_source(keep_modules: set[str] | None) -> tuple[Path, Path, bool]:
    """Return (build_cwd, entry_point_py, is_temp).

    When no applets are filtered we build from the source tree in place.
    When they are filtered we copy the mainsail/ package into a tempdir
    and prune, so Nuitka sees only the surviving applets via pkgutil
    at runtime.
    """
    if keep_modules is None:
        return ROOT, ROOT / "mainsail" / "__main__.py", False
    tmp = Path(tempfile.mkdtemp(prefix="mainsail-build-"))
    shutil.copytree(
        ROOT / "mainsail",
        tmp / "mainsail",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    _prune_applets(tmp / "mainsail", keep_modules)
    return tmp, tmp / "mainsail" / "__main__.py", True


def build_pyz(keep_modules: set[str] | None, suffix: str) -> int:
    """Build a portable zipapp (mainsail.pyz or mainsail-<suffix>.pyz)."""
    DIST.mkdir(exist_ok=True)
    name = f"mainsail{'-' + suffix if suffix else ''}.pyz"
    target = DIST / name
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(
            ROOT / "mainsail",
            tmp_path / "mainsail",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        if keep_modules is not None:
            _prune_applets(tmp_path / "mainsail", keep_modules)
        # Top-level __main__.py: zipapp's own `main=` synthesiser drops
        # the return code, so we write our own shim that sys.exit()s.
        (tmp_path / "__main__.py").write_text(
            "import sys\nfrom mainsail.cli import main\nsys.exit(main())\n",
            encoding="utf-8",
        )
        zipapp.create_archive(
            source=tmp_path,
            target=target,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    size_kb = target.stat().st_size / 1024
    print(f"wrote {target} ({size_kb:.1f} KB)")
    return 0


def build_binary(keep_modules: set[str] | None, suffix: str, *, static: bool = False) -> int:
    if shutil.which("nuitka") is None:
        try:
            import nuitka  # noqa: F401
        except ImportError:
            print("nuitka not installed — run: pip install nuitka", file=sys.stderr)
            return 1

    DIST.mkdir(exist_ok=True)
    # Modules none of our applets import — skipping them trims several
    # megabytes of stdlib from the onefile payload.
    exclude = (
        "tkinter", "turtle", "test", "tests", "idlelib", "ensurepip",
        "venv", "pydoc_data", "distutils", "setuptools", "pip", "wheel",
        "lib2to3",
    )
    output_name = f"mainsail{'-' + suffix if suffix else ''}"
    build_cwd, entry, is_temp = _stage_source(keep_modules)
    try:
        cmd = [
            sys.executable, "-m", "nuitka",
            "--onefile",
            "--standalone",
            # NB: `--remove-output` used to tidy the intermediate .dist dir,
            # but on Windows ARM64 runners Defender file-locks the freshly-
            # written artifacts long enough for Nuitka's 5-retry cleanup to
            # fail FATAL even though the onefile .exe was already produced.
            # Skip auto-cleanup; ephemeral CI VMs don't care, and locals
            # can `rm -rf dist/*.dist` themselves.
            "--assume-yes-for-downloads",
            f"--output-dir={DIST}",
            f"--output-filename={output_name}",
            # Applets are discovered via pkgutil at runtime, so Nuitka has
            # to bundle the whole package explicitly.
            "--include-package=mainsail.applets",
            # Nuitka's onefile bootstrap treats "-c" as a Python interpreter
            # self-call; our applets use -c legitimately (gzip -c, cp -c).
            "--no-deployment-flag=self-execution",
            # Size: strip asserts/docstrings/site from bundled bytecode.
            "--python-flag=no_asserts",
            "--python-flag=no_docstrings",
            "--python-flag=no_site",
            # Size: LTO trims compiled-C code (slower build).
            "--lto=yes",
            *(f"--nofollow-import-to={m}" for m in exclude),
        ]
        if sys.platform == "win32":
            # Windows bundles VC++ runtime DLLs by default; most users
            # already have them. Disabling shaves ~8 MB off the build.
            cmd.append("--include-windows-runtime-dlls=no")
        if static:
            # Ask Nuitka to link Python statically. Requires libpython.a
            # to be available — present on Alpine's python3-dev. On
            # systems where it isn't, Nuitka will refuse and the build
            # fails fast (which is what we want).
            cmd.append("--static-libpython=yes")
        cmd.append(str(entry))
        print(" ".join(cmd))
        rc = subprocess.call(cmd, cwd=build_cwd)
        return rc
    finally:
        if is_temp:
            shutil.rmtree(build_cwd, ignore_errors=True)


def _print_presets() -> int:
    # Discover the real applet count from the registry so the printout
    # stays accurate as we add applets.
    sys.path.insert(0, str(ROOT))
    try:
        from mainsail.registry import _REGISTRY, load_all_applets  # type: ignore
        load_all_applets()
        canonical = {a.name for a in _REGISTRY.values()}
    finally:
        sys.path.pop(0)
    print("Available presets:")
    for name, applets in PRESETS.items():
        if applets is None:
            print(f"  {name}  (all {len(canonical)} applets)")
        else:
            print(f"  {name}  ({len(applets)} applets): {', '.join(sorted(applets))}")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    want_pyz = False
    want_binary = False
    preset: str | None = None
    custom_applets: set[str] | None = None
    explicit_target = False
    static = False

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--pyz":
            want_pyz = True
            explicit_target = True
        elif a == "--onefile":
            want_binary = True
            explicit_target = True
        elif a == "--all":
            want_pyz = True
            want_binary = True
            explicit_target = True
        elif a == "--static":
            static = True
        elif a == "--list-presets":
            return _print_presets()
        elif a == "--preset":
            i += 1
            if i >= len(argv):
                print("--preset needs an argument", file=sys.stderr)
                return 2
            preset = argv[i]
            if preset not in PRESETS:
                print(f"unknown preset: {preset!r}; use --list-presets", file=sys.stderr)
                return 2
        elif a.startswith("--preset="):
            preset = a.split("=", 1)[1]
            if preset not in PRESETS:
                print(f"unknown preset: {preset!r}; use --list-presets", file=sys.stderr)
                return 2
        elif a == "--applets":
            i += 1
            if i >= len(argv):
                print("--applets needs a comma-separated list", file=sys.stderr)
                return 2
            custom_applets = {n.strip() for n in argv[i].split(",") if n.strip()}
        elif a.startswith("--applets="):
            custom_applets = {n.strip() for n in a.split("=", 1)[1].split(",") if n.strip()}
        elif a in {"-h", "--help"}:
            print(__doc__)
            return 0
        else:
            print(f"unknown option: {a!r}", file=sys.stderr)
            return 2
        i += 1

    if preset is not None and custom_applets is not None:
        print("--preset and --applets are mutually exclusive", file=sys.stderr)
        return 2

    # Default target: binary, unless --pyz given
    if not explicit_target:
        want_binary = True

    if custom_applets is not None:
        keep_modules, unknown = _resolve_applet_modules(custom_applets)
        if unknown:
            print(f"unknown applet(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        suffix = "custom"
    elif preset is not None:
        preset_set = PRESETS[preset]
        if preset_set is None:
            keep_modules = None
            suffix = ""
        else:
            keep_modules, unknown = _resolve_applet_modules(preset_set)
            if unknown:
                # shouldn't happen for our own presets — catch typos early
                print(
                    f"preset {preset!r} references unknown applet(s): {', '.join(unknown)}",
                    file=sys.stderr,
                )
                return 2
            suffix = preset
    else:
        keep_modules = None
        suffix = ""

    # Static is a Linux-binary-only concept (Windows DLLs / macOS libs are
    # always present on those systems); ignore it for the pyz path.
    if want_pyz:
        rc = build_pyz(keep_modules, suffix)
        if rc != 0:
            return rc
    if want_binary:
        rc = build_binary(keep_modules, suffix, static=static)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
