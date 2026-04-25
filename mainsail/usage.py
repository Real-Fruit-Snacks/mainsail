"""Per-applet --help text.

Each entry is the body of `mainsail <applet> --help` — it comes after a header
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
    "awk": """\
Usage: awk [-F sep] [-v var=val]... [-f script | 'program'] [file...]

Pattern-scanning and processing language. Each input record (default:
line) is matched against PATTERNs; matching records run the associated
ACTION block. With no file, read stdin.

Options:
  -F SEP            field separator (single char, or regex if multi-char)
  -v var=val        preset a variable before the program runs
  -f FILE           read the program from FILE instead of the command line

Program structure:
  BEGIN { ... }                  run once before reading any input
  /regex/ { action }             run action for records matching regex
  expr { action }                run action for records where expr is true
  pat1, pat2 { action }          range: activate on pat1 through pat2
  END { ... }                    run once after all input is read

Built-in variables:
  NR FNR NF FS OFS ORS RS SUBSEP FILENAME OFMT CONVFMT

Built-in functions:
  length, substr, index, split, sub, gsub, match, toupper, tolower,
  sprintf, int, sqrt, log, exp, sin, cos, atan2, rand, srand, system

Examples:
  awk '{print $2}' data.txt            # second field of each line
  awk -F: '{print $1}' /etc/passwd     # colon-separated fields
  awk '/error/' log.txt                # grep-like filter
  awk '{s+=$1} END{print s/NR}' data   # column mean
  awk '!seen[$0]++' f.txt              # de-duplicate, preserve order

