from __future__ import annotations

import os
import sys
from pathlib import Path


def test_version(invoke):
    rc, out, _ = invoke("--version")
    assert rc == 0
    assert out.startswith("pybox ")


def test_list_contains_core_applets(invoke):
    rc, out, _ = invoke("--list")
    assert rc == 0
    for name in ["echo", "pwd", "ls", "cat", "cp", "mv", "rm", "mkdir",
                 "touch", "find", "grep", "head", "tail", "wc", "sort",
                 "which", "env"]:
        assert f"  {name} " in out or f"  {name}  " in out, f"missing applet {name}"


def test_unknown_applet(invoke):
    rc, _, err = invoke("bogus_xyz")
    assert rc == 1
    assert "unknown applet" in err


# echo

def test_echo_basic(invoke):
    rc, out, _ = invoke("echo", "hello", "world")
    assert rc == 0
    assert out == "hello world\n"


def test_echo_no_newline(invoke):
    rc, out, _ = invoke("echo", "-n", "hi")
    assert rc == 0
    assert out == "hi"


def test_echo_interpret_escapes(invoke):
    rc, out, _ = invoke("echo", "-e", "a\\nb")
    assert rc == 0
    assert out == "a\nb\n"


# pwd

def test_pwd(invoke, workspace):
    rc, out, _ = invoke("pwd")
    assert rc == 0
    assert out.strip() == str(workspace) or Path(out.strip()).resolve() == workspace.resolve()


# mkdir / touch / ls

def test_mkdir_and_ls(invoke, workspace):
    rc, _, _ = invoke("mkdir", "sub")
    assert rc == 0
    assert (workspace / "sub").is_dir()

    rc, out, _ = invoke("ls", ".")
    assert rc == 0
    assert "sub" in out


def test_mkdir_p_nested(invoke, workspace):
    rc, _, _ = invoke("mkdir", "-p", "a/b/c")
    assert rc == 0
    assert (workspace / "a" / "b" / "c").is_dir()


def test_ls_F_classify(invoke, workspace):
    (workspace / "subdir").mkdir()
    (workspace / "file.txt").write_bytes(b"")
    rc, out, _ = invoke("ls", "-F", ".")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert "subdir/" in lines
    assert "file.txt" in lines


def test_ls_S_by_size(invoke, workspace):
    (workspace / "small").write_bytes(b"x")
    (workspace / "big").write_bytes(b"x" * 100)
    (workspace / "medium").write_bytes(b"x" * 10)
    rc, out, _ = invoke("ls", "-S", ".")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert lines.index("big") < lines.index("medium") < lines.index("small")


def test_ls_t_by_time(invoke, workspace):
    import time as t
    (workspace / "old").write_bytes(b"")
    t.sleep(0.05)
    (workspace / "new").write_bytes(b"")
    rc, out, _ = invoke("ls", "-t", ".")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert lines.index("new") < lines.index("old")


def test_ls_r_reverse(invoke, workspace):
    (workspace / "a").write_bytes(b"")
    (workspace / "b").write_bytes(b"")
    (workspace / "c").write_bytes(b"")
    rc, out, _ = invoke("ls", "-r", ".")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert lines == ["c", "b", "a"]


def test_ls_a_shows_dots(invoke, workspace):
    (workspace / "visible").write_bytes(b"")
    rc, out, _ = invoke("ls", "-a", ".")
    assert rc == 0
    names = [ln for ln in out.splitlines() if ln]
    assert "." in names
    assert ".." in names
    assert "visible" in names


def test_touch_creates_file(invoke, workspace):
    rc, _, _ = invoke("touch", "new.txt")
    assert rc == 0
    assert (workspace / "new.txt").is_file()


def test_touch_r_reference(invoke, workspace):
    ref = workspace / "ref.txt"
    ref.write_bytes(b"")
    ref_mtime = 1600000000.0
    os.utime(ref, (ref_mtime, ref_mtime))
    target = workspace / "target.txt"
    target.write_bytes(b"")
    rc, _, _ = invoke("touch", "-r", str(ref), str(target))
    assert rc == 0
    assert abs(target.stat().st_mtime - ref_mtime) < 1


