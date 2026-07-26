# Security

## Reporting a vulnerability

Open a GitHub issue describing the problem and how to reproduce it. If the issue
would expose someone's data by being public, say so in one line without the
details and ask for a private channel first.

## What this software does with your data

BrotherMode makes no network calls. It has no analytics, no account, and no
server. Most of what it writes goes to your vault folder, which you choose with
`BROTHERMODE_VAULT` (default `~/BrotherModeVault`). The work registry is the
exception: it writes inside your project directory, not the vault, so you can
find it there too:

- `threads/registry.json`, `threads/REGISTRY.md`, `threads/.registry.lock`, and
  `threads/thread-mode.json` live under your project root.
- Each thread also gets `threads/<name>/STATE.md`, `inbox.md`, `outbox.md`, and
  `digest.md`, plus a `threads/.mode.lock`. Everything written there is redacted
  at the write, the same as everything else.
- `absorb` appends a handover section to your project's `STATE.md`.
- The V2 store (`tools/bm_store.py`, arriving module by module) writes
  `.brothermode/store.sqlite3` under your project root. That database holds your
  objectives, decisions, digests, and directives AS YOU TYPED THEM: redaction in
  V2 applies at every exit (generated `STATE.md` views, rendered digests,
  dashboard output), while the database itself is the raw, sensitive artifact.
  Treat it like the corrections file below. If the database is ever corrupt it
  is renamed to `store.sqlite3.quarantine-<timestamp>` and never deleted, so a
  quarantine file is exactly as sensitive as the store. `bm_store.py init` adds
  `.brothermode/`, `threads/`, and `STATE.md` to your repo's `.git/info/exclude`
  so none of this reaches version control by accident. File permissions are
  owner-only where the platform supports it (on Windows this is best-effort;
  rely on your user profile's access control).

You can verify both claims yourself; the tools are about 12,400 lines of
standard-library Python and shell (measured 2026-07-26; a test fails if this
figure drifts more than 15 percent from what the command below returns).

This figure has been raised three times in one day, which is itself worth
stating plainly rather than hiding in a number. Two reasons, one legitimate and
one not: the V2 store currently ships ALONGSIDE the V1 registry and thread tools
it replaces (Phase 3 removes about 1,668 lines of those), and roughly a third of
the new store file is comment, much of it narrating which fix round changed what,
which belongs in git rather than in the source. A pass to strip that provenance
is contracted. If this number is not falling by the close of Phase 3, the growth
is real and the claim that this is a small auditable toolchain should be
withdrawn rather than restated:

```bash
find tools -type f \( -name "*.py" -o -name "*.sh" \) | xargs wc -l
grep -rnE "urllib|requests|socket|http|curl|wget|subprocess" tools/
```

Two files inside the vault deserve attention:

- `99-System/telemetry/outcomes.jsonl` holds per-session counts (tokens, tool
  calls, duration) plus the basename of the working directory. No file contents,
  no prompts.
- `99-System/telemetry/corrections.jsonl` holds short excerpts **of your own
  messages** that look like corrections, so the weekly review can turn them into
  rules. Secret-shaped substrings (API keys, tokens, `password=`, private keys,
  national-ID and card shapes) are redacted before anything is written, and the
  file is created owner-only (0600). Redaction is best-effort pattern matching,
  not a guarantee. Treat the file as sensitive, keep it out of version control
  (the shipped `vault-template/.gitignore` excludes it), and purge it whenever
  you like:

```bash
python3 tools/bm_telemetry.py purge-corrections        # shows what is there
python3 tools/bm_telemetry.py purge-corrections --yes  # deletes it
```

To disable correction capture entirely, remove the `SessionEnd` hook. You lose
the automatic capture half of the learning loop; everything else keeps working.

## The autosave makes no network call either

`tools/bm_autosave.py` runs on the PreCompact hook (right before Claude Code
compacts context, which is what happens when you run low on tokens). It snapshots
your tracked and untracked working-tree files into a private git ref namespaced per
worktree and per session, using a throwaway index so your real branch, index, and
working tree are never touched. Ignored files and uncommitted content inside nested
repositories or submodules are NOT captured, so this is not literally your entire
disk state; it is your working tree as git sees it.

This module is the ONE documented exception to the no-subprocess rule above,
because git is an external binary and there is no way to drive it otherwise. Every
call it makes is local: never push, fetch, pull, clone, or remote, and a test
enforces both halves (the named per-file exception, and the ban on any git command
that reaches a remote). The zero-network property holds with autosave enabled.

Recover a snapshot into a SEPARATE worktree, never over your live files:

```bash
python3 tools/bm_autosave.py recover
```

The previous shell version restored in place, which was measured to delete a
tracked file that had been excluded from the snapshot. That path is gone.

An optional continuous mode (`bm_autosave.py tick`, off unless you set
`BROTHERMODE_AUTOSAVE`) also snapshots every N tool calls, for a crash that is not
a compaction. To disable autosave entirely, remove the PreCompact hook.

## The update check makes no network call

`tools/bm_telemetry.py check-update` runs at session start and tells you when your
installed copy differs from an already-fetched origin, when it has gone stale, and
once when the law itself changed under you. It does this by reading git ref files
directly. It never runs `git`, never opens a socket, and never contacts a server, so
the zero-network property above still holds with the check enabled. The cost of that
choice: it can only see an update that something else already fetched, which is why
it also warns when your copy is simply old.

To disable it, remove the `check-update` line from `tools/bm_sessionstart.sh`.

## Scope note

This project governs how a Claude Code session behaves. It does not change what
Claude Code itself transmits to Anthropic or your chosen cloud provider. For
that, see Anthropic's own documentation on Claude Code data usage, and choose
your plan accordingly: commercial terms (Team, Enterprise, API, cloud providers)
differ materially from consumer plans.

## Verifying what you installed

This repository is unsigned and has no releases. If your organization requires
pinning, clone at a specific commit and record the hash:

```bash
git -C ~/.claude/skills/brothermode rev-parse HEAD
```
