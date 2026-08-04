# Known limits, stated plainly (2026-07-26)

What this project does NOT do, has NOT proven, or has only partly checked. This
file exists because an unstated gap is a failure even when it is small, and because
the single most useful thing a handover can contain is the list of things the last
person was not sure about.

## rc.4 merge: what the merged tree does NOT prove

- **A gate corpus is not bounded by your limit, and since 2026-07-30 (Loop 3) its
  full TEXT is.** Every applicable gate is still returned at every limit,
  deliberately, so a limit can never hide a safety rule. What changed is that gates
  are no longer all printed in full: every applicable gate appears in a compact,
  deterministic, hashed manifest, and full text is expanded only when the trigger
  matches, the scope is narrow and matched, the query reaches the gate's own action
  text, or the caller names the gate by ID. Ambient expansions are capped at
  `GATE_EXPANSION_CAP = 5` per call; an explicit `--expand <id>` is never capped,
  because withholding a gate the caller named would be the same hiding this project
  refuses to do for `limit`. Measured on a 20-gate store: 5722 characters before,
  1849 after.

  Two honest costs. At ONE gate the manifest's fixed header and footer make the
  output slightly LARGER than the old behaviour (524 characters against 454); the
  saving only begins past roughly two gates. And `GATE_EXPANSION_CAP` is a hardcoded
  constant, tunable by neither flag nor environment variable, so a founder who wants
  a different bound has to edit the source.
- **The installer is verified on macOS only** (Python 3.9.6). It is
  stdlib-only and POSIX-path-only and nothing in it is macOS-specific, but no
  Linux run has happened, so Linux is expected-to-work rather than tested.
  Windows is refused, not supported; WSL works.
- **The installer adds and overwrites files; it never prunes.** A file deleted
  upstream since your last install stays behind after `--upgrade`.
  `scripts/verify-install.sh` reports exactly those as EXTRA. Deleting was
  rejected on purpose: an installer that removes files it did not put there is
  the failure mode that loop existed to prevent.
- **Hook ownership is decided by the command string naming this installation's
  path.** Move the install directory by hand without re-running the installer
  and the old entries are no longer recognized as ours; pass `--target <old
  path>` to remove them.
- **The pinned install command is checked, not self-updating.** Since 2026-07-30
  (Loop 1) README, QUICKSTART and SETUP carry a tag-pinned clone generated from
  `install_command_pinned` in `tools/bm_project_facts.py`, and a drift test refuses
  any page that disagrees with that fact or that clones a moving branch. What the
  test CANNOT do is edit the pages for you: cutting a new tag makes the suite go red
  until the generated command is re-pasted. That is deliberate, because a docs
  rewrite nobody read is how the stale command got there in the first place. It does
  mean a release cut is a two-step act, and the second step is enforced only by the
  gate.
- **`scripts/doctor.py` now runs TEN checks, not one, since 2026-08-01 (Loop
  3 design D-3, docs/superpowers/specs/2026-08-01-loop3-consent-install-
  design.md): fence liveness (check 1, unchanged), VERSION-vs-manifest
  version identity, python3 and git availability, consent config presence,
  vault path writability, plugin-vs-clone duplicate-hook detection, project
  store health (`bm_store.py verify`), hook wiring matched to the consented
  installation_mode, a CHECKSUMS.sha256 self-check, and settings.json
  validity.** Each prints PASS, FAIL with a one-sentence fix, or SKIP with
  the reason nothing could be checked yet; `--json` for machines. What was
  already true of check 1 alone still holds for the whole surface: it checks
  the settings FILE and the CODE, not whether Claude Code has actually
  LOADED any of it (hooks are read at session start, so a mid-session
  correction is live at the next session), and the fence hook still fails
  open by design (missing, empty, or corrupt store, or any internal error),
  so a green doctor is a statement about the files and the code right now,
  not a promise about every future run.
