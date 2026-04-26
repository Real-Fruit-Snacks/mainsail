"""mainsail timeout — run a command with a time limit."""
from __future__ import annotations

import signal
import subprocess
import sys
import time

from mainsail.common import err

NAME = "timeout"
ALIASES: list[str] = []
HELP = "run a command with a time limit"


_SIG_NAMES = {
    "TERM": "SIGTERM", "KILL": "SIGKILL", "INT": "SIGINT", "HUP": "SIGHUP",
    "QUIT": "SIGQUIT", "USR1": "SIGUSR1", "USR2": "SIGUSR2",
}


def _parse_duration(s: str) -> float | None:
    if not s:
        return None
    mult = 1.0
    last = s[-1].lower()
    if last == "s": s = s[:-1]
    elif last == "m": mult = 60.0; s = s[:-1]
    elif last == "h": mult = 3600.0; s = s[:-1]
    elif last == "d": mult = 86400.0; s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _resolve_signal(name: str) -> int | None:
    n = name.upper()
    if n.startswith("SIG"):
        n = n[3:]
    full = _SIG_NAMES.get(n, "SIG" + n)
    sig = getattr(signal, full, None)
    if sig is None:
        try:
            return int(name)
        except ValueError:
            return None
    return int(sig)


def main(argv: list[str]) -> int:
    args = argv[1:]
    sig = signal.SIGTERM if hasattr(signal, "SIGTERM") else 15
    kill_after: float | None = None
    preserve_status = False
    foreground = False
    verbose = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-s", "--signal"} and i + 1 < len(args):
            s = _resolve_signal(args[i + 1])
            if s is None:
                err(NAME, f"unknown signal: {args[i + 1]}")
                return 125
            sig = s
            i += 2; continue
        if a.startswith("--signal="):
            s = _resolve_signal(a.split("=", 1)[1])
            if s is None:
                err(NAME, f"unknown signal")
                return 125
            sig = s
            i += 1; continue
        if a in {"-k", "--kill-after"} and i + 1 < len(args):
            kill_after = _parse_duration(args[i + 1])
            if kill_after is None:
                err(NAME, f"invalid kill-after: {args[i + 1]}")
                return 125
            i += 2; continue
        if a == "--preserve-status":
            preserve_status = True
            i += 1; continue
        if a == "--foreground":
            foreground = True
            i += 1; continue
        if a in {"-v", "--verbose"}:
            verbose = True
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1 and not a[1:].replace(".", "").isdigit():
            err(NAME, f"unknown option: {a}")
            return 125
        break

    rest = args[i:]
    if len(rest) < 2:
        err(NAME, "usage: timeout DURATION COMMAND [ARG]...")
        return 125

    duration = _parse_duration(rest[0])
    if duration is None:
        err(NAME, f"invalid duration: {rest[0]}")
        return 125

    cmd = rest[1:]

    try:
        proc = subprocess.Popen(cmd)
    except (OSError, FileNotFoundError) as e:
        err(NAME, f"{cmd[0]}: {e.strerror or e}")
        return 127

    deadline = time.monotonic() + duration
    while True:
        rc = proc.poll()
        if rc is not None:
            if preserve_status and rc != 0:
                return rc
            return rc if rc >= 0 else 128 + (-rc)
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)

    if verbose:
        err(NAME, f"sending signal {sig} to PID {proc.pid}")
    try:
        proc.send_signal(sig)
    except OSError as e:
        err(NAME, f"send_signal: {e}")
        return 125

    timed_out = True
    grace_deadline = time.monotonic() + (kill_after if kill_after is not None else 5.0)
    while True:
        rc = proc.poll()
        if rc is not None:
            break
        if time.monotonic() >= grace_deadline:
            if kill_after is not None:
                if verbose:
                    err(NAME, f"sending SIGKILL to PID {proc.pid}")
                try:
                    proc.kill()
                except OSError:
                    pass
                proc.wait()
            else:
                proc.wait()
            break
        time.sleep(0.05)

    if preserve_status:
        rc = proc.returncode
        return rc if rc >= 0 else 128 + (-rc)
    return 124  # POSIX-spec exit on timeout