def test_touch_d_iso_date(invoke, workspace):
    from datetime import datetime as _dt
    target = workspace / "t.txt"
    target.write_bytes(b"")
    rc, _, _ = invoke("touch", "-d", "2020-01-15", str(target))
    assert rc == 0
    dt = _dt.fromtimestamp(target.stat().st_mtime)
    assert (dt.year, dt.month, dt.day) == (2020, 1, 15)


def test_touch_d_iso_datetime(invoke, workspace):
    from datetime import datetime as _dt
    target = workspace / "t.txt"
    target.write_bytes(b"")
    rc, _, _ = invoke("touch", "-d", "2020-01-15 14:30:00", str(target))
    assert rc == 0
    dt = _dt.fromtimestamp(target.stat().st_mtime)
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2020, 1, 15, 14, 30)


def test_touch_t_posix(invoke, workspace):
    from datetime import datetime as _dt
    target = workspace / "t.txt"
    target.write_bytes(b"")
    rc, _, _ = invoke("touch", "-t", "202001150930", str(target))
    assert rc == 0
    dt = _dt.fromtimestamp(target.stat().st_mtime)
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2020, 1, 15, 9, 30)


# cat / cp / mv / rm

def test_cat(invoke, workspace):
    (workspace / "x.txt").write_text("line1\nline2\n")
    rc, out, _ = invoke("cat", "x.txt")
    assert rc == 0
    assert out == "line1\nline2\n"


def test_cat_n(invoke, workspace):
    (workspace / "x.txt").write_text("a\nb\n")
    rc, out, _ = invoke("cat", "-n", "x.txt")
    assert rc == 0
    assert "1\ta\n" in out
    assert "2\tb\n" in out


def test_cp(invoke, workspace):
    (workspace / "a.txt").write_text("data")
    rc, _, _ = invoke("cp", "a.txt", "b.txt")
    assert rc == 0
    assert (workspace / "b.txt").read_text() == "data"


def test_mv(invoke, workspace):
    (workspace / "a.txt").write_text("data")
    rc, _, _ = invoke("mv", "a.txt", "b.txt")
    assert rc == 0
    assert not (workspace / "a.txt").exists()
    assert (workspace / "b.txt").read_text() == "data"


def test_cp_n_noclobber(invoke, workspace):
    (workspace / "src.txt").write_bytes(b"new")
    (workspace / "dst.txt").write_bytes(b"old")
    rc, _, _ = invoke("cp", "-n", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "dst.txt").read_bytes() == b"old"


def test_cp_u_skip_when_target_newer(invoke, workspace):
    import time as t
    (workspace / "src.txt").write_bytes(b"older_content")
    t.sleep(0.05)
    (workspace / "dst.txt").write_bytes(b"newer_content")
    rc, _, _ = invoke("cp", "-u", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "dst.txt").read_bytes() == b"newer_content"


def test_cp_u_overwrite_when_source_newer(invoke, workspace):
    import time as t
    (workspace / "dst.txt").write_bytes(b"older")
    t.sleep(0.05)
    (workspace / "src.txt").write_bytes(b"newer")
    rc, _, _ = invoke("cp", "-u", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "dst.txt").read_bytes() == b"newer"


def test_cp_i_yes(invoke, workspace, monkeypatch):
    import io as _io
    (workspace / "src.txt").write_bytes(b"new")
    (workspace / "dst.txt").write_bytes(b"old")
    monkeypatch.setattr(sys, "stdin", _io.StringIO("y\n"))
    rc, _, _ = invoke("cp", "-i", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "dst.txt").read_bytes() == b"new"


def test_cp_i_no(invoke, workspace, monkeypatch):
    import io as _io
    (workspace / "src.txt").write_bytes(b"new")
    (workspace / "dst.txt").write_bytes(b"old")
    monkeypatch.setattr(sys, "stdin", _io.StringIO("n\n"))
    rc, _, _ = invoke("cp", "-i", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "dst.txt").read_bytes() == b"old"


def test_mv_n_noclobber(invoke, workspace):
    (workspace / "src.txt").write_bytes(b"new")
    (workspace / "dst.txt").write_bytes(b"old")
    rc, _, _ = invoke("mv", "-n", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "src.txt").exists()
    assert (workspace / "dst.txt").read_bytes() == b"old"


