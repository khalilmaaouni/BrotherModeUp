# Security

## Reporting a vulnerability

Open a GitHub issue describing the problem and how to reproduce it. If the issue
would expose someone's data by being public, say so in one line without the
details and ask for a private channel first.

## What this software does with your data

BrotherMode's hooks and tools make no network calls when running on their own.
It has no analytics, no account, and no server. CORRECTED 2026-08-01: the
sentence above used to say flatly "makes no network calls", and that stopped
being fully precise the day /brotherme-update shipped: that command, and only
that command, runs `git ls-remote` against the public repository to compare
your installed version with the newest release tag, only when you invoke it,
sending nothing but the standard git query. Nothing that runs automatically
(hooks, gates, the store, the docs engine) reaches the network, ever. Most of what it writes goes to your vault folder, which you choose with
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

You can verify both claims yourself; the tools are about 108,900 lines of
standard-library Python and shell (re-measured 2026-08-05 after the Full-Auto
controller landed; the figure of 76,224 from earlier the same day drifted past
the 15 percent guard the test enforces, so it is corrected here rather than
restated, which is the third such correction and is exactly the pattern the
promise below is about). Most of that growth is test code, which is the kind
a reader of a security document should want: of the roughly 14,900 lines the
controller added, about 4,400 are the engine and its command line and the rest
are behavioral tests, including the tests that six adversarial refutation
rounds produced. Those rounds are why the number moved twice in one day: each
one reproduced a defect with a probe, and each reproduction became a permanent
test rather than a note. Four shipping tools import subprocess, each for LOCAL execution: bm_autosave.py drives git (never a push, never a remote), bm_controller.py (the Full-Auto controller) runs each unit's deterministic done-check as a local command, bm_continue.py starts the successor session as one detached local `claude -p` process whose output goes to a local log file, and brothermode_cli.py (the v3 public boundary) dispatches its eleven verbs to the existing local tools, with one stated network exception: its update check runs a single read-only `git ls-remote --tags` against the configured remote, a network READ that writes nothing and pushes nothing. All four are named exceptions in the no-network test, per file and per module, so no fifth tool inherits the allowance quietly.

The small-toolchain promise still stands: if the
NON-test line count starts climbing like this, the honest move is to withdraw
the claim, not keep restating a larger number.

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

## The page that shows where your project stands, and what publishing it means

Added 2026-08-05 with the live project view, and disclosed here because it is the
one artefact of this product that can leave your machine on purpose.

`bm-view render` writes `PROJECT-VIEW.html` at the top of your project folder,
and `bm-view brief-page` writes a page under `Handover/` for whoever picks up a
decision you took back. Both are ordinary files, written through the same one
write funnel as every other generated view, gated on the same consent record as
everything else: before setup, `bm-view` writes nothing, creates no folder and
publishes nothing. Both are generated from your project's own records, so what
they contain is what those records contain: your outcome in your own words, the
decisions and what was weighed, what has been learned and what would change it,
the checks and their results, spend against your ceilings, the recorded ids
behind each claim, and the file paths inside your project that the work touched.
They are subject to the same redaction rules as every other generated view, and
they carry no tokens, no receipts and no contents of any file outside what a
record holds. Read one before you send it anywhere, exactly as you would the
handover pages.

The page makes no network call. Nothing in it is fetched when it opens: no
fonts, no images, no scripts, no addresses of any kind, so it renders with the
machine offline, and there is no request that could carry anything anywhere.

Publishing is a separate act, and it is Claude's, not this toolchain's. No
command here can publish: publishing happens when Claude takes the file you
already have and puts it at a private address on claude.ai that only you and
anyone you deliberately share it with can open. Two things about that are worth
knowing before you agree to the first one. You are asked once, by Claude's own
permission prompt, and publishing that same page again afterwards does not ask
again, so after your first yes the page updates silently, which is the behaviour
you want and also the reason it is written here rather than left to be
discovered. And publishing can be unavailable to you entirely, for reasons that
have nothing to do with this product: the conditions are listed in
`docs/KNOWN-LIMITS.md`. Either way the file on disk is the primary artefact. It
is what the command promises, it is what is committed and diffed, and the
published copy is a convenience laid on top of it.

## Approval and state-change receipts are secrets

Added 2026-07-31, closing the open half of `docs/NOT-FINALIZED.md` item 21. The
code enforced these rules before this section existed; a reader had no way to
learn them from the security page.

