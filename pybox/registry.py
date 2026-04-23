from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable

import pybox.applets as _applets_pkg

_REGISTRY: dict[str, "Applet"] = {}
_LOADED = False


@dataclass(frozen=True)
class Applet:
    name: str
    help: str
    main: Callable[[list[str]], int]
    aliases: tuple[str, ...] = ()


def register(applet: Applet) -> None:
    _REGISTRY[applet.name] = applet
    for a in applet.aliases:
        _REGISTRY[a] = applet


def get_applet(name: str) -> Applet | None:
    return _REGISTRY.get(name)


def list_applets() -> list[str]:
    primary = {a.name: a for a in _REGISTRY.values()}
    return sorted(primary)


def list_applets_with_help() -> list[tuple[str, str, tuple[str, ...]]]:
    seen: dict[str, Applet] = {}
    for a in _REGISTRY.values():
        seen[a.name] = a
    return sorted(
        ((a.name, a.help, a.aliases) for a in seen.values()),
        key=lambda t: t[0],
    )


def load_all_applets() -> None:
    global _LOADED
    if _LOADED:
        return
    for _, modname, _ in pkgutil.iter_modules(_applets_pkg.__path__):
        mod = importlib.import_module(f"pybox.applets.{modname}")
        name = getattr(mod, "NAME", None)
        entry = getattr(mod, "main", None)
        if name is None or entry is None:
            continue
        aliases = tuple(getattr(mod, "ALIASES", ()) or ())
        help_ = getattr(mod, "HELP", "")
        register(Applet(name=name, help=help_, main=entry, aliases=aliases))
    _LOADED = True