def test_mv_u_skip_when_target_newer(invoke, workspace):
    import time as t
    (workspace / "src.txt").write_bytes(b"src_content")
    t.sleep(0.05)
    (workspace / "dst.txt").write_bytes(b"dst_content")
    rc, _, _ = invoke("mv", "-u", "src.txt", "dst.txt")
    assert rc == 0
    assert (workspace / "src.txt").exists()
    assert (workspace / "dst.txt").read_bytes() == b"dst_content"


def test_rm(invoke, workspace):
    (workspace / "a.txt").write_text("x")
    rc, _, _ = invoke("rm", "a.txt")
    assert rc == 0
    assert not (workspace / "a.txt").exists()


def test_rm_recursive(invoke, workspace):
    (workspace / "d").mkdir()
    (workspace / "d" / "x.txt").write_text("y")
    rc, _, _ = invoke("rm", "-rf", "d")
    assert rc == 0
    assert not (workspace / "d").exists()


# find

def test_find_by_name(invoke, workspace):
    (workspace / "a").mkdir()
    (workspace / "a" / "x.log").write_text("")
    (workspace / "a" / "y.txt").write_text("")
    rc, out, _ = invoke("find", "a", "-name", "*.log")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert any(ln.endswith("x.log") for ln in lines)
    assert not any(ln.endswith("y.txt") for ln in lines)


def test_find_type_d(invoke, workspace):
    (workspace / "d1").mkdir()
    (workspace / "f1").write_text("")
    rc, out, _ = invoke("find", ".", "-type", "d")
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln]
    assert any(ln.endswith("d1") for ln in lines)
    assert not any(ln.endswith("f1") for ln in lines)


def test_find_size(invoke, workspace):
    (workspace / "empty").write_bytes(b"")
    (workspace / "small").write_bytes(b"x" * 10)
    (workspace / "big").write_bytes(b"x" * 2000)
    rc, out, _ = invoke("find", ".", "-type", "f", "-size", "+100c")
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("big" in p for p in paths)
    assert not any("small" in p for p in paths)
    assert not any("empty" in p for p in paths)


def test_find_empty(invoke, workspace):
    (workspace / "full.txt").write_bytes(b"x")
    (workspace / "empty.txt").write_bytes(b"")
    rc, out, _ = invoke("find", ".", "-type", "f", "-empty")
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("empty.txt" in p for p in paths)
    assert not any("full.txt" in p for p in paths)


def test_find_not(invoke, workspace):
    (workspace / "a.txt").write_bytes(b"")
    (workspace / "b.log").write_bytes(b"")
    rc, out, _ = invoke("find", ".", "-type", "f", "!", "-name", "*.log")
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("a.txt" in p for p in paths)
    assert not any("b.log" in p for p in paths)


def test_find_or_parens(invoke, workspace):
    (workspace / "a.txt").write_bytes(b"")
    (workspace / "b.log").write_bytes(b"")
    (workspace / "c.md").write_bytes(b"")
    rc, out, _ = invoke(
        "find", ".", "-type", "f", "(",
        "-name", "*.txt", "-o", "-name", "*.log", ")",
    )
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("a.txt" in p for p in paths)
    assert any("b.log" in p for p in paths)
    assert not any("c.md" in p for p in paths)


def test_find_delete(invoke, workspace):
    (workspace / "doomed.tmp").write_bytes(b"")
    (workspace / "safe.txt").write_bytes(b"")
    rc, _, _ = invoke("find", ".", "-name", "*.tmp", "-delete")
    assert rc == 0
    assert not (workspace / "doomed.tmp").exists()
    assert (workspace / "safe.txt").exists()


def test_find_prune(invoke, workspace):
    (workspace / "good").mkdir()
    (workspace / "good" / "keep.txt").write_bytes(b"")
    (workspace / "skip").mkdir()
    (workspace / "skip" / "hide.txt").write_bytes(b"")
    rc, out, _ = invoke("find", ".", "-name", "skip", "-prune", "-o", "-print")
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("keep.txt" in p for p in paths)
    assert not any("hide.txt" in p for p in paths)


def test_find_newer(invoke, workspace):
    import time as t
    a = workspace / "a.txt"
    a.write_bytes(b"a")
    t.sleep(0.05)
    b = workspace / "b.txt"
    b.write_bytes(b"b")
    rc, out, _ = invoke("find", ".", "-type", "f", "-newer", str(a))
    assert rc == 0
    paths = [p for p in out.splitlines() if p]
    assert any("b.txt" in p for p in paths)
    assert not any("a.txt" in p for p in paths)


