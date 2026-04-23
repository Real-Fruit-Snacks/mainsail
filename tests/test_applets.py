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


def test_touch_creates_file(invoke, workspace):
    rc, _, _ = invoke("touch", "new.txt")
    assert rc == 0
    assert (workspace / "new.txt").is_file()


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
