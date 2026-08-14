# Install card

Status: CURRENT

One page. Print it or paste it into your team channel. Everybody installs the
same two versions and writes both numbers down.

## The versions everybody runs

| Tool | Version | What it governs |
|---|---|---|
| BrotherMode | `v3.3.0` | one person's session |
| BrotherSBE | `v3.1.0` | one change's passage between people |

They version independently on purpose. Write down both.

BrotherSBE `v3.1.0` was checked against its remote on 2026-08-12 and resolves
to `c48ac46b`, local and remote agreeing. The evidence is
[docs/evidence/tester-pack/CHECKED-2026-08-12.md](../evidence/tester-pack/CHECKED-2026-08-12.md).

BrotherMode `v3.3.0` is cut in the same change as this line, and its SHA is
therefore NOT quoted here: a number written before the tag exists would be a
guess wearing the shape of evidence. Check it yourself with
`git ls-remote --tags origin | grep v3.3.0` before sending this card to
anybody. The number before this one, 3.2.1, exists because a history rewrite
left the `v3.2.0` tag pointing at a commit that was no longer the one setting
VERSION; moving a published tag was rejected, cutting the next number was not.
[docs/plan/DEFECT-tag-version-disagreement-2026-08-12.md](../plan/DEFECT-tag-version-disagreement-2026-08-12.md)
carries that decision.

## Install

Requirements: Claude Code (CLI or desktop) with skills enabled, Python 3.9 or
newer using only the standard library, and git. Nothing to pip install.

**BrotherMode**, two plain shell commands, pasted into any terminal once:

```bash
claude plugin marketplace add khalilmaaouni/BrotherModeUp@v3.3.0
```

```bash
claude plugin install brothermode@brothermode-marketplace
```

**BrotherSBE**, the same two shapes against its own repository:

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE@v3.1.0
```

```bash
claude plugin install brothersbe@brothersbe
```

The `@v3.3.0` and `@v3.1.0` pin each marketplace to a released tag rather than
a moving branch, so everybody gets the same thing. BrotherSBE's own README
still documents the unpinned form; pin it here anyway, because a pilot in
which two people are on different commits of the same tool cannot tell a bug
from a version difference.

The full copy-pasteable walkthrough with the expected output of every command
is [docs/QUICKSTART.md](../QUICKSTART.md). If you are one of this week's
testers, start instead at [TESTER-PACK.md](TESTER-PACK.md), which sequences
both products and tells you what to send back.

## Confirm it worked

Inside a Claude Code session, type `/brothermode:doctor`. It should report all
checks passed. If any check fails, it prints the exact remediation next to the
failure; follow that rather than guessing.

## The three traps, so nobody loses an afternoon

**1. There is no `brothermode` command in your terminal.** If you type it at a
shell prompt you get "command not found". That is correct, not a broken
install. This tool only exists inside a Claude Code session, typed with a
slash. Its sibling is the opposite: `sbe` really is a terminal program.

**2. If you already ran an older major version, uninstall it first.** The
plugin identity changed at v3.0.0, so old and new are different plugins to
Claude Code and installing both wires two hook chains at once.

**3. Check what your shell actually has, not what you installed last.** Run
`which sbe` and confirm the path matches the version you meant to install. A
stale cached copy from an earlier install can sit on your PATH for months
while a newer version exists, and it will be missing commands the
documentation says exist. This is a real failure that was found on a
maintainer's own machine, two major versions behind.

## What to do on day one

Follow [FIRST-DAY.md](FIRST-DAY.md). It is three exercises on a throwaway
repository: one edit, one deliberate conflict, one resume. It takes about
forty minutes and it is the exit test for the first phase.

## Where to write your daily note

[DAILY-NOTE-TEMPLATE.md](DAILY-NOTE-TEMPLATE.md). Two minutes, four lines,
every day you used the tools. It is what the weekly review reads.