- **The fence covers Edit, Write, MultiEdit and NotebookEdit for PREVENTION. Bash
  writes are DETECTED, since 2026-08-01 (Loop 6, D-1), and still not prevented.**
  Bash writes (redirection, `sed -i`, `tee`, `git checkout`, inline interpreter
  scripts, any subprocess) still reach the filesystem without passing a hook that
  can refuse them: `tools/bm_fence_hook.py`'s `PreToolUse` matcher still cannot
  parse arbitrary shell, so nothing blocks a Bash write the way an Edit or Write
  can be blocked. What changed is that a fenced file changed BY a Bash call FROM a
  session that does not own that fence is no longer invisible: `tools/
  bm_bash_audit.py` snapshots every fenced, existing file before a Bash call and
  re-hashes it after, raising a high-severity fence-breach alert (through the
  store, requiring a human) when the hash changed and the acting session is not
  the owner. Detection, not prevention, stated in as many words in docs/HOOKS.md's
  own "Bash-write detection hook" section, which also states what it cannot see: a
  write that restores the original bytes before the check runs, a Bash call that
  removes its own snapshot along with the evidence, a concurrent process racing
  the same window, and a claim on a directory or glob that was never expanded into
  the files it covers. `scripts/bm_shell.py` still mitigates only the writes a
  caller chooses to declare: it is a declaration channel, not a sandbox, and its
  `--declare-none` screen is a short list of obvious write forms, not a shell
  parser. CORRECTED 2026-08-01 (loop6 refuter finding A1/A8c): this row used to say
  the new hook was wired into the plugin manifest (`hooks/hooks.json`) but NOT YET
  into `scripts/install.py`'s clone-install path, so a clone install got the fence
  hook only. That gap is closed: `scripts/install.py` now wires both the
  `PreToolUse` and `PostToolUse` halves of the Bash-audit pair too, on the same
  terms as the plugin manifest, so both install paths carry Bash-write detection.
  What is still true either way: the snapshot only covers a claimed path that
  resolves to a REAL, EXISTING FILE at the moment the Bash call starts, not a
  directory or glob-shaped claim expanded into the files it would cover.
  EXTENDED 2026-08-03 (closure item C-02), and this is the honest shape of
  what is and is not contained.
  WHAT IS CONTAINED: nothing, in the operating-system sense. No file this
  project writes is protected from a shell command by anything except a hook
  that Claude Code chooses to run.
  WHAT IS NOW REFUSED: with `BM_FENCE_MODE=enforced` set, AND ONLY WHEN THE
  BASH CALL'S CWD RESOLVES TO A BROTHERMODE PROJECT, a `Bash` command whose
  TEXT matches a small literal list of destructive forms (`rm`, `>`, `>>`,
  `tee`, `sed -i`, `truncate`, `mv`, `cp`, `chmod`, an inline `python3 -c`, a
  rewriting `git` subcommand, `find -delete`, and a few more) while also
  containing the literal string `.brothermode` or `store.sqlite3`, plus
  exactly two whole-directory forms that name nothing (`git clean` with
  `-x`, and `rm -r` aimed at `.` or `*`). The project check is load-bearing,
  not decoration: this hook installs at USER-GLOBAL scope
  (`~/.claude/settings.json`), so it runs on every Bash call in every Claude
  Code session on the machine, and without the project check enforced mode
  would refuse commands in every unrelated, non-BrotherMode directory too.
  Outside a BrotherMode project the refusal check is inert.
  THE DELIBERATE LIMIT THIS CREATES: when `tools/bm_store.py` cannot be
  imported at all, the project check itself cannot run, so nothing is
  refused, even under enforced mode, anywhere. That is a fail-open path
  inside a fail-closed feature, chosen on purpose: the only alternative is
  refusing every Bash command in every directory on the machine, which is
  not shippable. Someone who can break that import can therefore disable the
  refusal.
  WHAT IS NOW DETECTED, in both modes and in every BrotherMode project: the
  store file disappearing, becoming zero bytes, or ceasing to begin with the
  SQLite file header, and any session token file disappearing, between the
  start and the end of a Bash call. Each one prints a sentence on stderr and
  raises a high-severity `fence-control-loss` alert; when the store is the
  thing that went missing the alert cannot be written and the hook says so
  rather than falling silent.
  WHAT IS NOT CAUGHT, stated in full because a partial check presented as a
  complete one is the failure this file exists to prevent: a path assembled
  at runtime or held in a variable; a destructive command inside a script
  file, a Makefile target, or any program the command merely starts; any form
  not on the list; a write that returns a fenced file to its original bytes
  before the check runs; a Bash call that deletes its own snapshot; every
  write by a process that never passed through a hook at all (a second
  terminal, an editor, a background job); and, as stated above, anything at
  all once `tools/bm_store.py` cannot be imported. A project with NO active
  claim is not snapshotted at all, so nothing is detected there either,
  though enforced mode still refuses. And the refusal over-refuses by
  design, inside a BrotherMode project: `ls .brothermode > /tmp/x` is
  refused, and so is `git clean -xfd` anywhere in the tree. Full
  operating-system containment (a sandbox profile, a container, a FUSE write
  mediator) was considered and is explicitly OUT of scope: it sits outside
  "Python 3.9, standard library only" and would be a second product rather
  than a fix.
- **OBSERVED GREEN 2026-07-31, on all nine jobs.** This entry used to say no real
  Actions run had ever been observed. Run `30564943060` for commit `f751f9f`
  concluded success across the serial `gate` job, both `suite` legs, and all six
  `store` legs (three platforms, both Python versions). Getting there required
  fixing a real defect the Windows legs had been failing on: `invocation()` quoted
  user-facing commands with POSIX-only `shlex.quote`, so a Windows path came back
  single-quoted and the printed remedy was unrunnable in cmd and PowerShell.
  What is still NOT proven: the failure-artifact upload path, which needs a
  deliberately broken build on a temporary branch; and that green stays green,
  since the Windows fix was verified by CI rather than on a Windows machine here.
  Full per-job table: the current release evidence file in `docs/evidence/`
  (the rc.6 file this line used to cite was renamed forward at each
  release cut; `docs/evidence/RELEASE-CANDIDATE-2.0.0-rc.9.md` carries it now).
- **The remaining CI-equivalence gap.** Every refusal in `tools/test_all.py` was
  proven by running it on one machine. The first push to a branch CI watches is what turns
  that from designed to demonstrated.
- **The fence hook suite runs in CI on Linux and macOS only.** It contains
  deliberate win32 skips, so it is written to be Windows-aware, but it has never
  been run on Windows. The store and recovery suites do cover Windows.
- **The documentation consistency suite checks the pages listed in
  `tools/test_bm_docs.py` ACTIVE_DOCS.** Everything else, including
  `docs/DESIGN.md`, `docs/WHITEPAPER.md`, `docs/OBSIDIAN.md`, `docs/SUNSET.md`,
  `docs/REMAINING.md`, the PDFs and the one-pager HTML source, is unchecked. The
  suite catches stale FACTS it can generate, not a stale claim written in prose.
- **Path masking, narrowed 2026-07-31 (Loop 5) but not closed.** Quoted paths,
  escaped spaces, Windows drive paths, UNC paths, Unicode segments, multiple paths
  in one field, and paths glued to a word at the six known roots (`Users`, `home`,
  `root`, `Volumes`, `private`, `cygdrive`) now mask correctly. Still true: an
  UNQUOTED path containing a bare space masks only up to the space, and a
  single-letter Windows drive glued to a word stays unmasked, deliberately,
  because masking it provably swallows `https://` URLs. The known-root list can
  also OVER-mask a relative path that happens to share one of those six segment
  names. Withheld columns are unaffected: they reproduce nothing at all.