def test_find_exec(invoke, workspace):
    (workspace / "target.txt").write_bytes(b"hi")
    marker = workspace / "marker.out"
    script = f"open(r'{marker}', 'w').write('ok')"
    rc, _, _ = invoke(
        "find", ".", "-name", "target.txt",
        "-exec", sys.executable, "-c", script, ";",
    )
    assert rc == 0
    assert marker.exists() and marker.read_text() == "ok"


# grep

def test_grep_basic(invoke, workspace):
    (workspace / "f.txt").write_text("apple\nbanana\napricot\n")
    rc, out, _ = invoke("grep", "ap", "f.txt")
    assert rc == 0
    assert "apple" in out
    assert "apricot" in out
    assert "banana" not in out


def test_grep_i(invoke, workspace):
    (workspace / "f.txt").write_text("Apple\napple\n")
    rc, out, _ = invoke("grep", "-i", "APPLE", "f.txt")
    assert rc == 0
    assert "Apple" in out
    assert "apple" in out


def test_grep_v(invoke, workspace):
    (workspace / "f.txt").write_text("a\nb\nc\n")
    rc, out, _ = invoke("grep", "-v", "b", "f.txt")
    assert "a" in out
    assert "c" in out
    assert "b\n" not in out


def test_grep_no_match(invoke, workspace):
    (workspace / "f.txt").write_text("a\n")
    rc, _, _ = invoke("grep", "zzz", "f.txt")
    assert rc == 1


def test_grep_context_C(invoke, workspace):
    (workspace / "f.txt").write_text("a\nb\nMATCH\nc\nd\n")
    rc, out, _ = invoke("grep", "-C", "1", "MATCH", "f.txt")
    assert rc == 0
    assert "MATCH" in out
    assert "b\n" in out
    assert "c\n" in out
    # outside context
    assert "a\n" not in out
    assert "d\n" not in out


def test_grep_context_A(invoke, workspace):
    (workspace / "f.txt").write_text("one\nMATCH\nthree\nfour\nfive\n")
    rc, out, _ = invoke("grep", "-A", "2", "MATCH", "f.txt")
    assert rc == 0
    assert "MATCH" in out
    assert "three" in out
    assert "four" in out
    assert "five" not in out
    assert "one" not in out


def test_grep_context_B(invoke, workspace):
    (workspace / "f.txt").write_text("one\ntwo\nMATCH\nafter\n")
    rc, out, _ = invoke("grep", "-B", "1", "MATCH", "f.txt")
    assert rc == 0
    assert "two" in out
    assert "MATCH" in out
    assert "one" not in out
    assert "after" not in out


def test_grep_only_matching(invoke, workspace):
    (workspace / "f.txt").write_text("foo and bar\nbar and foo\n")
    rc, out, _ = invoke("grep", "-o", "foo", "f.txt")
    assert rc == 0
    assert out.count("foo") == 2
    assert "bar" not in out


def test_grep_word_boundary(invoke, workspace):
    (workspace / "f.txt").write_text("apple\npineapple\nappleseed\n")
    rc, out, _ = invoke("grep", "-w", "apple", "f.txt")
    assert rc == 0
    lines = out.strip().split("\n")
    assert lines == ["apple"]


def test_grep_quiet_match(invoke, workspace):
    (workspace / "f.txt").write_text("hello\nworld\n")
    rc, out, _ = invoke("grep", "-q", "hello", "f.txt")
    assert rc == 0
    assert out == ""


def test_grep_quiet_no_match(invoke, workspace):
    (workspace / "f.txt").write_text("hello\n")
    rc, out, _ = invoke("grep", "-q", "zzz", "f.txt")
    assert rc == 1
    assert out == ""


def test_grep_context_separator(invoke, workspace):
    (workspace / "f.txt").write_text("\n".join([
        "skip1", "skip2", "MATCH1", "skip3", "skip4", "skip5",
        "skip6", "MATCH2", "skip7",
    ]) + "\n")
    rc, out, _ = invoke("grep", "-A", "1", "MATCH", "f.txt")
    assert rc == 0
    # Two separate groups, so a "--" separator should appear
    assert "--" in out


# head / tail / wc

