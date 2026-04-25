"""mainsail nc — minimal TCP netcat.

Usage:
    nc HOST PORT                # client: connect, pipe stdin <-> socket
    nc -l -p PORT               # listen on PORT, accept first connection
    nc -z HOST PORT[-PORT2]     # port scan; print open ports

Limitations:
    - TCP only (no UDP).
    - Listen accepts a single connection then exits.
"""
from __future__ import annotations

import socket
import sys
import threading

from mainsail.common import err

NAME = "nc"
ALIASES: list[str] = []
HELP = "TCP netcat — connect, listen, port-scan"


def _pump(src, dst, *, close_dst: bool = False) -> None:
    try:
        while True:
            chunk = src.read(65536) if hasattr(src, "read") else src.recv(65536)
            if not chunk:
                break
            if hasattr(dst, "send"):
                dst.send(chunk if isinstance(chunk, (bytes, bytearray)) else chunk.encode("utf-8"))
            else:
                dst.write(chunk if isinstance(chunk, (bytes, bytearray)) else chunk.encode("utf-8"))
                dst.flush()
    except (OSError, ValueError):
        pass
    finally:
        if close_dst:
            try:
                if hasattr(dst, "shutdown"):
                    dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass


def _bidirectional(sock: socket.socket, timeout: float | None) -> None:
    if timeout:
        sock.settimeout(timeout)
    stop = threading.Event()

    def sock_to_stdout() -> None:
        try:
            while not stop.is_set():
                data = sock.recv(65536)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
        except (OSError, ValueError):
            pass
        finally:
            stop.set()

    def stdin_to_sock() -> None:
        try:
            while not stop.is_set():
                data = sys.stdin.buffer.read(65536)
                if not data:
                    break
                sock.sendall(data)
        except (OSError, ValueError):
            pass
        finally:
            try:
                sock.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    t_out = threading.Thread(target=sock_to_stdout, daemon=True)
    t_in = threading.Thread(target=stdin_to_sock, daemon=True)
    t_out.start()
    t_in.start()
    # Wait for the receiving thread; once the peer closes, we're done.
    t_out.join()
    stop.set()


def _parse_ports(spec: str) -> list[int] | None:
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        try:
            return list(range(int(lo), int(hi) + 1))
        except ValueError:
            return None
    try:
        return [int(spec)]
    except ValueError:
        return None


def main(argv: list[str]) -> int:
    args = argv[1:]
    listen = False
    port: int | None = None
    zero_io = False  # -z: don't send/recv, just check connectivity
    verbose = False
    timeout: float | None = None
    udp = False
    family = socket.AF_INET

    i = 0
    positional: list[str] = []
    while i < len(args):
        a = args[i]
        if a == "--":
            i += 1
            positional.extend(args[i:])
            break
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a == "-l":
            listen = True
            i += 1; continue
        if a == "-p" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid port: {args[i + 1]}")
                return 2
            i += 2; continue
        if a == "-z":
            zero_io = True
            i += 1; continue
        if a == "-v":
            verbose = True
            i += 1; continue
        if a == "-w" and i + 1 < len(args):
            try:
                timeout = float(args[i + 1])
            except ValueError:
                err(NAME, f"invalid timeout: {args[i + 1]}")
                return 2
            i += 2; continue
        if a == "-u":
            udp = True
            i += 1; continue
        if a == "-4":
            family = socket.AF_INET
            i += 1; continue
        if a == "-6":
            family = socket.AF_INET6
            i += 1; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        positional.append(a)
        i += 1

    if udp:
        err(NAME, "UDP mode (-u) is not supported in this build")
        return 2

    sock_type = socket.SOCK_STREAM

    if listen:
        # Listen mode. -p PORT or first positional as port.
        listen_port = port
        if listen_port is None and positional:
            try:
                listen_port = int(positional[-1])
            except ValueError:
                err(NAME, f"invalid port: {positional[-1]}")
                return 2
        if listen_port is None:
            err(NAME, "listen mode requires a port")
            return 2

        srv = socket.socket(family, sock_type)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("", listen_port))
            srv.listen(1)
            if verbose:
                sys.stderr.write(f"listening on port {listen_port}\n")
            conn, addr = srv.accept()
            if verbose:
                sys.stderr.write(f"connection from {addr[0]}:{addr[1]}\n")
        except OSError as e:
            err(NAME, str(e))
            srv.close()
            return 1
        finally:
            srv.close()
        try:
            _bidirectional(conn, timeout)
        finally:
            conn.close()
        return 0

    # Client mode
    if len(positional) < 2:
        err(NAME, "missing host or port")
        return 2
    host = positional[0]
    ports_spec = positional[1]
    ports = _parse_ports(ports_spec)
    if ports is None:
        err(NAME, f"invalid port spec: {ports_spec}")
        return 2

    if zero_io:
        rc = 0
        for p in ports:
            try:
                with socket.create_connection((host, p), timeout=timeout or 3.0):
                    if verbose:
                        sys.stderr.write(f"Connection to {host} {p} port [tcp/*] succeeded!\n")
                    sys.stdout.write(f"{p}/tcp open\n")
            except (OSError, socket.timeout):
                rc = 1
                if verbose:
                    sys.stderr.write(f"nc: connect to {host} port {p} failed\n")
        return rc

    if len(ports) > 1:
        err(NAME, "port range only valid with -z")
        return 2

    p = ports[0]
    try:
        sock = socket.create_connection((host, p), timeout=timeout)
    except (OSError, socket.timeout) as e:
        err(NAME, f"connect: {e}")
        return 1

    try:
        if verbose:
            sys.stderr.write(f"Connection to {host} {p} port [tcp/*] succeeded!\n")
        _bidirectional(sock, None)  # don't apply timeout to data flow
    finally:
        sock.close()
    return 0
