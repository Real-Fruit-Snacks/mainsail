"""mainsail watch — periodically re-run a command and redraw output."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from datetime import datetime

from mainsail.common import err

NAME = "watch"
ALIASES: list[str] = []
HELP = "execute a command periodically, showing output"


def _clear_screen() -> None:
    # ANSI clear; works on most terminals on all three OSes.
    sys.stdout.write("\x1b[2J\x1b[H")


def main(argv: list[str]) -> int:
    args = argv[1:]
    interval = 2.0
    no_title = False
    exec_via_shell = True
    exit_on_change = False
    beep_on_change = False
    precise = False  # honor --interval drift compensation

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-n", "--interval"} and i + 1 < len(args):
            try:
                interval = float(args[i + 1])
            except ValueError:
                err(NAME, f"invalid interval: {args[i + 1]}")
                return 2
            if interval < 0.1:
                interval = 0.1
            i += 2; continue
        if a.startswith("-n") and len(a) > 2:
            try:
                interval = float(a[2:])
            except ValueError:
                err(NAME, f"invalid interval: {a[2:]}")
                return 2
            i += 1; continue
        if a in {"-t", "--no-title"}:
            no_title = True
            i += 1; continue
        if a in {"-x", "--exec"}:
            exec_via_shell = False
            i += 1; continue
        if a in {"-g", "--chgexit"}:
            exit_on_change = True
            i += 1; continue
        if a in {"-b", "--beep"}:
            beep_on_change = True
            i += 1; continue
        if a in {"-p", "--precise"}:
            precise = True
            i += 1; continue
        if a == "--":
            i += 1
            break
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    cmd = args[i:]
    if not cmd:
        err(NAME, "no command given")
        return 2

    cmd_display = " ".join(shlex.quote(c) for c in cmd)
    last_output: str | None = None

    try:
        while True:
            cycle_start = time.monotonic()
            now = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            try:
                if exec_via_shell:
                    proc = subprocess.run(
                        cmd if len(cmd) > 1 else cmd[0],
                        shell=len(cmd) == 1,
                        capture_output=True,
                        text=True,
                    )
                else:
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                output = proc.stdout + proc.stderr
            except (OSError, subprocess.SubprocessError) as e:
                output = f"watch: command failed: {e}\n"

            _clear_screen()
            if not no_title:
                left = f"Every {interval:g}s: {cmd_display}"
                right = now
                # Right-align the timestamp; cap left if it'd overflow.
                try:
                    cols = os.get_terminal_size().columns
                except OSError:
                    cols = 80
                gap = max(1, cols - len(left) - len(right))
                if len(left) + gap + len(right) > cols:
                    left = left[:cols - len(right) - 4] + "..."
                    gap = max(1, cols - len(left) - len(right))
                sys.stdout.write(f"{left}{' ' * gap}{right}\n\n")
            sys.stdout.write(output)
            sys.stdout.flush()

            if exit_on_change and last_output is not None and last_output != output:
                if beep_on_change:
                    sys.stdout.write("\x07")
                    sys.stdout.flush()
                return 0
            if beep_on_change and last_output is not None and last_output != output:
                sys.stdout.write("\x07")
                sys.stdout.flush()
            last_output = output

            elapsed = time.monotonic() - cycle_start
            sleep = interval - (elapsed if precise else 0)
            if sleep > 0:
                try:
                    time.sleep(sleep)
                except KeyboardInterrupt:
                    return 0
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return 0
