"""mainsail http — minimal curl-style HTTP client.

Usage:
    mainsail http URL                       # GET
    mainsail http -X POST -d @body.json URL
    mainsail http -H "Authorization: Bearer TOKEN" URL
    mainsail http -i URL                    # include response headers
    mainsail http -I URL                    # HEAD-only
    mainsail http -o file.bin URL           # write body to file
    mainsail http --json '{"a":1}' URL      # POST JSON
"""
from __future__ import annotations

import json as _json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from mainsail.common import err

NAME = "http"
ALIASES: list[str] = []
HELP = "minimal HTTP client (curl-equivalent)"


def main(argv: list[str]) -> int:
    args = argv[1:]
    method: str | None = None
    headers: list[tuple[str, str]] = []
    body: bytes | None = None
    json_body: object = None
    output: str | None = None
    include_headers = False
    head_only = False
    follow_redirects = True
    silent = False
    fail_on_error = False
    user_agent = "mainsail-http/1.0"
    timeout = 30.0
    url: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            args = args[:i] + args[i + 1:]
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-X", "--request"} and i + 1 < len(args):
            method = args[i + 1].upper()
            i += 2
            continue
        if a in {"-H", "--header"} and i + 1 < len(args):
            h = args[i + 1]
            if ":" in h:
                k, v = h.split(":", 1)
                headers.append((k.strip(), v.strip()))
            i += 2
            continue
        if a in {"-d", "--data"} and i + 1 < len(args):
            v = args[i + 1]
            if v.startswith("@"):
                p = v[1:]
                try:
                    body = Path(p).read_bytes()
                except OSError as e:
                    err(NAME, f"{p}: {e.strerror or e}")
                    return 1
            else:
                body = v.encode("utf-8")
            i += 2
            continue
        if a == "--json" and i + 1 < len(args):
            v = args[i + 1]
            if v.startswith("@"):
                try:
                    raw = Path(v[1:]).read_text(encoding="utf-8")
                except OSError as e:
                    err(NAME, f"{v[1:]}: {e.strerror or e}")
                    return 1
                try:
                    json_body = _json.loads(raw)
                except _json.JSONDecodeError as e:
                    err(NAME, f"invalid JSON: {e}")
                    return 1
            else:
                try:
                    json_body = _json.loads(v)
                except _json.JSONDecodeError as e:
                    err(NAME, f"invalid JSON: {e}")
                    return 1
            i += 2
            continue
        if a in {"-o", "--output"} and i + 1 < len(args):
            output = args[i + 1]
            i += 2
            continue
        if a in {"-i", "--include"}:
            include_headers = True
            i += 1
            continue
        if a in {"-I", "--head"}:
            head_only = True
            i += 1
            continue
        if a in {"-L", "--location"}:
            follow_redirects = True
            i += 1
            continue
        if a == "--no-location":
            follow_redirects = False
            i += 1
            continue
        if a in {"-s", "--silent"}:
            silent = True
            i += 1
            continue
        if a in {"-f", "--fail"}:
            fail_on_error = True
            i += 1
            continue
        if a in {"-A", "--user-agent"} and i + 1 < len(args):
            user_agent = args[i + 1]
            i += 2
            continue
        if a == "--timeout" and i + 1 < len(args):
            try:
                timeout = float(args[i + 1])
            except ValueError:
                err(NAME, f"invalid timeout: {args[i + 1]}")
                return 2
            i += 2
            continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        if url is None:
            url = a
            i += 1
            continue
        err(NAME, f"unexpected argument: {a}")
        return 2

    if url is None:
        err(NAME, "missing URL")
        return 2

    # Resolve method
    if head_only:
        method = "HEAD"
    if json_body is not None and body is None:
        body = _json.dumps(json_body).encode("utf-8")
        if not any(k.lower() == "content-type" for k, _ in headers):
            headers.append(("Content-Type", "application/json"))
    if method is None:
        method = "POST" if body is not None else "GET"

    # Build request
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", user_agent)
    for k, v in headers:
        req.add_header(k, v)

    try:
        if not follow_redirects:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *_args, **_kwargs):
                    return None
            opener = urllib.request.build_opener(NoRedirect)
            resp = opener.open(req, timeout=timeout)
        else:
            resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        if fail_on_error:
            if not silent:
                err(NAME, f"HTTP {e.code} {e.reason}")
            return 22
        resp = e
    except urllib.error.URLError as e:
        if not silent:
            err(NAME, f"{e.reason}")
        return 6
    except OSError as e:
        if not silent:
            err(NAME, str(e))
        return 1

    status = getattr(resp, "status", None) or getattr(resp, "code", 0)
    headers_out = resp.headers

    out_stream = sys.stdout.buffer
    close_out = False
    if output is not None:
        try:
            out_stream = open(output, "wb")
            close_out = True
        except OSError as e:
            err(NAME, f"{output}: {e.strerror or e}")
            return 1

    try:
        if include_headers or head_only:
            line = f"HTTP/1.1 {status} {getattr(resp, 'reason', '')}\r\n".encode("ascii", "replace")
            sys.stdout.buffer.write(line)
            for k, v in headers_out.items():
                sys.stdout.buffer.write(f"{k}: {v}\r\n".encode("ascii", "replace"))
            sys.stdout.buffer.write(b"\r\n")
            sys.stdout.flush()
        if not head_only:
            try:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out_stream.write(chunk)
            except OSError as e:
                err(NAME, str(e))
                return 1
            out_stream.flush()
    finally:
        if close_out:
            out_stream.close()
        try:
            resp.close()
        except Exception:
            pass

    if fail_on_error and status >= 400:
        return 22
    return 0
