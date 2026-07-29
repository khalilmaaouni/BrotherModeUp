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

CORRECTED 2026-07-27 (external audit finding 17). The list below previously named
`threads/registry.json`, `threads/REGISTRY.md`, `threads/.registry.lock` and
`threads/.mode.lock`. Phase 3 deleted `bm_registry.py` and rewrote thread storage
on top of the sqlite store, so no shipped tool writes any of those four files any
more. Verified by grep across `tools/*.py`. Stale security documentation is an
operational risk in its own right, because a reviewer audits the data flow the
document describes rather than the one the code has.

What the code actually writes inside your project today:

- `.brothermode/store.sqlite3` and its `-wal` / `-shm` sidecars: the raw store,
  holding objectives, decisions, digests and directives BEFORE redaction. This is
  the sensitive artefact. It is excluded from git and, as of the audit
  remediation, the tools refuse to run when it is already tracked.
- `threads/thread-mode.json` under your project root.
- Each thread gets `threads/<name>-<id>/STATE.md`, `inbox.md`, `outbox.md` and
  `digest.md`. Everything written there is redacted at the write.
- There are no lock files. Ordering comes from single sqlite transactions, and a
  test forbids importing `fcntl` anywhere in the toolchain.
- `STATE.md` is regenerated from the store on every mutating command (a generated
  view, never hand-edited truth). One honest exception, still open at the time of
  writing: handover delivery APPENDS a block to `STATE.md` outside the store
  transaction (audit finding 12). That is being moved into the store so the view
  is generated rather than appended to. Until it lands, treat `STATE.md` as
  "regenerated, plus one appender", not as purely generated. Each
  thread also gets its own `threads/<name>-<id>/digest.md`, a view of that
  thread's recorded handover. There is no `absorb` command in either CLI
  (confirmed by running `--help` on both, 2026-07-26: `bm_store.py`'s
  commands are adopt, checkpoint, claim, complete, dashboard, decide, dump,
  init, park, resume, verify; `bm_threads.py`'s are adopt, checkpoint,
  complete, dashboard, decide, off, on, park, recommend, resume, send,
  start). An earlier draft of this document named a command that was never
  shipped.
- The V2 store (`tools/bm_store.py`, arriving module by module) writes
  `.brothermode/store.sqlite3` under your project root. That database holds your
  objectives, decisions, digests, and directives AS YOU TYPED THEM: redaction in
  V2 applies at every exit (generated `STATE.md` views, rendered digests,
  dashboard output), while the database itself is the raw, sensitive artifact.
  The learning tables are the one part scrubbed on the way IN as well: every
  field you type into a correction (trigger, action, reason, domain, scope key,
  approval reference, override reason) has secret-shaped substrings masked
  before it is stored, and the count of what was masked is on the candidate.
  Your verbatim capture text and the evidence excerpts taken from it are
  withheld from `dump` entirely and from every `--json` command unless you pass
  `--show-source`.
  As of the 2026-07-29 privacy loop this is no longer special to the learning
  tables. ONE withholding policy now governs every export (`dump`, its JSON
  output, and the MCP server's responses): founder prose is WITHHELD, not
  merely scrubbed, because the scrubber only removes secret SHAPES and
  ordinary sentences carry none. That covers objectives, evidence, digest
  bodies and next intents, transition notes, decision text and directive text.
  Absolute filesystem paths are masked wherever an export does still print
  text, because `/Users/jane.doe/clients/acme` names a person, an employer and
  a client in one string. Masking stops at a space and at a handful of
  characters that end a path in ordinary prose (quotes, backtick, angle
  brackets, pipe, comma, semicolon, colon, and paired brackets and braces),
  so a path containing one of those is masked only up to it; everything else,
  including every non-ASCII name, is covered.
  What an export still shows is structural: identifiers, states, versions,
  hashes, counts, timestamps, plus the record name, tier and claimed path,
  which stay readable so a dump and the fence tools are still usable, and
  which are scrubbed and path-masked on the way out. A session id is shown
  only when it looks like a generated identifier: `--session` is free text, so
  a session id carrying a path, a key or a sentence is withheld like any other
  founder text. `dump --raw` returns everything, prints a warning on standard
  error saying so, and is the only way to get the founder text back out of an
  export.
  The local views you read yourself (`STATE.md`, `digest.md`, `inbox.md`) are
  NOT exports: they carry your real text, scrubbed at the display boundary,
  because they are the product.
  Treat it like the corrections file below. If the database is ever corrupt it
  is renamed to `store.sqlite3.quarantine-<timestamp>` and never deleted, so a
  quarantine file is exactly as sensitive as the store. `bm_store.py init` adds
  `.brothermode/`, `threads/`, and `STATE.md` to your repo's `.git/info/exclude`
  so none of this reaches version control by accident. File permissions are
  owner-only where the platform supports it (on Windows this is best-effort;
  rely on your user profile's access control).

You can verify both claims yourself; the tools are about 32,640 lines of
standard-library Python and shell (re-measured 2026-07-29 after the
correction-learning loops landed; a test fails if this figure drifts more than
15 percent from what the command below returns). Most of that growth is test
code, which is the kind a reader of a security document should want.

It went UP by roughly 2,700 lines on 2026-07-27, and that direction deserves
an explanation rather than a quiet edit. The external security audit of that
day found real escapes at the filesystem boundary, and closing them added one
shared containment funnel plus the adversarial tests that prove each escape
stays closed. Most of the growth is tests, which is the kind a reader of a
security document should want. The small-toolchain claim is still a promise
this project owes: if the non-test line count keeps climbing, the honest move
is to withdraw the claim rather than restate it.

This figure was raised three times in one day, then fell once Phase 3 landed
the same day: the V2 store shipped ALONGSIDE the V1 registry and thread tools
it replaced for a while, and Phase 3 deleted `bm_registry.py` (917 lines) and
rewrote `bm_threads.py` on top of the store instead of its own storage,
cutting `tools/test_bm.py` from 124 tests to the 54 it has today. Roughly a
third of `bm_store.py` is still comment, much of it narrating which fix round
changed what, which belongs in git rather than in the source; a pass to
strip that provenance out of the source remains contracted, not done:

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
  file is created owner-only (0600) on POSIX; on Windows `os.chmod` is
  best-effort and the real control is your user profile. That includes the
  paired fields: the
  previous response excerpt AND the file paths of the tools that ran, because a
  path can carry a secret in a directory name. Redaction is best-effort pattern
  matching, not a guarantee. Treat the file as sensitive, keep it out of version control
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