Not implemented: user-defined functions, getline.
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
    # ---- v0.2.0 additions: parity ------------------------------------------
    "tac": """\
Usage: tac [OPTION]... [FILE...]

Concatenate FILE(s) and print in reverse — last line first.

Options:
  -s, --separator=STR   use STR as the record separator (default: newline)
  -b, --before          attach the separator before each record (default after)
  -r, --regex           accepted for compatibility (treated as literal here)
""",
    "rev": """\
Usage: rev [FILE...]

Reverse the characters in every line. Trailing newline (LF or CRLF) is
preserved; only the line content is flipped.
""",
    "nl": """\
Usage: nl [OPTION]... [FILE...]

Number lines of FILE (or stdin), writing the result to stdout.

Options:
  -b, --body-numbering=STYLE   STYLE: a (all), t (non-empty, default), n (none)
  -ba / -bt / -bn              shorthand for the three styles
  -w, --number-width=N         column width for the number (default 6)
  -s, --number-separator=STR   separator after the number (default TAB)
  -v, --starting-line-number=N start counting at N (default 1)
  -i, --line-increment=N       step between numbers (default 1)
""",
    "mktemp": """\
Usage: mktemp [OPTION]... [TEMPLATE]

Create a unique temporary file or directory. TEMPLATE must contain at
least three trailing X's (default tmp.XXXXXXXXXX, in the current dir).

Options:
  -d, --directory       create a directory, not a file
  -u, --dry-run         only output the name; don't create the file
  -q, --quiet           suppress diagnostic messages
  -t                    interpret TEMPLATE relative to $TMPDIR
  -p, --tmpdir[=DIR]    use DIR as the prefix (default $TMPDIR)
""",
    "truncate": """\
Usage: truncate -s SIZE FILE...
       truncate -r REF FILE...

Shrink or extend each FILE to SIZE.

Options:
  -s, --size=SIZE       absolute size, or operator+number:
                        =N (set), +N (grow), -N (shrink), <N (cap),
                        >N (floor), /N (round down to multiple),
                        %N (round up to multiple). Suffixes K, M, G, T, P
                        multiply by 1024.
  -r, --reference=REF   use REF's size as SIZE
  -c, --no-create       don't create FILE if it doesn't exist
""",
    "paste": """\
Usage: paste [-s] [-d LIST] [FILE...]

Merge corresponding lines of files, separated by TAB (default). Treat
'-' as standard input.

Options:
  -d, --delimiters=LIST  cycle through LIST instead of TAB
  -s, --serial           paste one file at a time, not in parallel
""",
    "split": """\
Usage: split [OPTION]... [FILE [PREFIX]]

Split FILE into pieces named PREFIXaa, PREFIXab, … (default PREFIX 'x').
Read stdin if FILE is '-' or absent.

Options:
  -l, --lines=N           N lines per piece (default 1000)
  -b, --bytes=SIZE        SIZE bytes per piece (suffix K/M/G accepted)
  -a, --suffix-length=N   suffix is N letters (default 2)
  -d, --numeric-suffixes  use 00, 01, … instead of aa, ab, …
  --additional-suffix=S   append literal S to each output name
  -NUM                    same as -l NUM
""",
    "cmp": """\
Usage: cmp [OPTION]... FILE1 FILE2 [SKIP1 [SKIP2]]

Compare FILE1 and FILE2 byte by byte. Exit 0 on identical, 1 on
differing, 2 on error.

Options:
  -s, --silent / --quiet  no output; rely on exit code
  -b, --print-bytes       print the differing bytes
  -l, --verbose           print every difference (offset and bytes)
  -n, --bytes=N           compare at most N bytes
  -i SKIP[:SKIP2]         skip the first SKIP bytes of each file
""",
    "comm": """\
Usage: comm [OPTION]... FILE1 FILE2

Compare two SORTED files line by line. Output three columns:
  col 1: lines only in FILE1
  col 2: lines only in FILE2
  col 3: lines in both

Options:
  -1                      suppress column 1
  -2                      suppress column 2
  -3                      suppress column 3
  -12, -13, -23, -123     combine the above
  --check-order /
  --nocheck-order         enable/disable sortedness check
  --output-delimiter=STR  use STR between columns (default TAB)
""",
    "expand": """\
Usage: expand [OPTION]... [FILE...]

Convert TABs to spaces. Default tab stops every 8 columns.

Options:
  -t, --tabs=N         tab stops every N columns
  -t, --tabs=LIST      explicit comma- or space-separated tab stops
  -i, --initial        only convert leading TABs
  -NUM                 shorthand for --tabs=NUM
""",
    "unexpand": """\
Usage: unexpand [OPTION]... [FILE...]

Convert spaces to TABs (default: only leading whitespace).

Options:
  -t, --tabs=N            tab stops every N columns; implies -a
  -t, --tabs=LIST         explicit tab stop positions; implies -a
  -a, --all               convert all whitespace, not just leading
  --first-only            only convert leading whitespace (the default)
""",
    "getopt": """\
Usage: getopt -o SHORT [--long LONG] -- ARG...

POSIX/GNU-style option parser intended to be source-quoted in shell
scripts. Output is shell-quoted via Python's shlex.quote so it is safe
to `eval`.

Options:
  -o, --options=OPTSTR        short-option spec; suffix ':' = required arg,
                              '::' = optional arg
  -l, --long, --longoptions=L comma-separated long options; same suffix rules
  -u, --unquoted              emit unquoted output
  -T, --test                  exit 4 (signal: enhanced getopt available)
  -a, --alternative           accept long options with single '-'
""",
    # ---- v0.2.0 additions: network -----------------------------------------
    "http": """\
Usage: http [OPTION]... URL

Minimal HTTP client built on stdlib urllib. Returns the response body
on stdout; exit code 0 on success, 22 on HTTP >= 400 with --fail.

Options:
  -X, --request=METHOD      HTTP method (default GET, or POST if -d / --json)
  -H, --header='K: V'       add a request header (repeatable)
  -d, --data=DATA           request body literal, or '@file' to read from file
  --json=DATA               JSON body (sets Content-Type: application/json)
  -o, --output=FILE         write body to FILE
  -i, --include             include response headers in stdout
  -I, --head                HEAD-only request
  -L, --location            follow redirects (default)
  --no-location             do not follow redirects
  -s, --silent              suppress error output
  -f, --fail                exit non-zero on HTTP errors
  -A, --user-agent=UA       set User-Agent header
  --timeout=SECS            request timeout (default 30)
""",
    "dig": """\
Usage: dig [@server] [-x ADDR] [TYPE] NAME [+short] [+trace]

Resolve DNS records for NAME. Crafts wire-format queries directly via
stdlib socket — no third-party DNS library required.

Options:
  @server          query the given server (default: /etc/resolv.conf
                   or 1.1.1.1)
  -t, --type TYPE  record type (A, AAAA, MX, TXT, CNAME, NS, SOA, PTR, ANY)
  -x ADDR          reverse lookup the given IPv4 or IPv6 address
  +short           print only the answer values
  +trace           accepted for compatibility (no-op)
  --timeout SECS   per-query timeout (default 5)

The first positional non-option that matches a record type is taken as
the type; any other positional is the name. So `dig MX gmail.com` and
`dig gmail.com MX` both work.
""",
    # ---- v0.2.0 additions: JSON --------------------------------------------
    "jq": """\
Usage: jq [OPTION]... FILTER [FILE...]

Parse FILTER as a jq expression and apply it to JSON input from FILE
(or stdin). Emits zero or more JSON outputs per input.

Output formatting:
  -r, --raw-output       strip outer quotes from string outputs
  -c, --compact-output   single-line JSON, no extra whitespace
  --tab                  indent with TAB instead of two spaces
  -S, --sort-keys        sort object keys in output
  -j                     join: implies -r and skips trailing newlines

Input handling:
  -s, --slurp            read all inputs into one array first
  -n, --null-input       use null as the only input (no stdin/file read)
  -R, --raw-input        treat each input line as a raw string
  -e, --exit-status      non-zero exit if last output is null/false/empty

Supported filter syntax:
  Identity (.), field access (.foo, ."key with space"),
  optional access (.foo?), array index/slice (.[0], .[-1], .[2:5]),
  iteration (.[]), pipes (|), comma (,), alternatives (//),
  parentheses, comparison and arithmetic operators,
  if/then/elif/else/end, object {a:.x} and array [.[] | .y] constructors,
  try-suffix (?).

Built-in functions:
  length, keys, keys_unsorted, values, type, has, in, contains,
  empty, not, select, map, map_values, sort, sort_by, unique,
  unique_by, reverse, first, last, min, max, add, to_entries,
  from_entries, with_entries, paths, leaf_paths, tostring,
  tonumber, ascii, explode, implode, split, join, ltrimstr,
  rtrimstr, startswith, endswith, ascii_downcase, ascii_upcase,
  floor, ceil, sqrt, any, all, isempty.

Not implemented: user-defined functions (def), variable bindings
(as $x), update operators (|=, +=, etc.), recursive descent (..),
format strings (@csv, @json, @sh), regex functions (test, match,
capture, scan, sub, gsub).
""",
    # ---- v0.2.1 additions: more parity + nc -------------------------------
    "dd": """\
Usage: dd [OPERAND]...

Convert and copy a file. Operands are key=value pairs.

  if=FILE       read from FILE (default: stdin)
  of=FILE       write to FILE (default: stdout)
  bs=N          block size in bytes (default 512); suffix K M G T P
  ibs=N / obs=N input/output block size (override bs)
  count=N       copy at most N input blocks
  skip=N        skip N input blocks
  seek=N        seek N output blocks before writing
  conv=LIST     comma-separated: notrunc, sync, fdatasync, fsync,
                lcase, ucase, swab, noerror, excl, nocreat
  status=LEVEL  none, noxfer, progress, default
""",
    "od": """\
Usage: od [OPTION]... [FILE...]

Dump FILE(s) (or stdin) in octal (default) and other formats.

Options:
  -c                       characters with backslash escapes
  -d                       unsigned decimal (1-byte)
  -o                       octal (1-byte)
  -x                       hex (1-byte)
  -A {d,o,x,n}             address radix (n suppresses the address)
  -An / -Ad / -Ao / -Ax    same, attached form
  -j N, --skip-bytes=N     skip N bytes
  -N N, --read-bytes=N     read at most N bytes
  -w N, --width=N          bytes per line (default 16)
  -v                       always show every byte (we never collapse)
""",
    "hexdump": """\
Usage: hexdump [OPTION]... [FILE...]

Default output: 16 bytes per line, grouped as 2-byte little-endian words.

Options:
  -C, --canonical    canonical hex + ASCII layout (most-used)
  -b                 1-byte octal
  -c                 1-byte char (with backslash escapes)
  -d                 2-byte unsigned decimal
  -o                 2-byte octal
  -x                 2-byte hex (default)
  -s, --skip=N       skip N bytes
  -n, --length=N     read at most N bytes
""",
    "diff": """\
Usage: diff [OPTION]... FILE1 FILE2

Compare FILE1 and FILE2 line by line. Default output is a unified diff.

Options:
  -u, --unified[=N]         unified diff with N context lines (default 3)
  -U N                      same, separate-arg form
  -c                        context-diff format
  -y, --side-by-side        ndiff-style line-by-line view
  -q, --brief               only report whether files differ
  -i, --ignore-case         case-insensitive comparison
  -w, --ignore-all-space    treat all whitespace as equivalent
  -B, --ignore-blank-lines  ignore blank-line-only differences
  --strip-trailing-cr       strip CR before comparing

Exit: 0 = identical, 1 = differ, 2 = trouble.
""",
    "join": """\
Usage: join [OPTION]... FILE1 FILE2

Relational join of two files on a common key. Both files must be
sorted on the join field.

Options:
  -1 N             join field of FILE1 (default 1)
  -2 N             join field of FILE2 (default 1)
  -j N             same as -1 N -2 N
  -t CHAR          field separator (default: whitespace)
  -a {1,2}         also print unpaired lines from FILE 1 or 2
  -v {1,2}         only print unpaired lines from FILE 1 or 2
  -e EMPTY         text for missing fields
  -i, --ignore-case  case-insensitive key compare
  -o LIST          output spec: comma-separated FILE.FIELD pairs
""",
    "fmt": """\
Usage: fmt [OPTION]... [FILE...]

Reflow paragraphs to fit within a width. Blank lines separate
paragraphs; whitespace within a paragraph is collapsed.

Options:
  -w N, --width=N            target width in columns (default 75)
  -NUM                       same as -w NUM
  -u, --uniform-spacing      one space between words, two after sentences
  -c, --crown-margin         preserve indent of first/second lines
  -t, --tagged-paragraph     preserve indent of just the first line
  -s, --split-only           split long lines but never join short ones
""",
    "nc": """\
Usage: nc [OPTION]... HOST PORT
       nc -l -p PORT
       nc -z HOST PORT[-PORT]

TCP-only netcat. Bidirectional pipe between stdin/stdout and a TCP
socket; or open a listener; or scan a port range with -z.

Options:
  -l                listen mode (accept first connection then exit)
  -p PORT           port for listen mode
  -z                zero-I/O mode: only check connectivity (port scan)
  -w SECS           connect/recv timeout in seconds
  -v                verbose status to stderr
  -4 / -6           force IPv4 or IPv6
  -u                UDP mode (NOT supported in this build)
""",
}
