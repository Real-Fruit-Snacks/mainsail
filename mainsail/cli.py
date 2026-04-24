from __future__ import annotations

import sys
from pathlib import Path

from mainsail import __version__
from mainsail.registry import Applet, get_applet, list_applets_with_help, load_all_applets
from mainsail.usage import USAGE


def _program_stem(argv0: str) -> str:
    return Path(argv0).stem.lower()


def _print_top_help() -> None:
    print(f"mainsail {__version__} - cross-platform multi-call utility binary")
    print()
    print("Usage:")
    print("  mainsail <applet> [args...]")
    print("  mainsail <applet> --help       show help for <applet>")
    print("  <applet> [args...]          (when installed as hardlink/symlink)")
    print()
    print("Top-level options:")
    print("  --list           list available applets")
    print("  --help, -h       show this help")
    print("  --version        show version")


def _print_applet_help(applet: Applet) -> None:
    print(f"{applet.name} - {applet.help}")
    body = USAGE.get(applet.name)
    if body:
        print()
        print(body.rstrip("\n"))
    if applet.aliases:
        print()
        print(f"Aliases: {', '.join(applet.aliases)}")


def _print_list() -> None:
    rows = list_applets_with_help()
    if not rows:
        return
    width = max(len(name) for name, _, _ in rows)
    for name, help_, aliases in rows:
        suffix = f"  (aliases: {', '.join(aliases)})" if aliases else ""
        print(f"  {name.ljust(width)}  {help_}{suffix}")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    load_all_applets()

    stem = _program_stem(argv[0]) if argv else "mainsail"

    # Multi-call mode: argv[0] basename matches a known applet
    applet = get_applet(stem)
    if applet is not None and stem != "mainsail":
        # Intercept --help only; -h is overloaded by many applets (df/du/sort)
        if len(argv) >= 2 and argv[1] == "--help":
            _print_applet_help(applet)
            return 0
        return applet.main([stem, *argv[1:]])

    # Wrapper mode: mainsail <applet> [args...]
    if len(argv) < 2:
        _print_top_help()
        return 0

    first = argv[1]
    if first in ("--help", "-h"):
        # "mainsail --help <applet>" prints that applet's help
        if len(argv) >= 3:
            applet = get_applet(argv[2])
            if applet is not None:
                _print_applet_help(applet)
                return 0
        _print_top_help()
        return 0
    if first == "--version":
        print(f"mainsail {__version__}")
        return 0
    if first == "--list":
        _print_list()
        return 0

    applet = get_applet(first)
    if applet is None:
        print(f"mainsail: unknown applet '{first}'", file=sys.stderr)
        print("try 'mainsail --list' to see all applets", file=sys.stderr)
        return 1
    if len(argv) >= 3 and argv[2] == "--help":
        _print_applet_help(applet)
        return 0
    return applet.main([first, *argv[2:]])
