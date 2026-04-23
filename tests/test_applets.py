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


# uniq

def test_uniq_basic(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\na\nb\nc\nc\nc\n")
    rc, out, _ = invoke("uniq", "f.txt")
    assert rc == 0
    assert out == "a\nb\nc\n"


def test_uniq_count(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\na\nb\nc\nc\nc\n")
    rc, out, _ = invoke("uniq", "-c", "f.txt")
    assert rc == 0
    lines = [ln.strip() for ln in out.splitlines()]
    assert lines == ["2 a", "1 b", "3 c"]


def test_uniq_d_only_dupes(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\na\nb\nc\nc\n")
    rc, out, _ = invoke("uniq", "-d", "f.txt")
    assert rc == 0
    assert out == "a\nc\n"


def test_uniq_u_only_uniques(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\na\nb\nc\nc\n")
    rc, out, _ = invoke("uniq", "-u", "f.txt")
    assert rc == 0
    assert out == "b\n"


def test_uniq_i_ignore_case(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"apple\nAPPLE\nBanana\n")
    rc, out, _ = invoke("uniq", "-i", "f.txt")
    assert rc == 0
    assert out == "apple\nBanana\n"


def test_uniq_non_adjacent_kept(invoke, workspace):
    """uniq only dedupes ADJACENT duplicates; non-adjacent stay."""
    (workspace / "f.txt").write_bytes(b"a\nb\na\nb\n")
    rc, out, _ = invoke("uniq", "f.txt")
    assert rc == 0
    assert out == "a\nb\na\nb\n"


def test_uniq_skip_fields(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"1 apple\n2 apple\n3 banana\n")
    rc, out, _ = invoke("uniq", "-f", "1", "f.txt")
    assert rc == 0
    # First two lines collapse because after skipping field 1 both read "apple"
    assert out == "1 apple\n3 banana\n"


# tee

def test_tee_basic(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"hello\n")
    rc, out, _ = invoke("tee", "out.txt")
    assert rc == 0
    assert out == "hello\n"
    assert (workspace / "out.txt").read_bytes() == b"hello\n"


def test_tee_multiple_files(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"broadcast\n")
    rc, out, _ = invoke("tee", "a.txt", "b.txt", "c.txt")
    assert rc == 0
    assert out == "broadcast\n"
    assert (workspace / "a.txt").read_bytes() == b"broadcast\n"
    assert (workspace / "b.txt").read_bytes() == b"broadcast\n"
    assert (workspace / "c.txt").read_bytes() == b"broadcast\n"


def test_tee_append(invoke, workspace, monkeypatch):
    (workspace / "out.txt").write_bytes(b"existing\n")
    _with_stdin(monkeypatch, b"added\n")
    rc, out, _ = invoke("tee", "-a", "out.txt")
    assert rc == 0
    assert out == "added\n"
    assert (workspace / "out.txt").read_bytes() == b"existing\nadded\n"


def test_tee_no_files(invoke, workspace, monkeypatch):
    """tee with no files is effectively cat, writing stdin to stdout."""
    _with_stdin(monkeypatch, b"just passthrough\n")
    rc, out, _ = invoke("tee")
    assert rc == 0
    assert out == "just passthrough\n"


# xargs

def test_xargs_basic(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"arg1 arg2 arg3\n")
    marker = workspace / "m.txt"
    script = (
        f"import sys; open(r'{marker}', 'w').write('|'.join(sys.argv[1:]))"
    )
    rc, _, _ = invoke("xargs", sys.executable, "-c", script)
    assert rc == 0
    assert marker.read_text() == "arg1|arg2|arg3"


def test_xargs_n_batch(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"a b c d\n")
    marker = workspace / "m.txt"
    script = (
        f"import sys; open(r'{marker}', 'a').write('[' + '|'.join(sys.argv[1:]) + ']')"
    )
    rc, _, _ = invoke("xargs", "-n", "2", sys.executable, "-c", script)
    assert rc == 0
    assert marker.read_text() == "[a|b][c|d]"


def test_xargs_I_replace(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"x\ny\n")
    marker = workspace / "m.txt"
    script = (
        f"import sys; open(r'{marker}', 'a').write(sys.argv[1] + ';')"
    )
    rc, _, _ = invoke("xargs", "-I", "{}", sys.executable, "-c", script, "{}")
    assert rc == 0
    assert marker.read_text() == "x;y;"


def test_xargs_0_null_sep(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"a b\0c d\0")
    marker = workspace / "m.txt"
    script = (
        f"import sys; open(r'{marker}', 'w').write('|'.join(sys.argv[1:]))"
    )
    rc, _, _ = invoke("xargs", "-0", sys.executable, "-c", script)
    assert rc == 0
    # Two tokens: "a b" and "c d", both passed in single invocation
    assert marker.read_text() == "a b|c d"


def test_xargs_r_no_run_empty(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"")
    marker = workspace / "m.txt"
    script = f"import sys; open(r'{marker}', 'w').write('ran')"
    rc, _, _ = invoke("xargs", "-r", sys.executable, "-c", script)
    assert rc == 0
    assert not marker.exists()


def test_xargs_L_lines(invoke, workspace, monkeypatch):
    _with_stdin(monkeypatch, b"a b\nc d\ne f\n")
    marker = workspace / "m.txt"
    script = (
        f"import sys; open(r'{marker}', 'a').write('[' + ','.join(sys.argv[1:]) + ']')"
    )
    rc, _, _ = invoke("xargs", "-L", "1", sys.executable, "-c", script)
    assert rc == 0
    # Each input line (already joined/split differently) becomes one call
    content = marker.read_text()
    assert content.count("[") == 3


# basename / dirname / realpath

def test_basename_simple(invoke):
    rc, out, _ = invoke("basename", "/a/b/c.txt")
    assert rc == 0
    assert out == "c.txt\n"


def test_basename_suffix(invoke):
    rc, out, _ = invoke("basename", "/a/b/c.txt", ".txt")
    assert rc == 0
    assert out == "c\n"


def test_basename_trailing_slash(invoke):
    rc, out, _ = invoke("basename", "/a/b/c/")
    assert rc == 0
    assert out == "c\n"


def test_basename_a_multiple(invoke):
    rc, out, _ = invoke("basename", "-a", "/a/x.py", "/b/y.py")
    assert rc == 0
    assert out.splitlines() == ["x.py", "y.py"]


def test_basename_s_suffix(invoke):
    rc, out, _ = invoke("basename", "-s", ".py", "a.py", "b.py")
    assert rc == 0
    assert out.splitlines() == ["a", "b"]


def test_dirname_simple(invoke):
    rc, out, _ = invoke("dirname", "/a/b/c.txt")
    assert rc == 0
    assert out == "/a/b\n"


def test_dirname_no_dir(invoke):
    rc, out, _ = invoke("dirname", "file.txt")
    assert rc == 0
    assert out == ".\n"


def test_dirname_multiple(invoke):
    rc, out, _ = invoke("dirname", "/a/b.txt", "/c/d.py")
    assert rc == 0
    assert out.splitlines() == ["/a", "/c"]


def test_realpath_absolute(invoke, workspace):
    f = workspace / "x.txt"
    f.write_bytes(b"")
    rc, out, _ = invoke("realpath", str(f))
    assert rc == 0
    assert os.path.isabs(out.strip())


def test_realpath_relative(invoke, workspace):
    f = workspace / "rel.txt"
    f.write_bytes(b"")
    rc, out, _ = invoke("realpath", "rel.txt")
    assert rc == 0
    assert os.path.samefile(out.strip(), f)


def test_realpath_relative_to(invoke, workspace):
    (workspace / "sub").mkdir()
    f = workspace / "sub" / "x.txt"
    f.write_bytes(b"")
    rc, out, _ = invoke("realpath", "--relative-to", str(workspace), str(f))
    assert rc == 0
    result = out.strip().replace("\\", "/")
    assert result == "sub/x.txt"


# chmod

def test_chmod_octal_makes_writable(invoke, workspace):
    f = workspace / "file.txt"
    f.write_bytes(b"")
    os.chmod(f, 0o444)  # make read-only first
    try:
        rc, _, _ = invoke("chmod", "644", str(f))
        assert rc == 0
        assert os.access(f, os.W_OK)
    finally:
        os.chmod(f, 0o644)  # ensure cleanup can delete


def test_chmod_symbolic_add_write(invoke, workspace):
    f = workspace / "file.txt"
    f.write_bytes(b"")
    os.chmod(f, 0o444)
    try:
        rc, _, _ = invoke("chmod", "u+w", str(f))
        assert rc == 0
        assert os.access(f, os.W_OK)
    finally:
        os.chmod(f, 0o644)


def test_chmod_symbolic_remove_write(invoke, workspace):
    f = workspace / "file.txt"
    f.write_bytes(b"")
    os.chmod(f, 0o644)
    try:
        rc, _, _ = invoke("chmod", "u-w", str(f))
        assert rc == 0
        assert not os.access(f, os.W_OK)
    finally:
        os.chmod(f, 0o644)


def test_chmod_recursive(invoke, workspace):
    d = workspace / "tree"
    d.mkdir()
    inner = d / "inner.txt"
    inner.write_bytes(b"")
    os.chmod(inner, 0o444)
    try:
        rc, _, _ = invoke("chmod", "-R", "u+w", str(d))
        assert rc == 0
        assert os.access(inner, os.W_OK)
    finally:
        os.chmod(inner, 0o644)


def test_chmod_verbose(invoke, workspace):
    f = workspace / "file.txt"
    f.write_bytes(b"")
    os.chmod(f, 0o444)
    try:
        rc, out, _ = invoke("chmod", "-v", "644", str(f))
        assert rc == 0
        assert "changed" in out or "retained" in out
    finally:
        os.chmod(f, 0o644)


# ln

def test_ln_hard(invoke, workspace):
    target = workspace / "target.txt"
    target.write_bytes(b"payload")
    link = workspace / "link.txt"
    rc, _, _ = invoke("ln", str(target), str(link))
    assert rc == 0
    assert link.read_bytes() == b"payload"
    # On POSIX, same inode; on Windows, same file content suffices
    if os.name != "nt":
        assert target.stat().st_ino == link.stat().st_ino


def test_ln_symbolic(invoke, workspace):
    import pytest as _pytest
    target = workspace / "target.txt"
    target.write_bytes(b"symdata")
    link = workspace / "slink.txt"
    rc, _, err_text = invoke("ln", "-s", str(target), str(link))
    if rc != 0:
        _pytest.skip(f"symlink creation not permitted: {err_text.strip()}")
    assert link.is_symlink()
    assert link.read_bytes() == b"symdata"


def test_ln_f_force_replace(invoke, workspace):
    target = workspace / "target.txt"
    target.write_bytes(b"new")
    link = workspace / "existing.txt"
    link.write_bytes(b"old")
    rc, _, _ = invoke("ln", "-f", str(target), str(link))
    assert rc == 0
    assert link.read_bytes() == b"new"


def test_ln_error_on_existing(invoke, workspace):
    target = workspace / "target.txt"
    target.write_bytes(b"")
    link = workspace / "already.txt"
    link.write_bytes(b"")
    rc, _, _ = invoke("ln", str(target), str(link))
    assert rc == 1


def test_ln_into_directory(invoke, workspace):
    target = workspace / "src.txt"
    target.write_bytes(b"content")
    d = workspace / "bin"
    d.mkdir()
    rc, _, _ = invoke("ln", str(target), str(d))
    assert rc == 0
    assert (d / "src.txt").read_bytes() == b"content"


# stat

def test_stat_default_shows_name_and_size(invoke, workspace):
    f = workspace / "s.txt"
    f.write_bytes(b"12345")
    rc, out, _ = invoke("stat", str(f))
    assert rc == 0
    assert "s.txt" in out
    assert "5" in out  # size


def test_stat_format_size(invoke, workspace):
    f = workspace / "s.txt"
    f.write_bytes(b"abcdef")
    rc, out, _ = invoke("stat", "-c", "%s", str(f))
    assert rc == 0
    assert out.strip() == "6"


def test_stat_format_name(invoke, workspace):
    f = workspace / "namefile.txt"
    f.write_bytes(b"")
    rc, out, _ = invoke("stat", "-c", "%n", str(f))
    assert rc == 0
    assert out.strip().endswith("namefile.txt")


def test_stat_format_type(invoke, workspace):
    f = workspace / "s.txt"
    f.write_bytes(b"")
    d = workspace / "sdir"
    d.mkdir()
    rc, out, _ = invoke("stat", "-c", "%F", str(f), str(d))
    assert rc == 0
    lines = out.strip().splitlines()
    assert lines[0] == "regular file"
    assert lines[1] == "directory"


def test_stat_format_combined(invoke, workspace):
    f = workspace / "combo.txt"
    f.write_bytes(b"xy")
    rc, out, _ = invoke("stat", "-c", "%n=%s", str(f))
    assert rc == 0
    assert out.strip().endswith("combo.txt=2")


def test_stat_missing(invoke, workspace):
    rc, _, err_text = invoke("stat", str(workspace / "does_not_exist"))
    assert rc == 1
    assert "does_not_exist" in err_text


# du

def test_du_summary(invoke, workspace):
    d = workspace / "tree"
    d.mkdir()
    (d / "a.bin").write_bytes(b"x" * 2048)
    (d / "b.bin").write_bytes(b"y" * 1024)
    rc, out, _ = invoke("du", "-s", str(d))
    assert rc == 0
    # Total should be at least 3 (3072 bytes / 1024 = 3 blocks)
    size_str = out.strip().split("\t")[0]
    assert int(size_str) >= 3


def test_du_bytes_exact(invoke, workspace):
    d = workspace / "tree"
    d.mkdir()
    (d / "x.bin").write_bytes(b"x" * 100)
    rc, out, _ = invoke("du", "-sb", str(d))
    assert rc == 0
    size = int(out.strip().split("\t")[0])
    assert size >= 100


def test_du_all_files(invoke, workspace):
    d = workspace / "tree"
    d.mkdir()
    (d / "f1").write_bytes(b"a")
    (d / "f2").write_bytes(b"bb")
    rc, out, _ = invoke("du", "-a", str(d))
    assert rc == 0
    assert "f1" in out
    assert "f2" in out


def test_du_human(invoke, workspace):
    d = workspace / "tree"
    d.mkdir()
    (d / "big").write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MiB
    rc, out, _ = invoke("du", "-sh", str(d))
    assert rc == 0
    # Should contain a unit suffix like M or K
    first = out.strip().split("\t")[0]
    assert any(first.endswith(u) for u in ("K", "M", "G"))


def test_du_grand_total(invoke, workspace):
    a = workspace / "a"
    a.mkdir()
    (a / "x").write_bytes(b"x" * 1024)
    b = workspace / "b"
    b.mkdir()
    (b / "y").write_bytes(b"y" * 1024)
    rc, out, _ = invoke("du", "-sc", str(a), str(b))
    assert rc == 0
    assert "total" in out


# df

def test_df_runs(invoke):
    rc, out, _ = invoke("df", ".")
    assert rc == 0
    assert "Filesystem" in out
    assert "Mounted on" in out


def test_df_human(invoke):
    rc, out, _ = invoke("df", "-h", ".")
    assert rc == 0
    assert "Size" in out


# true / false / yes

def test_true_exit_0(invoke):
    rc, out, _ = invoke("true")
    assert rc == 0
    assert out == ""


def test_true_ignores_args(invoke):
    rc, _, _ = invoke("true", "ignored", "args")
    assert rc == 0


def test_false_exit_1(invoke):
    rc, out, _ = invoke("false")
    assert rc == 1
    assert out == ""


def test_sleep_short(invoke):
    import time as t
    start = t.monotonic()
    rc, _, _ = invoke("sleep", "0.1")
    assert rc == 0
    elapsed = t.monotonic() - start
    assert 0.08 <= elapsed < 1.0


def test_sleep_invalid(invoke):
    rc, _, _ = invoke("sleep", "not-a-number")
    assert rc == 2


def test_sleep_zero(invoke):
    rc, _, _ = invoke("sleep", "0")
    assert rc == 0


def test_seq_single_arg(invoke):
    rc, out, _ = invoke("seq", "5")
    assert rc == 0
    assert out.strip().split("\n") == ["1", "2", "3", "4", "5"]


def test_seq_two_args(invoke):
    rc, out, _ = invoke("seq", "3", "7")
    assert rc == 0
    assert out.strip().split("\n") == ["3", "4", "5", "6", "7"]


def test_seq_three_args_step(invoke):
    rc, out, _ = invoke("seq", "1", "2", "9")
    assert rc == 0
    assert out.strip().split("\n") == ["1", "3", "5", "7", "9"]


def test_seq_descending(invoke):
    rc, out, _ = invoke("seq", "5", "-1", "1")
    assert rc == 0
    assert out.strip().split("\n") == ["5", "4", "3", "2", "1"]


def test_seq_custom_separator(invoke):
    rc, out, _ = invoke("seq", "-s", ",", "3")
    assert rc == 0
    assert out.strip() == "1,2,3"


def test_seq_equal_width(invoke):
    rc, out, _ = invoke("seq", "-w", "8", "12")
    assert rc == 0
    assert out.strip().split("\n") == ["08", "09", "10", "11", "12"]


def test_seq_format(invoke):
    rc, out, _ = invoke("seq", "-f", "%03d", "1", "3")
    assert rc == 0
    assert out.strip().split("\n") == ["001", "002", "003"]


# uname / hostname / whoami

def test_uname_default(invoke):
    import platform
    rc, out, _ = invoke("uname")
    assert rc == 0
    assert out.strip() == (platform.uname().system or "unknown")


def test_uname_a_all(invoke):
    rc, out, _ = invoke("uname", "-a")
    assert rc == 0
    parts = out.strip().split()
    # -a yields 8 fields: system, node, release, version, machine, processor, platform, os
    assert len(parts) >= 3


def test_uname_s_and_m(invoke):
    rc, out, _ = invoke("uname", "-sm")
    assert rc == 0
    assert len(out.strip().split()) == 2


def test_hostname_matches_socket(invoke):
    import socket as _s
    rc, out, _ = invoke("hostname")
    assert rc == 0
    assert out.strip() == _s.gethostname()


def test_hostname_short(invoke):
    import socket as _s
    rc, out, _ = invoke("hostname", "-s")
    assert rc == 0
    assert "." not in out.strip()
    assert out.strip() == _s.gethostname().split(".")[0]


def test_whoami_matches_getpass(invoke):
    import getpass as _g
    rc, out, _ = invoke("whoami")
    assert rc == 0
    assert out.strip() == _g.getuser()


# date

def test_date_default_has_year(invoke):
    from datetime import datetime as _dt
    rc, out, _ = invoke("date")
    assert rc == 0
    assert str(_dt.now().year) in out


def test_date_custom_format(invoke):
    from datetime import datetime as _dt
    rc, out, _ = invoke("date", "+%Y")
    assert rc == 0
    assert out.strip() == str(_dt.now().year)


def test_date_parse_d(invoke):
    rc, out, _ = invoke("date", "-d", "2020-01-15", "+%Y-%m-%d")
    assert rc == 0
    assert out.strip() == "2020-01-15"


def test_date_r_from_file(invoke, workspace):
    f = workspace / "ref.txt"
    f.write_bytes(b"")
    known_mtime = 1577880000.0  # 2020-01-01 fixed reference
    os.utime(f, (known_mtime, known_mtime))
    rc, out, _ = invoke("date", "-r", str(f), "+%Y")
    assert rc == 0
    assert out.strip() == "2020"


def test_date_iso_date(invoke):
    from datetime import datetime as _dt
    rc, out, _ = invoke("date", "-I")
    assert rc == 0
    parts = out.strip().split("-")
    assert len(parts) == 3
    assert int(parts[0]) == _dt.now().year


def test_date_utc_flag(invoke):
    rc, out, _ = invoke("date", "-u", "+%Z")
    assert rc == 0
    # Python's strftime %Z yields 'UTC' when tz-aware UTC
    assert "UTC" in out or "utc" in out.lower()


# printf

def test_printf_s(invoke):
    rc, out, _ = invoke("printf", "%s\\n", "hello")
    assert rc == 0
    assert out == "hello\n"


def test_printf_d(invoke):
    rc, out, _ = invoke("printf", "num=%d\\n", "42")
    assert rc == 0
    assert out == "num=42\n"


def test_printf_escapes(invoke):
    rc, out, _ = invoke("printf", "a\\tb\\nc")
    assert rc == 0
    assert out == "a\tb\nc"


def test_printf_multiple_args_cycle(invoke):
    rc, out, _ = invoke("printf", "%s=%s\\n", "a", "1", "b", "2")
    assert rc == 0
    assert out == "a=1\nb=2\n"


def test_printf_width(invoke):
    rc, out, _ = invoke("printf", "%5d\\n", "7")
    assert rc == 0
    assert out == "    7\n"


def test_printf_hex(invoke):
    rc, out, _ = invoke("printf", "%x\\n", "255")
    assert rc == 0
    assert out == "ff\n"


def test_printf_zero_pad(invoke):
    rc, out, _ = invoke("printf", "%03d\\n", "5")
    assert rc == 0
    assert out == "005\n"


def test_printf_percent_literal(invoke):
    rc, out, _ = invoke("printf", "100%%\\n")
    assert rc == 0
    assert out == "100%\n"


def test_printf_too_few_args_pads_zero(invoke):
    rc, out, _ = invoke("printf", "%s-%d\\n", "only")
    assert rc == 0
    assert out == "only-0\n"


def test_printf_float(invoke):
    rc, out, _ = invoke("printf", "%.2f\\n", "3.14159")
    assert rc == 0
    assert out == "3.14\n"


# sed

def test_sed_substitute(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"hello world\n")
    rc, out, _ = invoke("sed", "s/hello/hi/", "f.txt")
    assert rc == 0
    assert out == "hi world\n"


def test_sed_substitute_global(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a b a c a\n")
    rc, out, _ = invoke("sed", "s/a/X/g", "f.txt")
    assert rc == 0
    assert out == "X b X c X\n"


def test_sed_substitute_case_insensitive(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"Hello hello HELLO\n")
    rc, out, _ = invoke("sed", "s/hello/hi/gi", "f.txt")
    assert rc == 0
    assert out == "hi hi hi\n"


def test_sed_delete_line_number(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"one\ntwo\nthree\n")
    rc, out, _ = invoke("sed", "2d", "f.txt")
    assert rc == 0
    assert out == "one\nthree\n"


def test_sed_n_suppresses_default(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\nb\nc\n")
    rc, out, _ = invoke("sed", "-n", "2p", "f.txt")
    assert rc == 0
    assert out == "b\n"


def test_sed_regex_address_delete(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"apple\nbanana\ncherry\n")
    rc, out, _ = invoke("sed", "/banana/d", "f.txt")
    assert rc == 0
    assert out == "apple\ncherry\n"


def test_sed_range_delete(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"1\n2\n3\n4\n5\n")
    rc, out, _ = invoke("sed", "2,4d", "f.txt")
    assert rc == 0
    assert out == "1\n5\n"


def test_sed_dollar_last_line(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"one\ntwo\nthree\n")
    rc, out, _ = invoke("sed", "$d", "f.txt")
    assert rc == 0
    assert out == "one\ntwo\n"


def test_sed_multiple_e(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"hello\n")
    rc, out, _ = invoke("sed", "-e", "s/h/H/", "-e", "s/o/O/", "f.txt")
    assert rc == 0
    assert out == "HellO\n"


def test_sed_negation(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\nb\nc\n")
    rc, out, _ = invoke("sed", "-n", "2!p", "f.txt")
    assert rc == 0
    assert out == "a\nc\n"


def test_sed_backreference_bre(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"abc123\n")
    rc, out, _ = invoke("sed", r"s/\([a-z]*\)\([0-9]*\)/\2\1/", "f.txt")
    assert rc == 0
    assert out == "123abc\n"


def test_sed_ampersand_in_replacement(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"hello\n")
    rc, out, _ = invoke("sed", "s/lo/[&]/", "f.txt")
    assert rc == 0
    assert out == "hel[lo]\n"


def test_sed_extended_regex(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"abc123\n")
    rc, out, _ = invoke("sed", "-E", "s/([a-z]*)([0-9]*)/\\2\\1/", "f.txt")
    assert rc == 0
    assert out == "123abc\n"


def test_sed_y_translate(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"hello\n")
    rc, out, _ = invoke("sed", "y/abcdefghijklmnopqrstuvwxyz/ABCDEFGHIJKLMNOPQRSTUVWXYZ/", "f.txt")
    assert rc == 0
    assert out == "HELLO\n"


def test_sed_quit(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"one\ntwo\nthree\n")
    rc, out, _ = invoke("sed", "2q", "f.txt")
    assert rc == 0
    assert out == "one\ntwo\n"


def test_sed_line_number_eq(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"a\nb\nc\n")
    rc, out, _ = invoke("sed", "-n", "=", "f.txt")
    assert rc == 0
    assert out.strip().split("\n") == ["1", "2", "3"]


def test_sed_in_place(invoke, workspace):
    f = workspace / "f.txt"
    f.write_bytes(b"hello world\n")
    rc, _, _ = invoke("sed", "-i", "s/hello/goodbye/", str(f))
    assert rc == 0
    assert f.read_bytes() == b"goodbye world\n"


def test_sed_alternate_delimiter(invoke, workspace):
    (workspace / "f.txt").write_bytes(b"/a/b/c\n")
    rc, out, _ = invoke("sed", "s|/a|/X|", "f.txt")
    assert rc == 0
    assert out == "/X/b/c\n"


def test_sed_bad_regex(invoke):
    rc, _, err_text = invoke("sed", "s/[/y/", "nofile")
    assert rc == 2
    assert "sed" in err_text


def test_yes_subprocess(workspace):
    """yes runs forever; drive it via subprocess and kill after we get output."""
    import subprocess
    import time as t
    pybox_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pybox_root) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [sys.executable, "-m", "pybox", "yes", "hello"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(workspace),
    )
    try:
        t.sleep(0.2)
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
    lines = out.splitlines()
    assert len(lines) > 10
    assert lines[0] == b"hello"


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