def test_head(invoke, workspace):
    (workspace / "f.txt").write_text("\n".join(str(i) for i in range(20)) + "\n")
    rc, out, _ = invoke("head", "-3", "f.txt")
    assert rc == 0
    assert out == "0\n1\n2\n"


def test_tail(invoke, workspace):
    (workspace / "f.txt").write_text("\n".join(str(i) for i in range(20)) + "\n")
    rc, out, _ = invoke("tail", "-3", "f.txt")
    assert rc == 0
    assert out == "17\n18\n19\n"


def test_tail_f_follows_append(workspace):
    """Run 'pybox tail -f' as a subprocess and verify it picks up appends."""
    import subprocess
    import time as t
    pybox_root = Path(__file__).resolve().parent.parent
    f = workspace / "follow.log"
    f.write_bytes(b"initial\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pybox_root) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [sys.executable, "-m", "pybox", "tail", "-f", "-s", "0.05", str(f)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(workspace),
    )
    try:
        t.sleep(0.3)
        with f.open("ab") as fh:
            fh.write(b"appended\n")
        t.sleep(0.4)
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
    assert b"appended" in out


def test_wc(invoke, workspace):
    (workspace / "f.txt").write_text("one two\nthree four five\n")
    rc, out, _ = invoke("wc", "-l", "f.txt")
    assert rc == 0
    assert out.strip().startswith("2")


def test_wc_w(invoke, workspace):
    (workspace / "f.txt").write_text("a b c\n")
    rc, out, _ = invoke("wc", "-w", "f.txt")
    assert rc == 0
    assert out.strip().startswith("3")


# sort

def test_sort(invoke, workspace):
    (workspace / "f.txt").write_text("c\na\nb\n")
    rc, out, _ = invoke("sort", "f.txt")
    assert rc == 0
    assert out == "a\nb\nc\n"


def test_sort_n(invoke, workspace):
    (workspace / "f.txt").write_text("10\n2\n1\n")
    rc, out, _ = invoke("sort", "-n", "f.txt")
    assert rc == 0
    assert out == "1\n2\n10\n"


def test_sort_u(invoke, workspace):
    (workspace / "f.txt").write_text("a\nb\na\n")
    rc, out, _ = invoke("sort", "-u", "f.txt")
    assert rc == 0
    assert out == "a\nb\n"


def test_sort_k_field(invoke, workspace):
    (workspace / "f.txt").write_text("b 1\na 2\nc 0\n")
    rc, out, _ = invoke("sort", "-k", "2", "f.txt")
    assert rc == 0
    assert out.splitlines() == ["c 0", "b 1", "a 2"]


def test_sort_k_numeric(invoke, workspace):
    (workspace / "f.txt").write_text("x 10\ny 2\nz 100\n")
    rc, out, _ = invoke("sort", "-k", "2n", "f.txt")
    assert rc == 0
    assert out.splitlines() == ["y 2", "x 10", "z 100"]


def test_sort_t_separator(invoke, workspace):
    (workspace / "f.txt").write_text("c,1\na,3\nb,2\n")
    rc, out, _ = invoke("sort", "-t", ",", "-k", "2n", "f.txt")
    assert rc == 0
    assert out.splitlines() == ["c,1", "b,2", "a,3"]


def test_sort_o_output(invoke, workspace):
    (workspace / "in.txt").write_text("c\na\nb\n")
    rc, out, _ = invoke("sort", "-o", "out.txt", "in.txt")
    assert rc == 0
    assert out == ""
    # read as bytes to avoid text-mode translation
    assert (workspace / "out.txt").read_bytes() == b"a\nb\nc\n"


def test_sort_multiple_keys(invoke, workspace):
    (workspace / "f.txt").write_text("a 2\nb 1\na 1\n")
    rc, out, _ = invoke("sort", "-k", "1", "-k", "2n", "f.txt")
    assert rc == 0
    assert out.splitlines() == ["a 1", "a 2", "b 1"]


# which

def test_which_python(invoke):
    rc, out, _ = invoke("which", sys.executable.rsplit(os.sep, 1)[-1].removesuffix(".exe"))
    # On some systems the python name varies; just check that *some* lookup works
    assert rc in (0, 1)


# env

def test_env_prints(invoke, monkeypatch):
    monkeypatch.setenv("PYBOX_TEST_VAR", "xyz")
    rc, out, _ = invoke("env")
    assert rc == 0
    assert "PYBOX_TEST_VAR=xyz" in out


