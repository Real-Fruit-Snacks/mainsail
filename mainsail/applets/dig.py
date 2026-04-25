"""mainsail dig — minimal DNS resolver.

Supports the most common record types (A, AAAA, MX, CNAME, TXT, NS,
SOA, PTR) over UDP. Crafts wire-format queries directly using stdlib
`socket` so there's no third-party dependency. The output is
deliberately a simplified take on `dig`'s familiar layout.

Usage:
    mainsail dig example.com
    mainsail dig example.com AAAA
    mainsail dig MX example.com
    mainsail dig @1.1.1.1 example.com
    mainsail dig +short example.com
    mainsail dig -x 8.8.8.8           # reverse lookup
"""
from __future__ import annotations

import os
import random
import socket
import struct
import sys

from mainsail.common import err

NAME = "dig"
ALIASES: list[str] = []
HELP = "DNS resolver"


_TYPE_NUM = {
    "A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12,
    "MX": 15, "TXT": 16, "AAAA": 28, "ANY": 255,
}
_NUM_TYPE = {v: k for k, v in _TYPE_NUM.items()}


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.strip(".").split("."):
        b = label.encode("idna" if any(ord(c) > 127 for c in label) else "ascii")
        if len(b) > 63:
            raise ValueError(f"label too long: {label!r}")
        out.append(len(b))
        out.extend(b)
    out.append(0)
    return bytes(out)


def _build_query(qid: int, name: str, qtype: int) -> bytes:
    # Header: id, flags(RD=1), qdcount=1, ancount=0, nscount=0, arcount=0
    header = struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    qname = _encode_name(name)
    question = qname + struct.pack("!HH", qtype, 1)  # class IN
    return header + question


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    seen = set()
    pos = offset
    end = None
    while True:
        if pos in seen:
            raise ValueError("compression loop")
        seen.add(pos)
        ln = data[pos]
        if ln == 0:
            pos += 1
            if end is None:
                end = pos
            return ".".join(labels), end
        if ln & 0xC0:
            ptr = ((ln & 0x3F) << 8) | data[pos + 1]
            if end is None:
                end = pos + 2
            pos = ptr
            continue
        labels.append(data[pos + 1:pos + 1 + ln].decode("ascii", "replace"))
        pos += 1 + ln


def _parse_response(data: bytes) -> tuple[int, list[tuple[str, str, int, str]]]:
    """Return (rcode, answers) where each answer is (name, type, ttl, value)."""
    qid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", data[:12])
    rcode = flags & 0x000F
    pos = 12
    # Skip questions
    for _ in range(qd):
        _, pos = _read_name(data, pos)
        pos += 4
    answers: list[tuple[str, str, int, str]] = []
    for _ in range(an):
        name, pos = _read_name(data, pos)
        rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", data[pos:pos + 10])
        pos += 10
        rdata = data[pos:pos + rdlen]
        value = _format_rdata(rtype, rdata, data, pos)
        pos += rdlen
        answers.append((name, _NUM_TYPE.get(rtype, str(rtype)), ttl, value))
    return rcode, answers


def _format_rdata(rtype: int, rdata: bytes, full: bytes, offset: int) -> str:
    if rtype == 1 and len(rdata) == 4:  # A
        return ".".join(str(b) for b in rdata)
    if rtype == 28 and len(rdata) == 16:  # AAAA
        return socket.inet_ntop(socket.AF_INET6, rdata)
    if rtype in (2, 5, 12):  # NS, CNAME, PTR
        name, _ = _read_name(full, offset)
        return name + "."
    if rtype == 15:  # MX
        if len(rdata) < 3:
            return rdata.hex()
        pref = struct.unpack("!H", rdata[:2])[0]
        exch, _ = _read_name(full, offset + 2)
        return f"{pref} {exch}."
    if rtype == 16:  # TXT
        out: list[str] = []
        i = 0
        while i < len(rdata):
            ln = rdata[i]
            i += 1
            out.append(rdata[i:i + ln].decode("utf-8", "replace"))
            i += ln
        return '"' + '" "'.join(out) + '"'
    if rtype == 6:  # SOA
        mname, p2 = _read_name(full, offset)
        rname, p3 = _read_name(full, p2)
        if len(full) >= p3 + 20:
            serial, refresh, retry, expire, minimum = struct.unpack(
                "!IIIII", full[p3:p3 + 20])
            return f"{mname}. {rname}. {serial} {refresh} {retry} {expire} {minimum}"
        return f"{mname}. {rname}."
    return rdata.hex()