- **Session labels are gated by an allowlist of generated shapes, not by a schema
  split.** Since 2026-07-31 (Loop 5) only the four real generated id shapes
  export; any hand-typed label, hyphenated or not, is withheld. This is
  deliberately NOT the plan's literal design (a separate internal session UUID
  column beside an optional human label); that split remains open as a schema-12
  candidate, recorded in `docs/NOT-FINALIZED.md`.
- **An approved rule's own `because_text` appears in `applications` output, and
  that is settled.** Founder ruling 2026-07-31: it is a feature, not a leak. The
  founder wrote it, explicitly promoted it into a rule, and retrieval exists to
  show rules with their reasons, so `applications` keeps explaining WHY a rule
  applied. Recorded here so the canary suite's "rule reason" field is read as
  "must not leak from surfaces that withhold founder prose", not as "must never
  render anywhere".
- **Windows owner-only file modes and ACLs.** Nothing in this project configures
  a Windows ACL. Stdlib only, with no subprocess in the shipping tools, rules
  out both `icacls` and `pywin32`, so `os.chmod` is best-effort there and the
  real control is your user profile. No Windows behavior is proven by these
  suites.
- **BrotherMode's own hooks are verified in Claude Code only.**
  `docs/RUNTIMES.md` reports whether each runtime has hook points at all; that
  is not the same claim as "BrotherMode's hooks run there". No runtime was
  driven end to end: the instruction-file conventions are documentation-verified,
  not behavior-verified.
- **The packaged modules install at the top level of site-packages**, and a
  package install wires no hooks. Building with the macOS system pip (21.2.4)
  silently produces an empty `UNKNOWN-0.0.0` wheel; build with `uv build` or a
  pip new enough to read PEP 621 metadata.
- **The public benchmark has been measured on ONE machine and ONE platform**
  (macOS, Python 3.9.6, 2026-07-29) and is not in CI. Scenarios 1, 2, 3 and 6
  exercise lexical word-overlap retrieval, which names itself `mode=lexical`; a
  green benchmark is not evidence of semantic retrieval, which this project does
  not have.
- **README's "verify the safety claims yourself" grep is stale.** As published
  it greps for the bare words http, socket, curl and wget across `tools/*.py`
  and `tools/*.sh` and says "Expected: no output", but it returns hits on
  documentation URLs inside comments. The underlying claim still holds, and an
  import-scoped grep proves it:
  `grep -rnE "import (urllib|socket|http|ftplib|smtplib|requests)" tools/*.py |
  grep -v "^tools/test_"` returns nothing. `docs/beta/BETA-KIT.md` ships the
  corrected grep.

## P7: what the optional search index does NOT do

- IT IS ENGLISH STEMMING. The tokenizer is `porter unicode61`. unicode61 folds
  case and accents, so French and Japanese text is stored and searchable, but
  porter stems ENGLISH only: "pousser" and "poussé" do not stem together, and
  Japanese has no word boundaries for it to find, so a Japanese query matches on
  whole runs of text or not at all. The fast path is therefore a real gain in
  English and roughly neutral elsewhere. Nothing in the output claims otherwise.
- IT IS NOT SEMANTIC. BM25 is term frequency arithmetic. There are no
  embeddings, and a task that shares no words with a rule still finds nothing
  unless the rule is a gate. That is a deliberate limit of this loop.
- DRIFT IS ONLY CHECKED WHEN THE INDEX IS ON. With `BROTHERMODE_FTS5` unset,
  `verify` says so in its note and compares nothing.
  CORRECTED 2026-07-29: this entry used to add that a stale index left by a
  previous session is "a reporting limit rather than a correctness one". That
  was wrong, and the fix round proved it on the real CLI. The switch is a
  per-process variable, so one ordinary shell that approved or edited a rule
  left the index behind with no error anywhere, and the next run with the fast
  path on consumed the stale index: a rule came back for a task its current text
  shares no word with, matched on text the founder had deleted, and the CLI
  explained the hit as a stem match no live word could produce. The index is now
  reconciled against the rules at the moment it is CONSUMED, so it cannot answer
  a query while it disagrees with them.
- THE INDEX IS RECONCILED BEFORE IT IS READ, NOT ON OPEN. It is built and filled
  the first time a store is opened with the fast path on, and maintained inside
  the same transaction as every approval and edit made by a connection that has
  the fast path on. Because another process can write between your open and your
  query, the check that matters runs at retrieval: an index that disagrees with
  the rules is rewritten from them first, and if it cannot be rewritten (another
  writer holds the lock, or the caller has no write authority) the fast path
  switches off and the run reports `mode=lexical`. `verify` and `index-status`
  still SHOW drift rather than repairing it, which is what keeps them worth
  running, and `rebuild-index` is still the explicit repair.
- THE INDEX CANNOT TAKE THE STORE WITH IT. Until 2026-07-29 it could: index SQL
  ran through the same routing point as everything else, and that point reads
  "no such table" as structural damage and quarantines the database file. An
  index table dropped mid-session therefore cost the whole store, the approval
  in flight, and every rule in it, and the status command did the same thing
  while claiming to be read only. Index statements now have their own routing
  point with no quarantine in it, so the worst an unreadable index can do is
  turn the fast path off.
- FORGOTTEN RULES STAY INDEXED. The index mirrors the current version of every
  rule row, including forgotten ones, exactly as `learning_rule_versions` does.
  They can never be retrieved (the state filter runs before ranking), so this
  costs index size, not privacy: the same text is in the versions table either
  way. Un-indexing them is not done.

## P6: what the retrieval run still cannot tell you

The run row makes the denominator a stored fact, and these things are still out
of its reach. Stated here rather than discovered later.

- ONE RUN IS THE AUTHORITY PER TASK. When the same task text is retrieved more
  than once in one session with DIFFERENT limits or contexts, the earliest run
  is used and `retrieval_runs` reports how many there were. Earliest now means
  insertion order, so it is the same run on every run of the classifier (fix
  round P6 closed a random uuid tie-break on the one-second timestamp). The
  later runs are still not merged and not compared. A reader can see the
  ambiguity; nothing resolves it.