A receipt authorises exactly one rule-changing act: approving a candidate into a
rule, editing an approved rule's injectable text, or a state change (supersede,
deprecate, forget, resolve-conflict, and resolving a critical alert). What the
code enforces:

- **Shown once, at mint time, and never again.** `grant-approval` and
  `grant-state-receipt` print the token; there is deliberately no command that
  reads a token back out of the store.
- **Never stored.** Only `sha256` of the token under a domain prefix is kept, and
  the mint path pops that column out of the record it returns, so a caller
  printing the whole record cannot print it either.
- **Withheld from every ordinary export** by the same name-shape policy that
  withholds every other digest column, so `dump` and the MCP surfaces never
  carry it.
- **Fifteen-minute life**, clamped in code, and single use: consumption is a
  conditional `UPDATE ... WHERE consumed_at IS NULL AND expires_at >= ?` in the
  same transaction as the change it authorises, so two racing spends cannot both
  win.
- **Bound to the exact proposed change.** The fingerprint covers rule text,
  scope, severity and any override in play, so a receipt minted for one proposal
  cannot be spent on another, and receipts of one kind cannot spend as another.

**What a receipt does NOT prove.** It proves an answer was supplied for this
exact proposed change and has not already been used. It does NOT prove which
human supplied it. Anything able to run the CLI as the same operating-system user
can mint one by asking, then spend it. The guarantee is "no rule changed without
a fresh, specific, one-time human answer", not "the founder personally authorised
this". Treat a leaked token as a short-lived capability: spendable by whoever
holds it until used or expired.

## Threat model (D-2, Loop 6 security closure)

Added 2026-08-01. Everything above describes what the code does; this section
states, in one place, what it is defending, from whom, and what it openly
does not defend against. Plain words: an "asset" below just means "a file or
value worth protecting", and a "trust boundary" means "the line past which
this project stops being able to promise anything".

**Assets** (the things worth protecting):

- **The store** (`.brothermode/store.sqlite3`): your objectives, decisions,
  digests, directives, alerts and (in the canonical protocol tables) your
  projects, tasks and forecasts, in the clear. The single most sensitive file
  this project writes.
- **The vault** (`BROTHERMODE_VAULT`, default `~/BrotherModeVault`): session
  telemetry and captured corrections, both described above.
- **The consent config** (`~/.brotherme/config.json`): records that setup
  ran and where your vault lives. Not secret by itself, but every hook
  PROGRAM that writes YOUR CONTENT refuses to write anything until this
  file says you said yes, so it is the switch that gates your data leaving
  a session. Read "program" strictly: one hook line can run more than one
  program (PreCompact runs two), and each one carries its own check. The
  gated set is `bm_sessionstart.sh`, `bm_autosave.py`, the Bash audit's
  two phases, all three hook-wired `bm_telemetry.py` commands
  (`outcomes-append`, `precompact-brief`, `stop-warn`), and
  `bm_lead.py watchdog`. A test reads `hooks/hooks.json` and fails if a
  wired command lacks the check, and since 2026-08-05 that test reads
  every module named on a hook line rather than `bm_telemetry.py` alone,
  which is the widening the incident at the end of this entry argues for.
  THE WATCHDOG, added 2026-08-05 and disclosed here because it ships ON BY
  DEFAULT: it is the half-hour catch-up, and it is a due check rather than
  a background process. Nothing schedules it and nothing runs between your
  turns; it runs on the Stop hook, once per model turn, alongside the
  telemetry warning already on that line. Its first statement reads the
  consent record, so before setup has been run it prints nothing and
  writes nothing at all, in the same one-door sense as the programs above.
  After consent it reads a few rows to ask whether a catch-up is due. When
  the answer is no, which is the ordinary case, it writes nothing and
  prints nothing. When the answer is yes it writes exactly one row into
  your own project store, the record of the catch-up you were shown, and
  prints that catch-up. It writes nothing into the vault, nothing outside
  your project, and it makes no network call.
  One narrow exception, named so this claim stays true: the fence hook
  does not check consent, and on first use it mints its own session token
  file (a machine-generated 64-hex value, no founder data) under
  `.brothermode/fence/`, because ownership proof has to exist before the
  hook can refuse anyone. It writes nothing else.
  HISTORY, dated because the claim above was FALSE until 2026-08-02: two
  of those `bm_telemetry.py` commands were ungated. `precompact-brief`
  wrote your last message verbatim into the vault, and `stop-warn` created
  the vault tree, both before anyone had said yes. Found by an independent
  adversarial review, reproduced in a throwaway home directory, fixed, and
  pinned by tests in `tools/test_bm_consent.py`. The sentence was wrong for
  the same reason it was easy to believe: the earlier fix gated the first
  program on a hook line and nobody checked the second.
