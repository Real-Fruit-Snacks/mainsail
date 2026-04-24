# Security Policy

## Supported Versions

Only the latest released version of mainsail receives security fixes.

| Version  | Supported          |
| -------- | ------------------ |
| latest   | :white_check_mark: |
| < latest | :x:                |

## Reporting a Vulnerability

**Please do not open a public issue for security vulnerabilities.**

If you discover a vulnerability in mainsail, report it privately via:

- **Preferred:** [GitHub Security Advisories](https://github.com/Real-Fruit-Snacks/mainsail/security/advisories/new)
- **Alternative:** Contact the maintainers directly (see profile)

### What to include

- Description of the vulnerability and its impact
- Affected version(s) and platform(s)
- Step-by-step reproduction
- Suggested fix or mitigation, if you have one

### Expected response

- **Acknowledgment:** within 72 hours
- **Initial assessment:** within one week
- **Fix or mitigation plan:** within 30 days for confirmed issues

Once a fix ships, we will publish a security advisory crediting the
reporter (unless anonymity is requested).

## Scope

mainsail is a general-purpose multi-call utility. Most applets shell out
to Python's standard library and don't process untrusted network input,
but a few warrant extra attention when evaluating:

- `tar`, `unzip`: archive extraction with path-traversal protection via
  Python 3.12's `data_filter` and explicit `resolve().relative_to()`
  checks. Report any bypass.
- `find -exec`, `xargs`: invoke user-specified commands — evaluate only
  against adversarial-input-as-path-name scenarios.
- `grep`, `sed`: use the `re` module. Report catastrophic backtracking
  in default flag combinations.
- `ln -s`: requires elevation on Windows; falls back gracefully.

Out of scope: issues that require already-privileged local access, or
bugs purely in the host Python interpreter.