- THE CORPUS CHECK COUNTS, IT DOES NOT IDENTIFY (fix round P6). A task is graded
  only when the rules that existed at retrieval time still number exactly what
  the run recorded as eligible; otherwise it is `corpus_changed_since_retrieval`
  and nothing is attributed. The run stores HOW MANY rules were eligible, not
  WHICH, so a removal and an addition that exactly cancel out still read as
  equal and the task is graded against a corpus that is not the one that ran.
  Narrower than the old behaviour, which re-ranked today's rules unconditionally,
  and not the same thing as reconstruction.
- A RELEVANCE MISS NOW MEANS ONE THING: the rule was eligible, ranked inside the
  requested limit, and the ledger holds no application row for that run. With
  the corpus pinned, that is a bookkeeping hole rather than a ranking verdict.
  Ranking quality itself is not measured by this number.
- MIXED-ERA TASKS ARE NOT SPECIAL-CASED. A task with both legacy application
  rows (no run) and a run row counts only the run's own rows as surfaced. The
  corpus count usually refuses such a task anyway, but that is a consequence,
  not a check.
- TIMESTAMPS ARE WHOLE SECONDS. A rule rewritten inside the same second as the
  retrieval reads as unchanged. Nothing in this design can separate them.
- LEGACY ROWS STAY LEGACY. An application recorded before schema 4 has no run,
  is reported as incomplete evidence, and is never backfilled. The misses those
  tasks had are not zero; they are unknown, and the reports say so.

## P5-fix: without `--record`, two units of work still cannot be told apart

The idempotence key now includes the work record, so naming one with `--record`
gives each unit of work its own application row. WITHOUT `--record` there is
still nothing to key on beyond the task fingerprint, which comes from the query
alone. Two different pieces of substantial work in one session phrased the same
way therefore still land on one row. That is now DISCLOSED rather than hidden:
`apply` prints which work record the row it found already belongs to and says it
cannot tell a re-read from different work. It is disclosure, not detection, and
the exit code is still 0. The founder has to act on the note.

Also not closed by this round: nothing forces `--record` to be passed at all,
and nothing verifies that the work record named is the work actually being done.
A caller can pass a real but wrong work-record id and the row will link to it.

## P5-fix: one pre-existing unrelated test is flaky on this machine

RESOLVED 2026-07-29 by Loop P12, which deleted the test rather than stabilised
it. `test_bm.py`
`TestFinding12HandoverDeliveryIsSerializedAndVerified.test_calibrated_without_the_lock_the_same_pair_duplicates_the_handover`
failed roughly 4 runs in 5 with "the reproduction did not reproduce": a timing
race in a CALIBRATION test for the handover lock, not in the guard it
calibrated. The lock and the append it guarded no longer exist, so neither does
the test. What replaced it is a concurrency test that races two parks through
the store's own transaction, which has no barrier to time out.

## Loop P5 left the older documentation naming the deprecated verb

`SKILL.md` now names `bm_learn.py apply --session` as the substantial-work path,
and a test enforces that. The narrative docs were NOT swept in the same change:
`docs/CORRECTION-LEARNING.md`, `docs/HANDOVER-2026-07-29.md` and the plan under
`docs/superpowers/plans/` still show `relevant`. Those examples still WORK, since
`relevant` is a live alias, but they teach the deprecated verb and a reader
following them would take the read-only path for work that should be recorded.
The law file is the one an agent follows, so this is a documentation debt rather
than a live hole, and it is scheduled for the Documentation Agent's pass.

Also unproven at P5: nothing forces an agent to run `apply` at all. The command
contract makes the recorded path the obvious one and removes the forgettable
flag; it does not detect a substantial task that skipped retrieval entirely.
`should-retrieve` answers that question only when someone asks it.

## The biggest one, updated: the engine IS connected now, and that surfaced new defects

Phase 3 landed 2026-07-26: `tools/bm_store.py` is now imported by
`bm_autosave.py`, `bm_sessionstart.sh`, `bm_telemetry.py`, and `bm_threads.py`
(43 references across those four files, measured the same day), and
`bm_registry.py`, the old JSON registry, is deleted rather than shimmed. The
defects the original audit found in that registry (silent name takeover, two
registries minted for one project, a truncated fingerprint dropping a
handover) go away with the file.

They were replaced by five real defects in the rewired thread commands,
written up in `docs/superpowers/specs/2026-07-26-release-blockers.md`. This
project's code changes fast: of the five, four were already fixed by the
time this file was corrected, in the same session, some within the hour.
Each line states what was found, and what direct re-execution just before
this edit actually showed:

- **Recovered work was world-readable. FIXED, re-verified 2026-07-26.**
  `bm_autosave.py recover` used to leave its worktree `drwxr-xr-x` with
  `-rw-r--r--` files inside (reproduced independently on this machine's own
  macOS `/tmp`, not only the Linux case that found it first). Re-run just
  now: the recovered directory comes back `drwx------` and the tool prints
  the mode it achieved.
- **The reversibility promise was broken. FIXED, re-verified 2026-07-26.**
  Turning thread mode off and then resuming a thread from a different
  session used to be refused with `not-owner`, breaking the founder's
  ratified requirement that thread mode be reversible mid-project with
  every thread resumable. Re-run just now: `resume` from a different
  session on a parked thread succeeds and transfers ownership.
- **`verify` reported a false problem after any thread command. FIXED,
  re-verified 2026-07-26.** Used to report "1 problem(s) found" on an
  otherwise healthy project and name an unresolvable relative path. Re-run
  just now: `verify` reports "healthy, 0 problem(s)" after a thread `off`.
- **Neither CLI validated flag names. FIXED, re-verified 2026-07-26.**
  `start X --file f` (the wrong, singular flag) used to be accepted at exit
  0 with no fence. Re-run just now: both `bm_store.py` and `bm_threads.py`
  refuse an unrecognized flag by name at exit 2, for `start` and for
  `checkpoint`.
