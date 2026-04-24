"""Comprehensive stress-test harness for mainsail.

Exercises large inputs, Unicode, binary-safe streams, deep trees,
complex pipelines, round-trips, and edge cases.

Usage:
    python scripts/stress.py                     # run against `python -m mainsail`
    python scripts/stress.py /path/to/mainsail.exe  # run against a compiled binary
    python scripts/stress.py --quick             # skip the slowest cases

Notes:
    Nuitka onefile binaries pay a ~250-1000 ms bootstrap cost per
    invocation. The "every applet --help" case fires ~50 invocations
    in a row; pair it with --quick when stressing a frozen binary on
    constrained machines (WSL OOM-kills around 50 sequential extracts).

Exits 0 on all-pass, 1 if anything fails.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BIN_CMD: list[str] = []
QUICK = False
PASSED = 0
FAILS: list[tuple[str, str]] = []
_SCRATCH: Path | None = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # When we chdir into a scratch dir, `python -m mainsail` still needs to
    # find the package. Pin PYTHONPATH to the project root.
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(PROJECT_ROOT) + (os.pathsep + existing if existing else "")
    return env


def run(args: list[str], *, stdin: bytes | None = None, timeout: float = 120.0):
    # Force UTF-8 subprocess I/O so unicode args (CJK, emoji) round-trip
    # cleanly on Windows where the default codepage is cp1252.
    proc = subprocess.run(
        BIN_CMD + args,
        input=stdin,
        capture_output=True,
        timeout=timeout,
        env=_child_env(),
    )
    return proc.stdout, proc.stderr, proc.returncode


def scratch() -> Path:
    assert _SCRATCH is not None, "scratch() called outside a case"
    return _SCRATCH


# -----------------------------------------------------------------------
# Test bodies: each takes no args, uses scratch() for the working directory

def case_large_wc():
    f = scratch() / "big.txt"
    n = 200_000
    f.write_bytes(("x" * 50 + "\n").encode() * n)
    out, err, rc = run(["wc", "-l", str(f)])
    assert rc == 0, f"rc={rc}, stderr={err!r}"
    got = int(out.split()[0])
    assert got == n, f"expected {n}, got {got}"


def case_gzip_roundtrip_5mb():
    f = scratch() / "payload.bin"
    random.seed(42)
    data = bytes(random.getrandbits(8) for _ in range(5_000_000))
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    _, _, rc = run(["gzip", str(f)])
    assert rc == 0
    assert not f.exists()
    _, _, rc = run(["gunzip", str(f) + ".gz"])
    assert rc == 0
    assert f.exists()
    out, _, rc = run(["sha256sum", str(f)])
    assert rc == 0
    got = out.decode().split()[0]
    assert got == expected, f"hash drift: {expected} vs {got}"


def case_many_files_2000():
    d = scratch() / "many"
    d.mkdir()
    for i in range(2000):
        (d / f"f_{i:05d}.dat").write_bytes(b"")
    out, _, rc = run(["ls", str(d)])
    assert rc == 0
    ls_count = len([ln for ln in out.decode().splitlines() if ln.strip()])
    assert ls_count == 2000, f"ls saw {ls_count}"
    out, _, rc = run(["find", str(d), "-type", "f", "-name", "f_*.dat"])
    assert rc == 0
    find_count = len([ln for ln in out.decode().splitlines() if ln.strip()])
    assert find_count == 2000, f"find saw {find_count}"


def case_deep_tree_50():
    parts = ["L" + str(i) for i in range(50)]
    deep = scratch().joinpath(*parts)
    _, _, rc = run(["mkdir", "-p", str(deep)])
    assert rc == 0
    assert deep.is_dir()
    out, _, rc = run(["find", str(scratch()), "-type", "d"])
    assert rc == 0
    n = len([ln for ln in out.decode().splitlines() if ln.strip()])
    assert n >= 51, f"dirs: {n}"


def case_cat_binary_safe():
    random.seed(7)
    data = bytes(random.getrandbits(8) for _ in range(64 * 1024))
    f = scratch() / "b.bin"
    f.write_bytes(data)
    out, _, rc = run(["cat", str(f)])
    assert rc == 0
    assert out == data, f"cat changed {sum(a != b for a, b in zip(out, data))} bytes"


def case_tee_binary_safe():
    random.seed(11)
    data = bytes(random.getrandbits(8) for _ in range(64 * 1024))
    f = scratch() / "tee_out.bin"
    out, _, rc = run(["tee", str(f)], stdin=data)
    assert rc == 0
    assert out == data, "tee stdout differs"
    assert f.read_bytes() == data, "tee file differs"


def case_tr_null_delete():
    out, _, rc = run(["tr", "-d", "\\0"], stdin=b"hello\x00world\x00foo")
    assert rc == 0
    assert out == b"helloworldfoo", f"got {out!r}"


def case_unicode_cat_wc():
    text = "Hello 世界 🌍\n日本語テスト\n"
    f = scratch() / "u.txt"
    f.write_bytes(text.encode("utf-8"))
    out, _, rc = run(["cat", str(f)])
    assert rc == 0
    assert out.decode("utf-8") == text
    out, _, rc = run(["wc", "-l", str(f)])
    assert rc == 0
    assert int(out.split()[0]) == 2


def case_unicode_grep_cjk():
    f = scratch() / "u.txt"
    f.write_bytes("first\n日本語のテキスト\nthird\n".encode("utf-8"))
    out, err, rc = run(["grep", "日本", str(f)])
    assert rc == 0, f"rc={rc}, stderr={err!r}"
    decoded = out.decode("utf-8", errors="replace")
    assert "日本語" in decoded, f"no CJK match in output: {decoded!r}"


def case_empty_input():
    f = scratch() / "empty"
    f.write_bytes(b"")
    out, _, rc = run(["cat", str(f)])
    assert rc == 0 and out == b""
    out, _, rc = run(["wc", str(f)])
    assert rc == 0
    parts = [int(p) for p in out.split()[:3]]
    assert parts == [0, 0, 0], f"wc empty: {parts}"
    out, _, rc = run(["sha256sum", str(f)])
    assert rc == 0
    assert out.decode().startswith(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    _, _, rc = run(["gzip", "-c", str(f)])
    assert rc == 0


def case_no_trailing_newline():
    f = scratch() / "nnl.txt"
    f.write_bytes(b"one\ntwo\nthree")
    out, _, rc = run(["wc", "-l", str(f)])
    assert rc == 0
    # POSIX: lines = newline count; "three" has none, expect 2
    assert int(out.split()[0]) == 2


def case_seq_sort_head_pipeline():
    env = _child_env()
    p1 = subprocess.Popen(BIN_CMD + ["seq", "10"], stdout=subprocess.PIPE, env=env)
    p2 = subprocess.Popen(BIN_CMD + ["sort", "-rn"], stdin=p1.stdout, stdout=subprocess.PIPE, env=env)
    p1.stdout.close()
    p3 = subprocess.Popen(BIN_CMD + ["head", "-3"], stdin=p2.stdout, stdout=subprocess.PIPE, env=env)
    p2.stdout.close()
    out, _ = p3.communicate(timeout=30)
    assert p3.returncode == 0, f"pipeline rc={p3.returncode}"
    # splitlines handles both \n and \r\n (Windows stdout translates LF→CRLF)
    lines = out.decode().splitlines()
    assert lines == ["10", "9", "8"], f"got {lines!r}"


def case_find_xargs_hash_stable():
    d = scratch() / "tree"
    d.mkdir()
    for i in range(20):
        (d / f"f{i}.txt").write_bytes(f"content_{i}\n".encode())
    env = _child_env()

    def pipeline() -> str:
        # Use -print0 / -0 so Windows backslashes aren't eaten by xargs'
        # default shell-like tokenizer.
        p1 = subprocess.Popen(
            BIN_CMD + ["find", str(d), "-type", "f", "-print0"],
            stdout=subprocess.PIPE, env=env,
        )
        p2 = subprocess.Popen(
            BIN_CMD + ["xargs", "-0", "-n", "1", *BIN_CMD, "sha256sum"],
            stdin=p1.stdout, stdout=subprocess.PIPE, env=env,
        )
        p1.stdout.close()
        out, _ = p2.communicate(timeout=60)
        return out.decode()

    r1 = pipeline()
    r2 = pipeline()
    # Sort lines so order from find doesn't affect the comparison
    r1_sorted = "\n".join(sorted(r1.splitlines()))
    r2_sorted = "\n".join(sorted(r2.splitlines()))
    assert r1_sorted == r2_sorted, "pipeline not stable across runs"
    n_lines = len(r1.splitlines())
    assert n_lines == 20, f"got {n_lines} lines:\n{r1[:500]}"


def case_sha256_known_vectors():
    vectors = {
        b"": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        b"abc": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        b"The quick brown fox jumps over the lazy dog":
            "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
    }
    for i, (payload, expected) in enumerate(vectors.items()):
        f = scratch() / f"v{i}.bin"
        f.write_bytes(payload)
        out, _, rc = run(["sha256sum", str(f)])
        assert rc == 0
        got = out.decode().split()[0]
        assert got == expected, f"{payload!r}: {got} vs {expected}"


def case_tar_roundtrip():
    src = scratch() / "src"
    src.mkdir()
    payloads = {}
    for i in range(15):
        p = src / f"file_{i}.txt"
        payload = f"data number {i}\n".encode() * (i + 1)
        p.write_bytes(payload)
        payloads[p.name] = payload

    archive = scratch() / "out.tar.gz"
    cwd = os.getcwd()
    os.chdir(scratch())
    try:
        _, err, rc = run(["tar", "-czf", str(archive), "src"])
        assert rc == 0, f"tar create rc={rc}, stderr={err!r}"
        target = scratch() / "restore"
        target.mkdir()
        _, err, rc = run(["tar", "-xzf", str(archive), "-C", str(target)])
        assert rc == 0, f"tar extract rc={rc}, stderr={err!r}"
    finally:
        os.chdir(cwd)

    for name, expected in payloads.items():
        got = (target / "src" / name).read_bytes()
        assert got == expected, f"tar lost data for {name}"


def case_zip_roundtrip():
    src = scratch() / "src"
    src.mkdir()
    for i in range(10):
        (src / f"f{i}").write_bytes(f"payload-{i}".encode() * (i + 1))
    archive = scratch() / "out.zip"
    cwd = os.getcwd()
    os.chdir(scratch())
    try:
        _, err, rc = run(["zip", "-r", str(archive), "src"])
        assert rc == 0, f"zip rc={rc}, stderr={err!r}"
        target = scratch() / "restore"
        _, err, rc = run(["unzip", "-d", str(target), str(archive)])
        assert rc == 0, f"unzip rc={rc}, stderr={err!r}"
    finally:
        os.chdir(cwd)
    for i in range(10):
        got = (target / "src" / f"f{i}").read_bytes()
        expected = f"payload-{i}".encode() * (i + 1)
        assert got == expected, f"payload mismatch for f{i}"


def case_sed_in_place():
    f = scratch() / "s.txt"
    f.write_bytes(b"alpha\nbeta\ngamma\n")
    _, _, rc = run(["sed", "-i", "s/beta/BETA/", str(f)])
    assert rc == 0
    assert f.read_bytes() == b"alpha\nBETA\ngamma\n"


def case_sort_50k_numeric():
    random.seed(99)
    lines = [str(random.randint(0, 100_000)) for _ in range(50_000)]
    f = scratch() / "nums.txt"
    f.write_bytes(("\n".join(lines) + "\n").encode())
    out, _, rc = run(["sort", "-n", str(f)], timeout=180)
    assert rc == 0
    got = [int(x) for x in out.decode().splitlines() if x]
    assert got == sorted(int(x) for x in lines)


def case_unknown_applet_errors():
    _, err, rc = run(["definitely_not_an_applet_xyz"])
    assert rc == 1
    assert b"unknown applet" in err


def case_rm_missing_without_f():
    _, _, rc = run(["rm", str(scratch() / "never_existed")])
    assert rc == 1


def case_every_applet_has_help():
    out, _, rc = run(["--list"])
    assert rc == 0
    names = [ln.strip().split()[0] for ln in out.decode().splitlines() if ln.strip()]
    assert len(names) >= 40, f"only {len(names)} applets listed"
    missing = []
    for name in names:
        h, _, rc = run([name, "--help"])
        if rc != 0 or f"{name} - ".encode() not in h:
            missing.append(name)
    assert not missing, f"no help for: {missing}"


def case_md5sum_tag_check_roundtrip():
    files = []
    for i in range(5):
        p = scratch() / f"r{i}"
        p.write_bytes(f"content {i}".encode())
        files.append(str(p))
    out, _, rc = run(["md5sum", "--tag", *files])
    assert rc == 0
    sumfile = scratch() / "sums.md5"
    sumfile.write_bytes(out)
    _, _, rc = run(["md5sum", "-c", str(sumfile)])
    assert rc == 0


def case_echo_500_args():
    args = ["echo"] + [f"arg{i}" for i in range(500)]
    out, _, rc = run(args)
    assert rc == 0
    decoded = out.decode()
    assert decoded.count("\n") == 1
    assert "arg0" in decoded and "arg499" in decoded


# -----------------------------------------------------------------------
# Registry: (name, fn, slow)

CASES: list[tuple[str, callable, bool]] = [
    ("large: 10 MB wc -l accurate",               case_large_wc,                  False),
    ("large: 5 MB gzip roundtrip preserves hash", case_gzip_roundtrip_5mb,        True),
    ("many-files: ls + find see 2000 files",      case_many_files_2000,           False),
    ("deep-tree: 50-level mkdir -p / find",       case_deep_tree_50,              False),
    ("binary-safe: cat preserves 64K random",     case_cat_binary_safe,           False),
    ("binary-safe: tee to file + stdout",         case_tee_binary_safe,           False),
    ("tr: -d strips nulls cleanly",               case_tr_null_delete,            False),
    ("unicode: cat + wc -l on CJK/emoji",         case_unicode_cat_wc,            False),
    ("unicode: grep finds CJK substring",         case_unicode_grep_cjk,          False),
    ("edge: empty input across 4 applets",        case_empty_input,               False),
    ("edge: file without trailing newline",       case_no_trailing_newline,       False),
    ("pipeline: seq|sort -rn|head -3",            case_seq_sort_head_pipeline,    False),
    ("pipeline: find|sort|xargs sha256sum stable", case_find_xargs_hash_stable,   True),
    ("sha256: matches RFC-known vectors",         case_sha256_known_vectors,      False),
    ("archive: tar -czf + -xzf roundtrip",        case_tar_roundtrip,             False),
    ("archive: zip -r + unzip roundtrip",         case_zip_roundtrip,             False),
    ("sed: -i edits in place",                    case_sed_in_place,              False),
    ("sort: -n on 50k random ints",               case_sort_50k_numeric,          True),
    ("error: unknown applet ->rc=1",              case_unknown_applet_errors,     False),
    ("error: rm missing file ->rc=1",             case_rm_missing_without_f,      False),
    ("help: every listed applet has --help",      case_every_applet_has_help,     True),
    ("md5sum: --tag <-> -c roundtrip",            case_md5sum_tag_check_roundtrip, False),
    ("echo: 500 args produce 1 line",             case_echo_500_args,             False),
]


def _run_one(name: str, fn, slow: bool) -> None:
    global PASSED, _SCRATCH
    if slow and QUICK:
        print(f"  {name:<46}  SKIP (--quick)")
        return
    print(f"  {name:<46}  ", end="", flush=True)
    root = Path(tempfile.mkdtemp(prefix="mainsail_stress_"))
    _SCRATCH = root
    t0 = time.perf_counter()
    try:
        fn()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"OK   ({elapsed:>7.0f} ms)")
        PASSED += 1
    except AssertionError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"FAIL ({elapsed:>7.0f} ms): {e}")
        FAILS.append((name, str(e)))
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"ERR  ({elapsed:>7.0f} ms): {type(e).__name__}: {e}")
        FAILS.append((name, f"{type(e).__name__}: {e}"))
    finally:
        _SCRATCH = None
        def _onerror(func, path, exc_info):
            try:
                os.chmod(path, 0o666)
                func(path)
            except OSError:
                pass
        shutil.rmtree(root, onerror=_onerror)


def main() -> int:
    global BIN_CMD, QUICK
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", nargs="?", default=None,
                        help="mainsail binary to test (default: python -m mainsail)")
    parser.add_argument("--quick", action="store_true",
                        help="skip slow cases")
    args = parser.parse_args()

    if args.binary:
        # Resolve so tests that chdir into a scratch dir still find it.
        resolved = str(Path(args.binary).resolve())
        BIN_CMD = [resolved]
        label = resolved
    else:
        BIN_CMD = [sys.executable, "-m", "mainsail"]
        label = " ".join(BIN_CMD)
    QUICK = args.quick

    print(f"stress-testing: {label}")
    print("-" * 72)
    for name, fn, slow in CASES:
        _run_one(name, fn, slow)
    print("-" * 72)
    total = PASSED + len(FAILS)
    if FAILS:
        print(f"{PASSED}/{total} passed, {len(FAILS)} FAILED")
        for n, e in FAILS:
            print(f"  FAIL {n}: {e}")
        return 1
    print(f"{PASSED}/{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