- **Your Claude Code `settings.json`**: what `scripts/install.py` edits to
  wire the hooks. If an attacker could rewrite it, they could point a hook
  command anywhere.
- **Generated views** (`STATE.md`, `digest.md`, `inbox.md`, `outbox.md`, and
  every document `bm_docs.py` or `bm_project.py` renders): read-only
  reflections of the store, scrubbed at the point they are written, so they
  are lower sensitivity than the store itself but not zero.

**Trust boundaries** (who is on which side of the line):

- **Hooks run as you, the logged-in user, with your full filesystem
  permissions.** They are not sandboxed and do not run as a separate,
  lower-privileged account. Anything you could type at your own terminal, a
  hook you installed could also do.
- **Subagents and parallel Claude Code sessions share the same working
  tree.** BrotherMode's fence is a coordination discipline between
  cooperating sessions, not a permission boundary between a trusted and an
  untrusted one: every session that can reach the project directory can, in
  principle, reach every file in it.
- **The MCP server this project can expose is read-only.** It answers
  queries against the store; it has no path that writes, so a client
  talking to it cannot use it to mutate your project even if it wanted to.

**Attacks this design answers:**

- **A second Edit, Write, MultiEdit or NotebookEdit crossing a fence, and
  since L06 (2026-08-06) a Bash apply_patch envelope naming a fenced path.**
  Blocked, in front of the write, by `tools/bm_fence_hook.py` (a PreToolUse
  hook that can refuse the call before it happens; see docs/HOOKS.md) --
  CORRECTED 2026-08-01 (loop6 refuter finding A8a): that "Blocked" is not
  unconditional. The hook FAILS OPEN (lets the write through unchecked) on
  a missing, empty or corrupt store, or on any internal error, exactly as
  docs/KNOWN-LIMITS.md already states; treat this line as "blocked when the
  store is readable", not as an unqualified guarantee.