- **A refused adoption attempt wrote its handover into `STATE.md`. FIXED,
  re-verified 2026-07-26 by the orchestrator after this file first recorded
  it as open.** The delivery write happened before the ownership check, so a
  refusal still recorded a live thread as "Adopted from dead/stalled thread".
  The order is now transition first, deliver second. Re-run just now: a
  different session attempting `adopt` without the override exits 2, the
  checksum of `STATE.md` is IDENTICAL before and after, and the false block
  appears zero times. This entry is kept rather than deleted because the
  sequence, found open and then closed within the same session, is the
  clearest example of why this file states dates and re-verification rather
  than conclusions.

Practical consequence: all five defects the rewire introduced are now closed
and each was re-verified by direct execution rather than accepted from a
report. This project's code changes fast; re-run the
reproduction steps in the release-blockers spec yourself rather than trust
this file's dates once more time has passed. The general operating
restrictions from the original audit still apply: run commands from the
repository root, avoid glob fences, do not run two worktrees of one repo in
parallel sessions, and never restore an autosave snapshot in place without
inspecting it first in a separate worktree.

## Used for real, but never MEASURED on a real project

CORRECTED 2026-08-03, and this correction runs in the opposite direction from
most on this page: the limit was overstated, not understated. Every earlier
version said flatly that nothing here had ever run on a real project and that
everything rested on tests, adversarial execution and simulated lifecycles.
That was true of the RECORD and false of the world. The founder reports weeks
of his own daily use, plus other people using it on their own machines,
installed by pointing them at this repository.

What remains true, and is the actual limit: none of that use was MEASURED.
There is no counted set of projects, no recorded failure and rework rate, no
comparison against working without the tool, and no outside participant whose
experience was observed rather than reported. So the honest statement is that
real use exists and graded outcomes do not, and a score that wants the second
cannot borrow it from the first.

The older, stronger claim survives in the dated documents that made it
(docs/SCORECARD-2026-07-27.md, docs/ACCOUNTING-2026-07-26.md). Those were
accurate on their dates and are deliberately NOT rewritten: editing a dated
record to match today is the failure this project refuses on principle.

## Continuous integration HAS executed, and it FAILED on Windows

CORRECTED 2026-07-26. An earlier version of this file said continuous integration
had never executed. That was FALSE and it was never checked: the workflow has run
18 times, three of them on branch v2, and the record is public in the repository's
Actions tab. Assuming instead of looking, in a project whose whole point is not
doing that, is worth recording rather than quietly fixing.

The result on the tagged release commit (run 18, commit 7c2e0ec) is FAILURE. The
job `store (windows-latest, 3.x)` exited 1; the other matrix legs were cancelled by
fail-fast, so the Windows 3.9 leg and one macOS leg remain UNKNOWN rather than
passing.

## Recovered work is owner-only on POSIX ONLY, not on Windows

Found 2026-07-27 by putting the recovery suite into CI for the first time (audit
finding 14). It failed on both Windows legs and passed on all four POSIX legs.

The guarantee "a recovered worktree, and any private untracked file inside it, is
readable only by you" rests on a POSIX file mode of 0700. Windows governs access
by ACLs instead, and there `os.chmod` can only toggle a read-only bit. So on
Windows the recovered directory inherits whatever the parent temp directory
grants, and this project does not currently set an ACL to narrow it.

What this does and does not mean:

- The tool does NOT lie about it. It prints the mode it actually achieved rather
  than the mode it wanted, so a Windows user sees the real value.
- The POSIX guarantee is unchanged and still asserted at full strength.
- A Windows user on a shared machine should treat recovered work as readable by
  other local accounts until this is closed with a real ACL call.

Not fixed yet because doing it properly needs a Windows ACL API rather than a
weaker assertion, and a security property is worth stating honestly while it is
missing rather than quietly skipping the test that revealed it.

## Windows was BROKEN, was fixed, and is now GREEN (the full arc, kept on purpose)

CORRECTED 2026-07-26. An earlier version said Windows was "designed for, not
proven". The stronger truth: it failed. Verbatim from the run:

    PermissionError: [WinError 32] The process cannot access the file because it is
    being used by another process: '...\.brothermode\store.sqlite3'

Cause: sqlite connections were opened and never closed. POSIX allows deleting a
file that still has an open handle, so every macOS and Linux leg passed and the
leak was invisible; Windows refuses, which is the only reason it surfaced. That
makes it a real API gap on every platform (a long-lived process leaked a handle per
store) that only one platform reported.

RESOLVED 2026-07-27, CI run on commit ba4eca2: all eight jobs pass, including
BOTH Windows legs (3.x and 3.9). This is the first green Windows run this
project has ever had. The fix was an idempotent close() plus context-manager
support on Store and ReadOnlyStore, twelve call sites closed, and four
Windows-only test bugs that only surfaced once the suite got far enough to run:
a mock-call string comparison that repr-doubled backslashes, a write handle
opened on a memory-mapped -shm file, and a deliberate locker connection that was
rolled back but never closed.

The arc is kept here rather than collapsed into "Windows works", because the
useful part is not the outcome. The founder OVERRODE a recommendation to declare
Windows unsupported and required it as scope. That override is the only reason
any of this was found: the defect was a real API gap on every platform (a
long-lived process leaked a database handle per store) that POSIX silently
tolerates. Narrowing the supported platforms would have hidden it, not avoided
it.

What is now guarded mechanically: every test that opens a store and does not
close it FAILS, on every platform, naming the test. That check was calibrated in
both directions before it was trusted, and enabling it immediately found ten
further undisciplined sites. Two earlier attempts at that check were discarded
for being incapable of failing, which is written up in the commit.
Symlink and hardlink tests skip on Windows entirely. Read-only database behavior,
file permission semantics, and the worktree layout are unverified there.