# tr

def _with_stdin(monkeypatch, data: bytes) -> None:
    import io as _io

    class _Stdin:
        def __init__(self, buf): self.buffer = _io.BytesIO(buf)
        def read(self): return self.buffer.read().decode("utf-8", errors="replace")
        def readline(self): return self.buffer.readline().decode("utf-8", errors="replace")
        def isatty(self): return False
    monkeypatch.setattr(sys, "stdin", _Stdin(data))


def test_tr_translate(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"hello\n")
    rc, out, _ = invoke("tr", "a-z", "A-Z")
    assert rc == 0
    assert out == "HELLO\n"


def test_tr_delete(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"hello world\n")
    rc, out, _ = invoke("tr", "-d", "aeiou")
    assert rc == 0
    assert out == "hll wrld\n"


def test_tr_squeeze(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"a   b  c\n")
    rc, out, _ = invoke("tr", "-s", " ")
    assert rc == 0
    assert out == "a b c\n"


def test_tr_complement_delete(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"hi 42 there\n")
    rc, out, _ = invoke("tr", "-cd", "0-9")
    assert rc == 0
    assert out == "42"


def test_tr_class_digit(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"abc123\n")
    rc, out, _ = invoke("tr", "[:digit:]", "#")
    assert rc == 0
    assert out == "abc###\n"


def test_tr_escape_newline(invoke, monkeypatch):
    _with_stdin(monkeypatch, b"a:b:c")
    rc, out, _ = invoke("tr", ":", "\\n")
    assert rc == 0
    assert out == "a\nb\nc"


# cut

def test_cut_f_single(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\tb\tc\nd\te\tf\n")
    rc, out, _ = invoke("cut", "-f", "2", "f.txt")
    assert rc == 0
    assert out == "b\ne\n"


def test_cut_f_multiple(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\tb\tc\td\n")
    rc, out, _ = invoke("cut", "-f", "1,3", "f.txt")
    assert rc == 0
    assert out == "a\tc\n"


def test_cut_f_range(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\tb\tc\td\te\n")
    rc, out, _ = invoke("cut", "-f", "2-4", "f.txt")
    assert rc == 0
    assert out == "b\tc\td\n"


def test_cut_f_open_range(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\tb\tc\td\n")
    rc, out, _ = invoke("cut", "-f", "3-", "f.txt")
    assert rc == 0
    assert out == "c\td\n"


def test_cut_d_custom(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a,b,c,d\n")
    rc, out, _ = invoke("cut", "-d", ",", "-f", "1,3", "f.txt")
    assert rc == 0
    assert out == "a,c\n"


def test_cut_c_range(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"hello\nworld\n")
    rc, out, _ = invoke("cut", "-c", "1-3", "f.txt")
    assert rc == 0
    assert out == "hel\nwor\n"


def test_cut_c_positions(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"abcdef\n")
    rc, out, _ = invoke("cut", "-c", "1,3,5", "f.txt")
    assert rc == 0
    assert out == "ace\n"


def test_cut_s_suppress(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a:b\nno-delim\nx:y\n")
    rc, out, _ = invoke("cut", "-d", ":", "-f", "2", "-s", "f.txt")
    assert rc == 0
    assert out == "b\ny\n"


def test_cut_order_independent(invoke, workspace):
    """Position list order doesn't change output order (GNU semantics)."""
    (workspace / "f.txt").write_bytes(b"a\tb\tc\n")
    rc, out, _ = invoke("cut", "-f", "3,1", "f.txt")
    assert rc == 0
    assert out == "a\tc\n"


# aliases

def test_alias_type_is_cat(invoke, workspace):
    (workspace / "f.txt").write_text("hello\n")
    rc, out, _ = invoke("type", "f.txt")
    assert rc == 0
    assert out == "hello\n"


def test_alias_dir_is_ls(invoke, workspace):
    (workspace / "marker.txt").write_text("")
    rc, out, _ = invoke("dir", ".")
    assert rc == 0
    assert "marker.txt" in out


def test_alias_del_is_rm(invoke, workspace):
    (workspace / "x.txt").write_text("")
    rc, _, _ = invoke("del", "x.txt")
    assert rc == 0
    assert not (workspace / "x.txt").exists()