- **The same kind of cross-fence write, but through Bash.** The fence hook
  cannot see inside a shell command, so this one cannot be blocked (see
  "The Bash boundary" in docs/HOOKS.md for why gating Bash itself is not on
  the table). It is instead DETECTED, after the fact, by
  `tools/bm_bash_audit.py` (D-1, this loop): a PreToolUse/PostToolUse pair
  that snapshots every fenced path that resolves to a REAL, EXISTING FILE
  at the moment the Bash call starts (a claim on a directory or a
  glob-shaped path is not expanded into the files it would cover, so a new
  file created inside a claimed directory during the call is invisible to
  it; see docs/HOOKS.md's "What it cannot see") before a Bash call and
  re-hashes it after, raising a high-severity alert naming the path when a
  session that does not own the fence changed it. Detection, not
  prevention: the write already happened by the time the alert exists, and
  docs/HOOKS.md and docs/KNOWN-LIMITS.md say so rather than implying
  otherwise. Wired on BOTH install paths since 2026-08-01 (the Claude Code
  plugin manifest and `scripts/install.py`'s clone-install path alike; see
  docs/HOOKS.md's "Installing the Bash audit hook").
  EXTENDED 2026-08-03 (closure item C-02). Two things above were incomplete
  until that date. FIRST, a shell command that destroyed BrotherMode's OWN
  enforcement state produced no alert and no stderr line at all. The measured
  case was `rm -f .brothermode/store.sqlite3`: the store is not itself a
  claimed path, so nothing in the detection pair ever looked at it, and with
  the store gone a write the fence had just refused became an allow. That is
  now DETECTED on the same pair, in both modes and in every BrotherMode
  project. The pre phase records whether the store exists, is non-empty and
  still begins with the SQLite file header, and which session tokens exist;
  the post phase reports every one of those that was lost, on stderr and as a
  high-severity `fence-control-loss` alert row. Growth and ordinary mutation
  are ignored on purpose, because a shell call that runs `bm_store.py` is
  normal work. When the store itself is what went missing the row cannot be
  written, and the hook says exactly that instead of falling silent.
  SECOND, and only if you opt in with `BM_FENCE_MODE=enforced` AND the Bash
  call's cwd resolves to a BrotherMode project, that command is now REFUSED
  before it runs. The project check is load-bearing, not decoration: this
  hook installs at USER-GLOBAL scope
  (`~/.claude/settings.json`), so it runs on every Bash call in every Claude
  Code session on the machine, and an earlier draft that refused before
  resolving a project root would have refused this same command in every
  unrelated, non-BrotherMode directory too. Outside a BrotherMode project the
  refusal check is inert. THE DELIBERATE LIMIT THIS CREATES: when
  `tools/bm_store.py` cannot be imported at all, the project check itself
  cannot run, so nothing is refused, even under enforced mode, anywhere. That
  is a fail-open path inside a fail-closed feature, chosen on purpose,
  because the only alternative is refusing every Bash command in every
  directory on the machine, which is not shippable. Someone who can break
  that import can therefore disable the refusal. Read what the refusal is,
  and is not, before relying on it: it is a literal match, a small list of
  destructive shell forms combined with the literal names `.brothermode` and
  `store.sqlite3`, plus two forms that wipe a whole directory without naming
  anything (`git clean` with `-x`, and `rm -r` aimed at `.` or `*`). It is
  not a shell parser and will not become one here. A name assembled at
  runtime, held in a variable, or sitting inside a script file the hook never
  reads is NOT caught, and neither is any program that deletes the file
  without the name appearing in the command. It also over-refuses on purpose,
  inside a BrotherMode project: a read-only command that merely mentions the
  directory next to a redirection is refused too. What enforced mode adds
  beyond the refusal is the aftermath: if the store does go missing by a
  route the refusal misses, the fence hook in that same mode then DENIES
  rather than allowing (C-01), so the one-command bypass needs both halves to
  fail rather than one.
- **A secret leaking through an export.** `dump`, its JSON output, and the
  MCP server responses all pass through ONE withholding policy
  (`export_column` in `tools/bm_store.py`): founder-typed prose is withheld
  outright by default, secret-shaped substrings are redacted wherever a
  column is allowed to show text at all, and absolute filesystem paths are
  masked. Described in full in "What this software does with your data"
  above.
- **A stale or hand-edited manifest going unnoticed.** `scripts/doctor.py`
  check 9 self-checks the release against `CHECKSUMS.sha256`, so a file
  that was quietly modified after the checksums were cut is reported rather
  than trusted -- CORRECTED 2026-08-01 (loop6 refuter finding A8b): on a
  DIRTY working tree (ordinary uncommitted edits, not a checked-out
  release) this check SKIPs and reports nothing, because a checked-in
  manifest was never generated to describe a tree mid-edit; a SKIP is not a
  PASS, and the whole run still exits 0 on a SKIP unless `--strict` is
  passed, so check 9 catches tampering only against a clean, checked-out
  release, not against your own working copy while you edit it.

**Attacks this design explicitly does NOT answer**, each with the one
sentence that says why it is out of scope rather than merely unmentioned:

- **A malicious process already running with your own user privileges.**
  Nothing in this project can defend against that, because a hook, the
  store, and every file this project owns are themselves just more files
  that process could already read or overwrite; there is no privilege
  boundary between "this tool" and "anything else you are running" to
  defend across.
- **A shell command that writes or deletes files, in the general case.**
  Claude Code hands a `Bash` PreToolUse hook a command STRING, not the set of
  files that command will touch, and nothing inside "Python 3.9, standard
  library only" turns one into the other, so there is no honest way to gate
  shell writes the way Edit and Write are gated. What exists instead is
  stated above: after-the-fact detection for fenced files and for
  BrotherMode's own state, and, in enforced mode and inside a BrotherMode
  project only, a literal-match refusal for the obvious destructive forms
  aimed at that state. Real containment would need an operating-system write
  mediator (a sandbox profile, a container, a FUSE layer). That is out of
  scope for this project, deliberately and not for now, and
  docs/KNOWN-LIMITS.md carries the same statement.
- **A supply-chain compromise of Python or git themselves.** This project
  is standard-library Python plus one documented, local-only use of the
  `git` binary; if either of those two trusted programs were themselves
  compromised, every promise in this document is made by code running
  inside the compromised interpreter or shelling out to the compromised
  binary, so no check this project runs on itself could catch it.

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