## Paths exercised only partly

- The backup that should be written before a status file is rewritten has not been
  exercised, because in every test the tool correctly refused before reaching it.
  Refusing is the safer behavior, but the backup code path is unproven.
- The `deliveries` table and the full-length handover fingerprint shipped with no
  writer. RESOLVED 2026-07-29 (Loop P12): `deliveries` was deleted earlier as
  decoration, and the fingerprint now has a real writer. It is the dedupe behind
  the unique index on the `handovers` table, which is what stops a retried
  handover being stored or rendered twice. CORRECTED the same day (P12 fix
  round): that index was UNIQUE(lifecycle_uuid, payload_fingerprint) over every
  row for all time, and a key that wide does not deduplicate handovers, it
  deletes them. The fingerprint covers the objective, files, owner, tier, check,
  evidence, latest digest and decisions, and NOT the state, version, transition,
  heading or sessions, so a second park after an acknowledged one wrote nothing
  at all. Schema 6 makes it UNIQUE(lifecycle_uuid, payload_fingerprint, heading)
  WHERE delivered_at IS NULL. What that still means, stated rather than hidden:
  two parks with the SAME heading while the first is unacknowledged remain one
  row, so the second transition has no handover row of its own. The founder sees
  the same text either way; the one-transition-one-handover link is exact only
  up to identical text.
- `send()` takes no expected version, making directives the one mutation without
  optimistic concurrency. Phase 3 owns the directive experience.

## The test suite's honest shape

Eight rounds of adversarial review plus one independent code review plus one
systematic mutation audit. The mutation audit found that fifteen tests named as
calibrated were testing a local copy of old code rather than the product, and could
never have failed; they are being deleted and the honest count reported. Treat any
test count in this repository as a claim to be re-verified rather than a
certificate.

## The correction-learning system: built through Loop 12, never run on a real day

UPDATED 2026-07-29. The paragraph below used to say the self-learning mechanism
was designed and not implemented. That is now false and would mislead a reader
who trusted it: capture, founder approval, scoped explainable retrieval,
conflict and supersession detection, retrieval and application outcome
tracking, and rework and escaped-defect grading are all built, tested, and
were driven by hand against a real, throwaway store while writing this line.
Plain-language explanation with real command output:
`docs/CORRECTION-LEARNING.md`. Technical detail: `docs/NOT-FINALIZED.md`
sections 15, 17 through 20.

What has NOT changed, and matters more than what has:

- **Never run on a real day of the founder's work.** Every command, every
  count, every test in the whole system comes from a test suite or a scripted
  probe against a throwaway store. `docs/NOT-FINALIZED.md` item 1 stays
  UNPROVEN, ranked as the highest-harm open item in the project, until a real
  dogfood window (Loop 14a) closes it. No amount of further testing closes
  this; only using it does.
- **Approval proves an answer, not an identity. UPDATED 2026-07-29 (post-audit
  LOOP 3, Model A).** Until this date the "founder-only approval" claim was
  wording, not mechanism: `bm_learn.py approve <id>` with no arguments beyond
  the id created a rule and wrote its own approval evidence. Reproduced against
  d88abcc, gate rule 61de7eb9, exit 0. Approval now needs a one-time receipt,
  minted from a real answer, bound to one candidate and to the exact rule text
  shown, valid fifteen minutes, spendable once, consumed in the same
  transaction that creates the rule. What is still NOT true: nothing checks
  WHICH human answered. Anyone who can run `grant-approval` can mint a receipt.
  The guarantee is "an answer was given about this exact thing, once, recently",
  not "the founder gave it". Read any wording that suggests otherwise as a
  defect and report it.
- **The receipt gate covers creating AND rewriting a rule, since fix round P3
  on 2026-07-29, and it did not on the day LOOP 3 landed.** For that one day,
  `Store.edit_learning_rule` appended a new current version of an approved rule
  with no receipt, no fingerprint check, and a hardcoded
  `approved_by='founder'`. Reproduced: an approved gate rule saying "never force
  push to main" was rewritten to "always force push to main, skip review",
  keeping its gate severity. Editing now takes its own one-time receipt. Two
  things are still true and worth stating: the receipt proves an answer, not an
  identity, exactly as above; and neither minting nor spending an edit receipt
  has a CLI command, so this door is reachable only from imported code, which
  is also the only vector it ever had.
- **Five more commands can alter the live rule set, and none of them had a
  receipt, until LOOP 2 on 2026-07-30.** Create and edit were receipt-gated;
  supersede, resolve-conflict, deprecate, forget, and resolving a critical
  alert were not. The most serious: `resolve-conflict` could stand an
  approved GATE rule down (state `contradicted`, `deprecated`, or
  `superseded`) with no human answer anywhere, and resolving a critical
  alert unblocked an approval the same way, since `blocking_alerts` stops
  counting a note the moment it is resolved. Both are reproduced and closed
  in `tools/test_bm_store.py` (`TestLoop2StateChangeReceipts`). Rather than
  five separate checks, ONE generic lane now covers all five: a new,
  additive `learning_state_change_receipts` table (schema 8 to 9), one
  `mint_state_change_receipt` and one `_require_state_change_receipt`/
  `_consume_state_change_receipt` pair, keyed by a `kind` discriminator so a
  receipt minted for one of the five can never spend as another, and the
  store's own `change_learning_rule_state` gate is now UNCONDITIONAL for
  supersede/deprecate/forget: a caller cannot opt out by simply omitting the
  receipt kind, which closes the direct-Python-import vector the same way
  approval and edit already were closed. An ordinary note, and a
  non-critical alert, still resolve with no receipt, exactly as before:
  only a critical alert (kind `alert`, severity `critical`) is gated.
  `bm_learn.py capture` with no arguments also used to store an EMPTY
  candidate instead of printing usage (item D6 of the Loop 0 sweep); it now
  refuses at the CLI layer, leaving `capture_learning_candidate` itself
  untouched. And the forged-token test's mutation
  (`tools/test_bm_store.py`) was probabilistic, flaking roughly one run in
  sixteen when the real token's last character happened to be `0`; it is
  now a guaranteed-different substitution.
