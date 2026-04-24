"""Per-applet --help text.

Each entry is the body of `pybox <applet> --help` — it comes after a header
line like "<applet> - <one-line description>" that the CLI prints.
Keep entries compact: Usage synopsis, Options (indented), optional Examples.
"""
from __future__ import annotations

USAGE: dict[str, str] = {
    # ---- file ops ----------------------------------------------------------
    "ls": """\
Usage: ls [OPTION]... [FILE]...

List information about each FILE (the current directory by default).

Options:
  -a            show entries starting with '.', plus '.' and '..'
  -A            like -a but exclude '.' and '..'
  -l            long listing (mode, links, owner, group, size, mtime, name)
  -F            classify: append '/' to dirs, '*' to executables, '@' to links
  -1            force one entry per line
  -R            list subdirectories recursively
  -S            sort by size, largest first
  -t            sort by modification time, newest first
  -r            reverse the sort order
""",
    "cat": """\
Usage: cat [OPTION]... [FILE]...

Concatenate FILE(s) to standard output (stdin if no FILE or FILE is '-').

Options:
  -n            number every output line (right-justified, tab)
  -b            like -n but skip blank lines (wins over -n)
""",
    "cp": """\
Usage: cp [OPTION]... SOURCE... DEST

Copy SOURCE to DEST, or multiple SOURCEs to the directory DEST.

Options:
  -r, -R        recurse into directories
  -f            force: remove existing targets without prompting
  -i            prompt before overwrite (y/n on stderr)
  -n            never overwrite existing files
  -u            only copy when source is strictly newer than target
  -p            preserve mode, ownership, and timestamps
  -a            archive: implies -r -p
  -v            verbose: print each copy
""",
    "mv": """\
Usage: mv [OPTION]... SOURCE... DEST

Rename SOURCE to DEST, or move multiple SOURCEs to the directory DEST.

Options:
  -f            force: overwrite without prompting
  -i            prompt before overwrite
  -n            never overwrite existing files
  -u            only move when source is strictly newer than target
  -v            verbose: print each move
""",
    "rm": """\
Usage: rm [OPTION]... FILE...

Remove each FILE.

Options:
  -f            ignore missing files, suppress prompts
  -r, -R        remove directories and their contents recursively
  -d            remove empty directories
  -v            verbose: print each removal
""",
    "mkdir": """\
Usage: mkdir [OPTION]... DIR...

Create each DIR, if it does not already exist.

Options:
  -p            create intermediate directories as needed; don't fail if
                target already exists
  -m MODE       set file mode (as in chmod) on created directories
  -v            print a message for each created directory
""",
    "touch": """\
Usage: touch [OPTION]... FILE...

Update access and modification times of each FILE to the current time.
Create each FILE that does not exist.

Options:
  -a            change only the access time
  -m            change only the modification time
  -c            do not create files that do not exist
  -r REF        use REF's timestamps instead of the current time
  -d STR        parse STR as an ISO 8601 date-time and use it
  -t STAMP      use [[CC]YY]MMDDhhmm[.ss] (POSIX format)
""",
    "find": """\
Usage: find [PATH...] [EXPRESSION]

Search for files matching EXPRESSION under each PATH (default: .).

Tests (return true/false):
  -name GLOB         basename matches fnmatch GLOB
  -iname GLOB        basename matches GLOB (case-insensitive)
  -path GLOB         full path matches GLOB
  -ipath GLOB        full path matches GLOB (case-insensitive)
  -type X            X is f (file), d (dir), or l (symlink)
  -size N[cbwkMG]    size compares N units; prefix + for > and - for <
  -mtime N           mtime in days; prefix + for older, - for newer
  -mmin N            mtime in minutes; same prefixes as -mtime
  -atime N, -amin N  access time, same forms
  -ctime N, -cmin N  change time, same forms
  -newer FILE        modified more recently than FILE
  -empty             file is 0 bytes or directory is empty

Actions:
  -print             print path (default if no action)
  -print0            print path, null-terminated
  -delete            remove matching files/empty directories
  -prune             do not descend into matched directories
  -exec CMD ;        run CMD for each match ({} is replaced by path)
  -exec CMD +        batch multiple paths per invocation

Operators: -and / -a, -or / -o, -not / !, parens ( )
Depth:     -maxdepth N, -mindepth N
""",
    "stat": """\
Usage: stat [OPTION]... FILE...

Display file or filesystem status.

Options:
  -c, --format=FMT   print according to FMT (see below)
  -L, --dereference  follow symlinks
  -t, --terse        one space-separated line per FILE

Format placeholders:
  %n  name          %s  size          %a  octal mode    %A  symbolic mode
  %F  type string   %u/%U uid/name    %g/%G gid/name    %h  link count
  %i  inode         %y/%x/%z          mtime/atime/ctime (formatted)
  %Y/%X/%Z          same as above but as epoch seconds
""",
    "chmod": """\
Usage: chmod [OPTION]... MODE FILE...

Change file mode bits.

MODE may be:
  an octal string:  644, 0755, 1777
  a symbolic spec:  [ugoa...][+-=][rwxXst...], comma-separated clauses

Options:
  -R, -r        recurse into directories
  -v            print each file's before/after mode
  -c            like -v but only when mode actually changes
  -f            silent; suppress most errors
""",
    "ln": """\
Usage: ln [OPTION]... TARGET [LINKNAME]
   or: ln [OPTION]... TARGET... DIR

Create a link named LINKNAME (or inside DIR) pointing at TARGET.

Options:
  -s            make symbolic links (default is hard links)
  -r            make symbolic link relative to its directory (implies -s)
  -f            remove existing destination first
  -T            treat LINKNAME as a plain file, never a directory
  -v            print each created link
""",

    # ---- text processing ---------------------------------------------------
    "grep": """\
Usage: grep [OPTION]... PATTERN [FILE...]

Search each FILE (or stdin) for lines matching PATTERN.

Options:
  -i            ignore case
  -v            invert match
  -n            prefix each match with its line number
  -r, -R        recurse into directories
  -F            treat PATTERN as a fixed string, not a regex
  -E            extended regex (default in Python's re module)
  -l            only print names of files with at least one match
  -c            print only a count of matching lines per file
  -o            print only the matching substring
  -w            match only whole words
  -q            quiet: no output, exit 0 if found, 1 otherwise
  -A N          print N lines of context after each match
  -B N          print N lines of context before each match
  -C N          print N lines of context on both sides
""",
    "head": """\
Usage: head [OPTION]... [FILE...]

Print the first lines of each FILE.

Options:
  -n N          print N lines (default 10); use -N as shorthand
  -c N          print N bytes instead of lines
""",
    "tail": """\
Usage: tail [OPTION]... [FILE...]

Print the last lines of each FILE.

Options:
  -n N          print N lines (default 10); use -N as shorthand
  -c N          print N bytes
  -f, -F        follow: wait for new data after initial output
  -s N          sleep N seconds between polls in follow mode (default 1)
""",
    "wc": """\
Usage: wc [OPTION]... [FILE...]

Count newlines, words, and bytes for each FILE.

Options:
  -l            print line count
  -w            print word count
  -c            print byte count
  -m            print character count

With no options, prints lines words bytes.
""",
    "sort": """\
Usage: sort [OPTION]... [FILE...]

Sort lines of FILE(s) or standard input.

Options:
  -r            reverse result
  -n            compare by numeric value (leading number)
  -u            only unique lines
  -f            case-insensitive
  -b            ignore leading blanks
  -k SPEC       sort by fields: N, N,M, Nn (numeric); may repeat for
                composite keys (primary + tiebreakers)
  -t CHAR       field separator (default: runs of whitespace)
  -o FILE       write result to FILE (preserves LF line endings)
""",
    "uniq": """\
Usage: uniq [OPTION]... [INPUT [OUTPUT]]

Collapse repeated adjacent lines.

Options:
  -c            prefix each line with its run count
  -d            only print lines that have duplicates in their run
  -u            only print lines that appear exactly once
  -i            case-insensitive comparison
  -f N          skip N whitespace-separated fields before comparing
  -s N          skip N characters (after -f) before comparing
  -w N          compare at most N characters of the key
""",
    "cut": """\
Usage: cut OPTION... [FILE...]

Extract sections from each line of FILE(s).

Options (must specify -f or -c):
  -f LIST       fields (separated by DELIM, default tab)
  -c LIST       character positions (1-based)
  -d CHAR       set field delimiter (for -f)
  -s            suppress lines without the delimiter (-f only)

LIST syntax: N, N-, -N, N-M, combinations joined with comma.
""",
    "tr": """\
Usage: tr [OPTION]... SET1 [SET2]

Translate, delete, or squeeze characters from stdin.

Options:
  -d            delete characters in SET1
  -s            squeeze runs of characters in SET1 (or SET2 with -d)
  -c            complement SET1 (applies to -d / -s / translate)
  -t            truncate SET1 to length of SET2

Set syntax: ranges (a-z), character classes ([:alpha:] [:digit:] ...),
backslash escapes (\\n \\t \\\\ \\0).

Examples:
  tr a-z A-Z           uppercase
  tr -d '\\r'            strip carriage returns
  tr -cd '[:alnum:]'    keep only alphanumeric
""",
    "sed": """\
Usage: sed [OPTION]... SCRIPT [FILE...]

Stream editor: apply SCRIPT to each line of FILE (or stdin).

Options:
  -n                    suppress automatic pattern-space output
  -e SCRIPT             add SCRIPT (may be repeated; concatenated)
  -f FILE               read SCRIPT from FILE
  -i                    edit each input file in place
  -E, -r                extended regex (default is BRE)

Commands supported:
  s/PAT/REPL/FLAGS      substitution (flags: g global, i/I case, p print)
  d                     delete pattern space
  p                     print pattern space
  q                     quit (prints line unless -n)
  =                     print current line number
  y/SRC/DST/            transliterate char-by-char

Addresses: N, $, /regex/, ranges (N,M / N,/R/), trailing ! negates.
""",
    "tee": """\
Usage: tee [OPTION]... [FILE...]

Copy stdin to stdout and to each FILE.

Options:
  -a            append to FILEs instead of overwriting
  -i            ignore SIGINT (no-op on platforms without signal support)
""",
    "xargs": """\
Usage: xargs [OPTION]... [COMMAND [ARG...]]

Build command lines from stdin and run COMMAND (default: echo).

Options:
  -n N          pass at most N args per invocation
  -L N          read N input lines per invocation
  -I STR        substitute STR with each token; one invocation per token
  -0, --null    null-separated input (disables quote handling)
  -d CHAR       custom single-char delimiter
  -a FILE       read input from FILE instead of stdin
  -r            do not run if input is empty
  -t            print each invocation to stderr before running

Default tokenizer handles ' ', \", and \\ quoting like a POSIX shell.
""",

    # ---- path helpers ------------------------------------------------------
    "basename": """\
Usage: basename NAME [SUFFIX]
   or: basename OPTION... NAME...

Strip directory components from NAME; optionally strip trailing SUFFIX.

Options:
  -a, --multiple    treat every operand as a path
  -s, --suffix=SUF  shared suffix to strip from every operand; implies -a
  -z, --zero        null-terminate each output
""",
    "dirname": """\
Usage: dirname [OPTION]... NAME...

Strip the final component from each NAME.

Options:
  -z, --zero        null-terminate each output
""",
    "realpath": """\
Usage: realpath [OPTION]... FILE...

Canonicalize each FILE to an absolute path (following symlinks by default).

Options:
  -e, --canonicalize-existing   require the target to exist
  -m, --canonicalize-missing    allow nonexistent components (default)
  -s, -L, --no-symlinks         do not resolve symlinks
  -z, --zero                    null-terminate each output
  --relative-to=DIR             print result relative to DIR
""",
    "pwd": """\
Usage: pwd [OPTION]

Print the current working directory.

Options:
  -L            logical (use PWD if it still matches cwd; default)
  -P            physical (resolve symlinks)
""",
    "which": """\
Usage: which [OPTION]... COMMAND...

Locate COMMAND(s) on PATH; on Windows also tries PATHEXT suffixes.

Options:
  -a            print all matches, not just the first
""",

    # ---- system / time -----------------------------------------------------
    "uname": """\
Usage: uname [OPTION]...

Print system information.

Options:
  -s            kernel name (default)
  -n            network node hostname
  -r            kernel release
  -v            kernel version
  -m            machine hardware name
  -p            processor type
  -i            hardware platform
  -o            operating system
  -a            all of the above

Long options mirror the short ones (--kernel-name, --all, etc.).
""",
    "hostname": """\
Usage: hostname [OPTION]

Display the system's hostname (does not set it).

Options:
  -s, --short       short hostname (before the first '.')
  -f, --fqdn, --long   fully qualified domain name
  -I                IP addresses resolved from the hostname
""",
    "whoami": """\
Usage: whoami

Print the effective user name.
""",
    "date": """\
Usage: date [OPTION]... [+FORMAT]

Display the current date/time (or a specified date) in FORMAT.

Options:
  -u, --utc                     use UTC
  -d STR, --date=STR            parse STR (ISO 8601 variants)
  -r FILE, --reference=FILE     use FILE's modification time
  -R, --rfc-2822                RFC 2822 email format
  -I[SPEC]                      ISO 8601 format
                                (SPEC: date, hours, minutes, seconds, ns)

FORMAT uses strftime conversions (%Y, %m, %d, %H, %M, %S, ...).
""",
    "env": """\
Usage: env [OPTION]... [NAME=VALUE]... [COMMAND [ARG...]]

With no COMMAND: print the current environment. Otherwise run COMMAND
in a modified environment.

Options:
  -i, --ignore-environment   start with an empty environment
  -u NAME, --unset=NAME      remove NAME from the environment
""",
    "sleep": """\
Usage: sleep NUMBER[smhd]...

Pause for the total of each NUMBER with optional suffix:
  s   seconds (default)      m   minutes
  h   hours                   d   days

Multiple operands are summed.
""",

    # ---- control / simple --------------------------------------------------
    "true": """\
Usage: true [ANY...]

Exit 0, ignoring all arguments.
""",
    "false": """\
Usage: false [ANY...]

Exit 1, ignoring all arguments.
""",
    "yes": """\
Usage: yes [STRING...]

Repeatedly output STRING (default 'y') until killed.
""",
    "seq": """\
Usage: seq [OPTION]... LAST
   or: seq [OPTION]... FIRST LAST
   or: seq [OPTION]... FIRST INCR LAST

Print numbers from FIRST to LAST, stepping by INCR (default 1).

Options:
  -s SEP           separator between values (default: newline)
  -f FMT           printf-style format applied to each value
  -w, --equal-width zero-pad to the widest value's width
""",
    "echo": """\
Usage: echo [-neE] [STRING...]

Print each STRING separated by spaces, followed by a newline.

Options:
  -n            do not output the trailing newline
  -e            enable backslash escapes (\\n, \\t, \\\\, ...)
  -E            disable backslash escapes (default)
""",
    "printf": """\
Usage: printf FORMAT [ARG...]

Print ARG(s) according to FORMAT. FORMAT is reapplied when ARGs remain.

Specifiers: %s %d %i %o %u %x %X %e %E %f %g %G %c %b %%
Flags: - + # space 0 ; width and .precision permitted as usual.
Escapes: \\n \\t \\r \\\\ \\a \\b \\f \\v \\0 \\' \\\"
%b interprets escape sequences inside the corresponding ARG.
""",

    # ---- archives / compression --------------------------------------------
    "tar": """\
Usage: tar OPERATION [OPTION]... [FILE...]

Create, extract, or list tar archives. Supports traditional (tar cvfz ...)
and dashed (-cvfz) syntax; bundled flag letters work either way.

Operations (pick one):
  -c, --create      create archive
  -x, --extract     extract from archive
  -t, --list        list contents

Options:
  -f FILE           archive file (use '-' for stdin/stdout)
  -v                verbose progress
  -C DIR            change to DIR before operation
  -z, -j, -J        gzip, bzip2, xz compression
  --exclude PAT     skip names matching PAT (may repeat)
""",
    "gzip": """\
Usage: gzip [OPTION]... [FILE...]

Compress each FILE (adding .gz) or decompress with -d.

Options:
  -d, --decompress    decompress (same as gunzip)
  -c, --stdout        write to stdout, keep the original
  -k, --keep          keep the original after operation
  -f, --force         overwrite existing .gz / source
  -t, --test          check archive integrity
  -1..-9              compression level (default 6)

With no FILE or '-', reads stdin and writes stdout.
""",
    "gunzip": """\
Usage: gunzip [OPTION]... [FILE...]

Decompress .gz files. Accepts the same options as gzip -d.
""",
    "zip": """\
Usage: zip [OPTION]... ARCHIVE [FILE...]

Package FILEs into ARCHIVE (.zip).

Options:
  -r                recurse into directories
  -j                junk paths (store only basenames)
  -g                append to an existing archive
  -d                delete named entries from ARCHIVE
  -0..-9            compression level (0 = stored, else deflated)
""",
    "unzip": """\
Usage: unzip [OPTION]... ARCHIVE [FILE...]

Extract (or list) entries in ARCHIVE.

Options:
  -d DIR            extract to DIR (default: current directory)
  -l                list archive contents
  -p                print entries to stdout (pipe mode)
  -o                overwrite without prompting
  -n                never overwrite
  -q, -qq           quiet
""",

    # ---- disk usage --------------------------------------------------------
    "du": """\
Usage: du [OPTION]... [PATH...]

Estimate disk usage of each PATH (default: .).

Options:
  -s            summary: one total per operand
  -a            include individual files
  -h            human-readable sizes (K/M/G/T/P)
  -b            exact byte counts
  -c            print grand total at end
  -k            1024-byte blocks (default)
  -m            1 MiB blocks
  --max-depth=N limit output depth
""",
    "df": """\
Usage: df [OPTION]... [PATH...]

Report filesystem usage for the volume containing each PATH (default: .).

Options:
  -h            human-readable sizes
  -k            1024-byte blocks (default)
  -m            1 MiB blocks
""",

    # ---- hashing -----------------------------------------------------------
    "md5sum": """\
Usage: md5sum [OPTION]... [FILE...]

Print or check MD5 message digests.

Options:
  -b, --binary        output with '*' separator (binary mode)
  -t, --text          output with ' ' separator (default)
  -c, --check         verify digests in each FILE
  --tag               BSD-style output: 'MD5 (FILE) = HEX'
  -z, --zero          null-terminate each line
  --quiet             suppress 'OK' lines in check mode
  --status            suppress all normal output; exit code only
  -w, --warn          warn on malformed check lines
  --strict            fail on any malformed check line
""",
    "sha1sum": """\
Usage: sha1sum [OPTION]... [FILE...]

Print or check SHA-1 digests. Same options as md5sum; tag label is SHA1.
""",
    "sha256sum": """\
Usage: sha256sum [OPTION]... [FILE...]

Print or check SHA-256 digests. Same options as md5sum; tag label is SHA256.
""",
    "sha512sum": """\
Usage: sha512sum [OPTION]... [FILE...]

Print or check SHA-512 digests. Same options as md5sum; tag label is SHA512.
""",
}
