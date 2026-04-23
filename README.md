# pybox

A cross-platform BusyBox-like multi-call binary written in Python. One executable, many Unix-style utilities — runs natively on Linux, macOS, and Windows.

Unlike BusyBox, pybox isn't trying to fit into 1 MB for embedded systems. The niche is different: a **single-file, hackable, portable toolkit** that gives you consistent Unix utilities everywhere, especially on Windows where they aren't installed by default.

## Install

### Download a release binary (no Python needed)

Grab the binary for your OS from the [Releases page](../../releases):

- `pybox-linux-x64`
- `pybox-macos-arm64`
- `pybox-windows-x64.exe`

Drop it anywhere on your `PATH` and you're done.

### From source

```bash
git clone https://github.com/<you>/pybox
cd pybox
pip install -e .
```

## Usage

Invoke any applet via `pybox <applet> [args]`:

```bash
pybox ls -la
pybox cat file.txt | pybox grep pattern
pybox find . -name '*.py' -type f
pybox --list      # show all applets
pybox --version
```

On Windows you can also use native-sounding aliases:

```cmd
pybox dir .
pybox type file.txt
pybox copy a.txt b.txt
pybox del old.txt
```

### Multi-call mode (optional)

If you hardlink or symlink the binary to the applet names, you can call them directly:

```bash
ln pybox ls
ls -la   # runs the ls applet
```

## Supported applets

| Applet | Aliases | Description |
|--------|---------|-------------|
| `basename` |                | strip directory components from a filename |
| `cat`   | `type`             | concatenate files and print on the standard output |
| `chmod` |                    | change file mode bits (octal or symbolic) |
| `cp`    | `copy`             | copy files and directories |
| `cut`   |                    | remove sections from each line of files |
| `date`  |                    | print or format the date and time |
| `df`    |                    | report filesystem disk space usage |
| `dirname` |                  | strip last component from a path |
| `du`    |                    | estimate file space usage |
| `echo`  |                    | display a line of text |
| `env`   |                    | run a program in a modified environment, or print the environment |
| `false` |                    | do nothing, unsuccessfully (exits 1) |
| `find`  |                    | search for files in a directory hierarchy |
| `grep`  |                    | print lines matching a pattern |
| `head`  |                    | output the first part of files |
| `hostname` |                | show the system's hostname |
| `ln`    |                    | create hard or symbolic links |
| `ls`    | `dir`              | list directory contents |
| `mkdir` | `md`               | make directories |
| `mv`    | `move`, `ren`, `rename` | move (rename) files |
| `printf` |                   | format and print data |
| `pwd`   |                    | print name of current/working directory |
| `realpath` |                | resolve a path to its canonical absolute form |
| `rm`    | `del`, `erase`     | remove files or directories |
| `sed`   |                    | stream editor (s///, d, p, q, =, y, addresses) |
| `seq`   |                    | print a sequence of numbers |
| `sleep` |                    | delay for a specified amount of time |
| `sort`  |                    | sort lines of text files |
| `stat`  |                    | display file or file system status |
| `tail`  |                    | output the last part of files (supports `-f`) |
| `tee`   |                    | read stdin and write to stdout and files |
| `touch` |                    | change file timestamps (create if missing) |
| `tr`    |                    | translate, delete, or squeeze characters |
| `true`  |                    | do nothing, successfully (exits 0) |
| `uname` |                    | print system information |
| `uniq`  |                    | collapse repeated adjacent lines |
| `wc`    |                    | print newline, word, and byte counts for each file |
| `which` | `where`            | locate a command on PATH |
| `whoami` |                   | print effective user name |
| `xargs` |                    | build and execute command lines from standard input |
| `yes`   |                    | output a string repeatedly until killed |

Each applet implements the common POSIX flags — enough for day-to-day scripting, not full GNU coreutils parity.

## Development

```bash
pip install -e ".[dev]"   # install with test deps
pytest -q                 # run test suite
```

Applets live in `pybox/applets/`. Adding a new one means dropping in a module with:

```python
NAME = "myapplet"
ALIASES: list[str] = []
HELP = "one-line description"

def main(argv: list[str]) -> int:
    ...
    return 0
```

Auto-discovery picks it up — no manual registration required.

### Building a standalone binary

```bash
pip install nuitka
python build.py
# → dist/pybox (or dist/pybox.exe on Windows)
```

## License

MIT