- **A result limit caps soft rules only, since loop P4 on 2026-07-29, and it
  capped gates too before that.** Reproduced on the real CLI against 05441e7:
  two live global rules, a gate whose trigger shared no vocabulary with the
  task, `--limit 1`, and the gate never appeared. The relevance floor already
  exempted gates from being filtered for irrelevance, and the slice then cut
  them anyway, which made the exemption decorative. `retrieve_learning_rules`
  now splits eligible rules into gates and soft, returns every applicable live
  gate regardless of the limit, and applies the limit to soft rules only.
  Ranking is unchanged, so a gate does not jump the queue, it simply cannot be
  cut from it. `--limit 0` and negative limits both mean "gates only". What is
  still NOT claimed: applicability is scope plus lifecycle state, so a gate
  scoped to a project you are not in, or one you deprecated or forgot, is
  correctly absent, and a gate you never approved was never a gate. Relevance
  is still lexical word matching, so the ranking a gate sits at inside the
  result can still be poor even though its presence is guaranteed. And the
  numbers are checkable rather than trusted: `gates_returned` is counted off
  the rows actually returned, `gates_total` off the applicable set, and a test
  fails if they ever differ.

  Amended the same day by fix round P4-fix, because the loop shipped the
  guarantee and half the disclosure. The two sentences were printed at the
  bottom of `relevant`, and the zero-result branch returns before reaching
  them, so `--limit 0` and `--limit -1` in a store holding one matching soft
  rule printed "none matched" and no omission count while the JSON from the
  identical call reported `omitted: 1`. No gate was hidden by this, since an
  empty result means `gates_total` was zero, but the founder was told all the
  rules had been considered when one had been cut. The footer is now one
  function called from every human-output path, and the zero-result line names
  which of its two causes applied. What is still NOT claimed: the count of
  rules "in scope" on that line is scope and lifecycle eligibility, not a
  promise that each of them is a good match, and "none matched" remains a
  statement about lexical overlap, which is the only relevance this tool has.
- **A digest in the database is not a promise, it is a delay.**
  `founder_response_hash` is an unsalted sha256 of a short answer. Until fix
  round P3 it was printed verbatim by `dump`, and a ten-word wordlist recovered
  the answer. `dump` now withholds digests, but the column is still an unsalted
  hash of a low-entropy string, and `--raw` and the database file itself expose
  it. `SECURITY.md` already treats the file as sensitive; treat that column as
  the answer itself, not as protection.
- **Rules approved before 2026-07-29 carry the old, weaker provenance.** The
  schema 2 to 3 migration deliberately does not annotate or invalidate them.
  If a store predates receipts, its existing rules were approved under the
  mechanism described above as broken, and their approval evidence should be
  read that way.
- **No independent second-model review.** `docs/NOT-FINALIZED.md` item 12
  stays open. The privacy and security fixes that landed in Loop 12 (the
  secret scrubber and the withholding of raw founder text, described in item
  15) were written and verified by the same model family that built the
  feature. That is real evidence, but it is not the independent adversarial
  pass item 12 asks for.
- **Two loops of the program were deliberately not built.** Evaluation
  partitions (Loop 9) and generated knowledge views (Loop 10) are both
  unbuilt on purpose, with stated reopening conditions, because at the
  current size of one founder's rule corpus (twenty to forty rules) neither
  would produce a number large enough to support a decision. Building the
  machinery anyway would make an unsupportable number look rigorous, which
  is the exact failure this program's own principle forbids. See
  `docs/CORRECTION-LEARNING.md` for the reopening conditions.
- **The optional automatic-retrieval hook (Loop 11B) is gated on the dogfood
  window, not built yet.** The skill-driven retrieval that already ships
  (Stage A, Loop 11A) has to prove itself in real use first. A hook that
  pushes the wrong rule into every prompt is worse than the opt-in retrieval
  this project ships today.