def _do_query(server: str, name: str, qtype: int, *, timeout: float = 5.0) -> bytes:
    qid = random.randint(0, 0xFFFF)
    query = _build_query(qid, name, qtype)
    # Try IPv4 first; fall back to IPv6 if server is bracketed/colon-y.
    family = socket.AF_INET
    if ":" in server and not server.startswith("["):
        family = socket.AF_INET6
    sock = socket.socket(family, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        addr = (server, 53)
        sock.sendto(query, addr)
        data, _ = sock.recvfrom(4096)
        return data
    finally:
        sock.close()


def _arpa_for_ip(ip: str) -> str | None:
    try:
        if "." in ip and ":" not in ip:
            parts = ip.split(".")
            if len(parts) != 4:
                return None
            return ".".join(reversed(parts)) + ".in-addr.arpa"
        # IPv6
        packed = socket.inet_pton(socket.AF_INET6, ip)
        nibbles = "".join(f"{b >> 4:x}{b & 0xF:x}" for b in packed)
        return ".".join(reversed(nibbles)) + ".ip6.arpa"
    except OSError:
        return None


def _resolvers_from_etc() -> list[str]:
    paths = ["/etc/resolv.conf"]
    out: list[str] = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            out.append(parts[1])
        except OSError:
            continue
    return out


def main(argv: list[str]) -> int:
    args = argv[1:]
    server: str | None = None
    name: str | None = None
    qtype = "A"
    short = False
    reverse = False
    trace = False
    timeout = 5.0

    rcode_names = {
        0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
        4: "NOTIMP", 5: "REFUSED",
    }

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--help":
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a.startswith("@"):
            server = a[1:]
            i += 1
            continue
        if a == "+short":
            short = True
            i += 1
            continue
        if a == "+trace":
            trace = True
            i += 1
            continue
        if a == "-x" and i + 1 < len(args):
            reverse = True
            arpa = _arpa_for_ip(args[i + 1])
            if arpa is None:
                err(NAME, f"invalid address: {args[i + 1]}")
                return 2
            name = arpa
            qtype = "PTR"
            i += 2
            continue
        if a in {"-t", "--type"} and i + 1 < len(args):
            qtype = args[i + 1].upper()
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
        if a.startswith("-") and a != "-" and len(a) > 1 and not a.startswith("@"):
            err(NAME, f"unknown option: {a}")
            return 2
        # Positional: type or name
        if a.upper() in _TYPE_NUM:
            qtype = a.upper()
        elif name is None:
            name = a
        else:
            err(NAME, f"unexpected argument: {a}")
            return 2
        i += 1

    if name is None:
        err(NAME, "missing query name")
        return 2

    qtype_num = _TYPE_NUM.get(qtype.upper())
    if qtype_num is None:
        err(NAME, f"unknown query type: {qtype}")
        return 2

    servers = [server] if server else (_resolvers_from_etc() or ["1.1.1.1", "8.8.8.8"])

    last_err = None
    response: bytes | None = None
    used_server = None
    for s in servers:
        try:
            response = _do_query(s, name, qtype_num, timeout=timeout)
            used_server = s
            break
        except (socket.timeout, OSError) as e:
            last_err = e
            continue

    if response is None:
        err(NAME, f"no response from any server: {last_err}")
        return 9

    try:
        rcode, answers = _parse_response(response)
    except Exception as e:
        err(NAME, f"malformed response: {e}")
        return 1

    if short:
        for _name, _type, _ttl, value in answers:
            sys.stdout.write(value + "\n")
    else:
        sys.stdout.write(f";; SERVER: {used_server}\n")
        sys.stdout.write(f";; status: {rcode_names.get(rcode, str(rcode))}\n")
        sys.stdout.write(f";; QUESTION: {name}. IN {qtype}\n")
        if answers:
            sys.stdout.write(";; ANSWER SECTION:\n")
            for _name, _type, ttl, value in answers:
                sys.stdout.write(f"{_name}.\t{ttl}\tIN\t{_type}\t{value}\n")
        else:
            sys.stdout.write(";; (no answer)\n")
    sys.stdout.flush()
    return 0 if rcode == 0 else 1
