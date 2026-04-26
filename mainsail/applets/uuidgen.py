"""mainsail uuidgen — generate a UUID."""
from __future__ import annotations

import sys
import uuid

from mainsail.common import err

NAME = "uuidgen"
ALIASES: list[str] = []
HELP = "generate a UUID"


def main(argv: list[str]) -> int:
    args = argv[1:]
    flavor = "random"  # random | time | md5 | sha1
    namespace: uuid.UUID | None = None
    name: str | None = None
    upper = False
    no_dashes = False
    count = 1

    i = 0
    while i < len(args):
        a = args[i]
        if a in {"-h", "--help"}:
            from mainsail.usage import USAGE
            sys.stdout.write(f"{NAME} - {HELP}\n\n{USAGE.get(NAME, '')}")
            return 0
        if a in {"-r", "--random"}:
            flavor = "random"
            i += 1; continue
        if a in {"-t", "--time"}:
            flavor = "time"
            i += 1; continue
        if a in {"-m", "--md5"}:
            flavor = "md5"
            i += 1; continue
        if a in {"-s", "--sha1"}:
            flavor = "sha1"
            i += 1; continue
        if a in {"-n", "--namespace"} and i + 1 < len(args):
            ns_arg = args[i + 1]
            preset = {
                "@dns": uuid.NAMESPACE_DNS, "@url": uuid.NAMESPACE_URL,
                "@oid": uuid.NAMESPACE_OID, "@x500": uuid.NAMESPACE_X500,
            }.get(ns_arg)
            if preset:
                namespace = preset
            else:
                try:
                    namespace = uuid.UUID(ns_arg)
                except ValueError:
                    err(NAME, f"invalid namespace: {ns_arg}")
                    return 2
            i += 2; continue
        if a == "-N" and i + 1 < len(args):
            name = args[i + 1]
            i += 2; continue
        if a == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2; continue
        if a == "--upper":
            upper = True
            i += 1; continue
        if a == "--hex":
            no_dashes = True
            i += 1; continue
        if a in {"-c", "--count"} and i + 1 < len(args):
            try:
                count = int(args[i + 1])
            except ValueError:
                err(NAME, f"invalid count: {args[i + 1]}")
                return 2
            if count < 1:
                err(NAME, "count must be >= 1")
                return 2
            i += 2; continue
        if a.startswith("-") and a != "-" and len(a) > 1:
            err(NAME, f"unknown option: {a}")
            return 2
        break

    if flavor in {"md5", "sha1"} and (namespace is None or name is None):
        err(NAME, f"--{flavor} requires --namespace and --name")
        return 2

    for _ in range(count):
        if flavor == "random":
            u = uuid.uuid4()
        elif flavor == "time":
            u = uuid.uuid1()
        elif flavor == "md5":
            assert namespace is not None and name is not None
            u = uuid.uuid3(namespace, name)
        else:  # sha1
            assert namespace is not None and name is not None
            u = uuid.uuid5(namespace, name)
        out = u.hex if no_dashes else str(u)
        if upper:
            out = out.upper()
        sys.stdout.write(out + "\n")
    sys.stdout.flush()
    return 0