- **The old weekly scorecard's unflattering audit is still true where it was
  never addressed.**
  `docs/superpowers/specs/2026-07-26-self-learning-redesign.md` found a
  hardcoded metric that could never move, five of nine scored metrics with no
  mechanical number, thirteen law amendments against one weekly review, and
  ratings the graded party could write itself. The correction-learning system
  now gives several of those metrics a real, row-backed number
  (`bm_learn.py loop-failures`, `bm_learn.py rule-outcomes`, see
  `docs/CORRECTION-LEARNING.md`'s scorecard section), but `RUBRIC.md` itself
  is a founder-frozen template that changes only by the founder's own
  decision, so it has not been rewritten here. Do not cite the OLD scorecard
  metric 1 as evidence of anything until the founder ratifies pointing it at
  the new commands.

## What was checked by class rather than individually

The original external audit contained 63 findings. Twenty-two were reproduced by
execution. The remainder were triaged into phases by class rather than each being
re-proven. If one of them matters to a decision, re-verify it rather than trusting
this file.

## The plugin install path and the beginner layer: brand new, installed once

Added 2026-07-31 on the beginner-first branch. The facts, stated so the
QUICKSTART honesty label has a register entry behind it:

- The Claude Code plugin packaging (`.claude-plugin/plugin.json`, the
  repository marketplace manifest, `hooks/hooks.json`, the six `/brotherme`
  commands, and the guided skill at `skills/brotherme/`) is new. It has been installed exactly once: on the
  author's machine on 2026-07-31, from a local copy of the repository, full
  cycle in `docs/evidence/2026-07-31-first-plugin-install.md` (in the public
  repository). No install from GitHub or on any other machine yet. Two
  defects that first install surfaced: a name collision (a development copy
  carrying the same manifest name is refused loading while the plugin is
  installed; the development copy is now named differently) and double
  wiring (the plugin auto-wires the same six hook events scripts/install.py
  wires into settings.json, so a machine carrying both runs every hook twice
  while the plugin is installed; pick one wiring, not both). UPDATED
  2026-08-01 (Loop 3 design D-3): this double-fire state is no longer
  silent. `scripts/doctor.py` check 6 detects it mechanically, both a
  plugin named in settings.json's `enabledPlugins` and a clone-managed
  `PreToolUse` entry wired at the same time, and FAILs naming which one to
  remove (`/plugin uninstall <name>` or `python3 scripts/uninstall.py`).
  What is still NOT true: nothing prevents the double install from
  happening in the first place, only from staying unnoticed once doctor is
  run.
- The marketplace install command only works once these files exist on the
  branch or tag the marketplace add fetches. If your copy predates them, the
  command fails; that is a missing-files condition, not a broken machine.
- `hooks/hooks.json` mirrors the same six hook events `scripts/install.py`
  wires into `settings.json`, but the plugin-managed wiring has never been
  exercised end to end. The `scripts/install.py` path is the exercised one.
- How the guided layer loads is only partly proven. On this project's own
  machine, a working copy at `~/.claude/skills/brothermode` that contains the
  plugin manifest, the commands, and the guided skill DID register all six
  `/brotherme` commands and the guided skill in a live Claude Code session on
  2026-07-31 (one observation, one machine, one Claude Code version). No
  fresh-machine install of either path has demonstrated the guided layer yet;
  treat reachability as promising, not verified.
- UPDATED 2026-08-01 (Loop 3 design D-1/D-2, docs/superpowers/specs/
  2026-08-01-loop3-consent-install-design.md): what this entry used to say
  is now false and would mislead a reader who trusted it. There IS a
  first-run setup now, `python3 scripts/setup.py`, runnable interactively
  (question by question, plain words) or flag-driven
  (`--vault PATH --mode plugin|clone --accept-notice`) for scripted runs and
  tests, and it is the ONLY code path in the project allowed to create
  `~/.brotherme/config.json`. Every write-capable hook entry point
  (`bm_sessionstart.sh`, `bm_autosave.py`, and all three hook-wired commands
  in `bm_telemetry.py`: `outcomes-append`, `precompact-brief` and
  `stop-warn`) checks that config BEFORE writing anything and, when setup has
  not run, writes NOTHING and prints one sentence naming `scripts/setup.py`:
  proven directly by walking both the HOME tree and the project tree before
  and after, a fresh HOME stays at zero files (`tools/test_bm_consent.py`,
  the suite this loop added).
  CORRECTED 2026-08-02, and the correction is the useful part: this sentence
  named only two entry points because only two had been gated, and the two it
  omitted were writing. `precompact-brief` wrote the founder's last message
  VERBATIM into `~/BrotherModeVault/99-System/telemetry/last-resume-*.md`
  pre-consent, and `stop-warn` created the vault tree to hold a marker file.
  Both were found by an independent Loop 9 review and reproduced from scratch
  in a throwaway HOME before being fixed. The escape route matters more than
  either bug: the PreCompact hook line runs TWO programs off one payload, the
  earlier fix gated the first, and every check that existed drove hook EVENTS
  rather than every PROGRAM on each line, so nothing could see the second.
  The gate now sits on each command, and an inventory test reads
  `hooks/hooks.json` and fails if any hook-wired `bm_telemetry.py` command
  lacks a consent check, so the next hook cannot reopen the class. The
  automatic session hooks no longer default the vault to
  `~/BrotherModeVault` on their own the first time they fire; they simply do
  not write until `scripts/setup.py` has recorded a vault path, and setup
  itself never creates the vault directory, only records the path a founder
  chose. What is still NOT true: the guided `/brotherme-start` skill flow
  and this CLI-based setup are two separate entry points that have not been
  unified into one first-run experience, and `docs/specs/canonical-project-
  protocol.md` remains the longer-term direction, not what shipped here.

## The rc.9 install gap, found by the Loop 9 preliminary refuter pass (2026-08-02)

Three related facts, all true at once, all resolved only by the founder
cutting the next release tag at program end:

- **The pinned install commands install the pre-fix tree.** Every install
  page pins `v2.0.0-rc.13`, the last resolvable tag, per the Loop 0
  version law. But rc.9 predates every commit of the release-closure
  program, so a user installing today gets the acknowledged-broken
  five-event hand-wiring blocks, no Bash-write detection, and none of
  loops 1 through 8. The release branch's own install path does not
  install the release branch. This is the designed cost of refusing to
  tag mid-program (a late rc.10 or rc.11 tag would have recreated the
  rc.8 two-trees ambiguity); it stops being true the moment the next tag
  is cut and the three doc pins move to it.
- **rc.9 cannot read a store this branch has touched.** rc.9 code
  understands store schema 11; the program's Loop 1 migrated the schema
  to 12, and the Memory Sentinel (Full-Auto Phase 1, 2026-08-02) moved it
  again to 13. An rc.9 install pointed at that store refuses loudly at
  session start ("store schema_version is 13 but this BrotherMode
  understands at most 11. Upgrade BrotherMode; do not downgrade the
  store.") and touches nothing, so the mismatch is safe but noisy. The
  founder's own machine shows this warning every session for exactly
  this reason. It ends when the live install is upgraded past the
  schema-13 migration.
- **doctor's wiring check reads 1 of 7 hook groups.** Check 8's healthy
  verdict confirms the PreToolUse fence entry and nothing else: an
  install missing SessionEnd, Stop, PreCompact, PostToolUse and both
  Bash-audit groups (telemetry, autosave and the Loop 6 detection all
  dead) still prints "All 10 checks passed". Widening the check to all
  seven groups is a post-freeze fix; until then, the mechanical
  cross-check is `python3 tools/test_install.py`, whose shape assertions
  do read all seven.
