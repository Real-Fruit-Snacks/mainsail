from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def invoke():
    """Return a callable that invokes pybox.cli.main with the given argv.

    Returns (return_code, stdout_text, stderr_text).
    """
    from pybox.cli import main

    def _invoke(*args: str) -> tuple[int, str, str]:
        import io

        stdout_buf = io.BytesIO()
        stderr_buf = io.StringIO()
        old_out, old_err = sys.stdout, sys.stderr

        class _Stdout:
            def __init__(self, buf): self.buffer = buf
            def write(self, s): self.buffer.write(s.encode("utf-8") if isinstance(s, str) else s)
            def flush(self): pass
            def isatty(self): return False
        try:
            sys.stdout = _Stdout(stdout_buf)
            sys.stderr = stderr_buf
            rc = main(["pybox", *args])
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        out = stdout_buf.getvalue().decode("utf-8", errors="replace")
        err = stderr_buf.getvalue()
        # Normalize CRLF so tests are platform-agnostic. Our applets do
        # byte-preserving I/O, so CRLF survives when Python text-mode writes
        # a fixture file on Windows. Tests assert on logical content.
        out = out.replace("\r\n", "\n")
        return rc, out, err

    return _invoke
