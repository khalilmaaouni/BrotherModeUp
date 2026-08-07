# Current limits

Status: CURRENT.

What this project does NOT do, has NOT proven, or has only partly checked, as
of today. This page carries ONLY still-open limits: an entry that has since
been fixed belongs in dated evidence, not here. The full, dated history of
every limit ever found and every fix that closed one lives in
`docs/KNOWN-LIMITS.md`, which this page distills rather than replaces; read
that file for the reproduction steps, the exact commits, and the entries
already marked FIXED, RESOLVED, or CLOSED that are deliberately left out of
this list.

## The reachable surface is bigger than the advertised nine

Several shim files under `commands/` describe themselves as "not part of the
nine advertised in `/help`". That "nine" is real (it is the count of v3
skill directories whose own header calls them a "canonical replacement",
`tools/test_bm.py` counts the same nine as "the v3 rename adds nine
canonical skill directories"), but it is nine out of a reachable surface of
32 files that answer to some typed name, not 32 out of 32. Counted
mechanically: `skills/` holds 17 directories, `commands/` holds 15 legacy
shim files.

The 32 breaks down honestly as:

- **Nine, public and canonical.** `help`, `next`, `review`, `start`,
  `status`, `update`, `view`, `deliver`, `doctor`: each is what `skills/
  help/SKILL.md` calls the short, first-time list (`start`, `status`,
  `next`, `help`) plus the five it names as reachable but more advanced
  (`view`, `review`, `deliver`, `update`, `doctor`).
- **Seven, internal and hidden, but still directly typeable.** `auto`,
  `auto-status`, `brief`, `decisions`, `handback`, `handover-pack`, `stop`:
  `user-invocable: false` or `disable-model-invocation: true` in their
  frontmatter, so Claude Code does not list them in the `/` menu and does
  not auto-invoke them from ordinary conversation, but a user who types the
  exact name reaches them directly. Each carries its own "v3 note"
  explaining why it is hidden rather than removed.
- **One conductor.** `skills/brotherme/SKILL.md`, the file `/brothermode`
  itself resolves to; it runs the deep-tour flow and orients a first-time
  user toward the rest. `skills/help/SKILL.md`'s own reference answer, when
  asked to list everything, names all sixteen skills above (nine plus
  seven) grouped into four short sets; it does not separately call out
  which are hidden from the `/` menu, only that some are "the more advanced
  layer."
- **Fifteen, legacy v2 compatibility shims.** `commands/brotherme-*.md`,
  kept unchanged so a v2 install or a v2 habit still resolves during the
  migration window. Each names its own removal condition in its own header:
  the v3.0.0 tag, once `claude plugin validate` and a repository grep show
  no live consumer of that specific `/brotherme-X` command remains. The
  replacement path for every one of them is named in the same header line:
  the matching `/brothermode:X` skill. Removing the shims without that
  per-file check, or before v3.0.0, would make the reachable surface
  shrink with no user-facing notice; the condition exists so that cannot
  happen silently.

Nothing above is a defect in the product's behavior: every one of these 32
files does what it says. The limit is documentation honesty, stated plainly
here because it was not stated plainly enough anywhere a reader would find
it first: a reader who takes "nine" as the whole surface, without the
breakdown above, will undercount the real surface by more than three times.

## What is enforced, and what is only detected

- **Bash writes are detected, not prevented, with one exception.** The one
  writer per file guarantee is enforced by a hook for the Claude Code write
  tools (Edit, Write, MultiEdit, NotebookEdit) and for one specific Bash
  shape: an `apply_patch` envelope naming a fenced path, the form every
  Codex CLI file write takes. Every other Bash write (redirection, `sed -i`,
  `tee`, `git checkout`, an inline interpreter script, any other subprocess)
  still reaches the filesystem without passing a hook that can refuse it.
  What changed is that a fenced file changed by an unrecognized Bash call is
  no longer invisible: `tools/bm_bash_audit.py` snapshots every fenced file
  before a Bash call and re-hashes it after, raising an alert when the hash
  moved and the acting session was not the fence's owner. That is detection,
  stated as such in `docs/HOOKS.md`, never prevention. See
  `docs/KNOWN-LIMITS.md`, the Bash-write fence entry, for the exact refused
  and detected shapes.
- **The fence does not fire under OpenAI Codex CLI's exec path.** Measured
  2026-08-07 on Codex CLI 0.146.0: a live run overwrote a file another
  session had claimed, twice, and a marker probe proved the PreToolUse hook
  never executed there, with configuration syntax, project trust, and
  hook-trust bypass all ruled out
  (`docs/mistakes/M19-the-codex-fence-does-not-fire-in-exec-mode.md`). Under
  Codex, BrotherMode is an instruction file plus a working command line, not
  an enforcement layer; `docs/RUNTIMES.md` and `capabilities.status.json`
  state the same fact.
- **The fence and driver ownership checks are coordination, not access
  control against a hostile local actor.** A session's identity is a value
  it asserts and the store records; any process running as your own user
  can read the same token file and act as that session. This keeps
  cooperating sessions from colliding and records who did what; it is not a
  defence against a hostile process already running as you, which already
  has the run of your filesystem. A real trust boundary needs separate
  operating system accounts or machines, not separate BrotherMode sessions.
- **Hooks are cooperative enforcement with no sandbox underneath them.** No
  container or operating system sandbox is provided; every guarantee above
  depends on Claude Code actually running the hook it was told to run.

## The fence hook and the store: six measured holes (2026-08-08)

Found in the same closure pass that produced the rest of this page,
reproduced against the exact files and line numbers named below rather than
asserted from a description. None of the five code-level holes is fixed
here: each sits in `tools/bm_fence_hook.py` or `tools/bm_store.py`, the
fence's own core, and this closure's own rule forbids touching that core to
close a review finding with anything but a narrow, safe diff; each stays a
published limit instead, with the fix it needs stated plainly so it is not
lost. The sixth item is a configuration change this pass DID make, listed
here because it exists to answer the first hole below.

- **Sub-agent profiles no longer default to a separate git worktree.** Was
  `isolation: worktree` in `agents/builder.md` and `agents/fast-worker.md`;
  removed 2026-08-08, because the fence does not resolve a claim across a
  worktree boundary (the next entry), so the isolation those two profiles
  asked for by default was quietly weaker than it looked: a claim filed
  inside the worktree and a write from outside it, or the reverse, could
  pass each other unrefused. A caller that still wants worktree isolation
  for an unrelated reason (a genuinely parallel, disjoint-file task) can
  request it explicitly; it is no longer the default for scoped
  implementation or bulk mechanical work.
- **The fence does not resolve a claim across a git worktree boundary
  (H1).** A nested worktree (for example `.claude/worktrees/<name>/`)
  carries no `.brothermode/` of its own, so `tools/bm_store.py`'s
  `resolve_root` (line 305) climbs to the OUTER repository that does.
  `tools/bm_fence_hook.py`'s `canonical_target` (line 340) then computes
  the write's target relative to that OUTER root, which is the
  worktree-prefixed path (`.claude/worktrees/<name>/<file>`), never the
  plain path a claim filed on `<file>` inside the worktree actually stores.
  A claim on a file shared between the outer tree and a worktree therefore
  matches neither the worktree's own write nor a second worktree's, and the
  fence allows a write it should deny. Reproduced directly against
  `resolve_root` and `canonical_target`; the fix belongs to one or both of
  those two functions, judged too wide a diff for this closure to attempt
  safely, so it stays a published limit rather than a rushed patch to the
  fence's own core.
- **An `apply_patch` heredoc is unparsed, and therefore unfenced, in two
  common shapes.** `tools/bm_fence_hook.py`'s `_command_word` (line 453)
  takes the first token on a heredoc's operator line as the command, with
  no special case for the `command` builtin, so `command apply_patch
  <<'PATCH'` is read as the command `command`, not `apply_patch`, and its
  body is never checked. Separately, `_find_heredoc_ops` (line 476) only
  accepts alphanumeric characters and underscore inside a quoted heredoc
  delimiter, so a delimiter such as `'PATCH-END'` fails its own
  closing-quote check and the whole heredoc is dropped rather than parsed.
  Both paths return zero parsed bodies, and `decide()` (line 787) takes the
  empty-bodies allow path with no claim check at all. Reproduced directly
  by calling `apply_patch_bodies()`: one parsed body for a plain
  `apply_patch <<'PATCH'`, zero for either variant above. Under Codex CLI
  every file write arrives as exactly this kind of heredoc
  (`docs/mistakes/M19-the-codex-fence-does-not-fire-in-exec-mode.md`), so
  this is a real bypass for two plausible command shapes, not a contrived
  one.
- **`BROTHERMODE_ROOT`, if set in the environment, is never cross-checked
  against the file actually being written.** `resolve_root` (`tools/
  bm_store.py`, line 343) reads `os.environ.get("BROTHERMODE_ROOT")` and
  gives it absolute precedence over the hook payload's own `cwd` whenever
  it names an existing directory, with no check that it has anything to do
  with the write in front of it. A stale or simply wrong inherited value
  makes the fence hook consult the wrong store; the real write target then
  canonicalizes outside that mistaken root and is silently allowed.
  Reproduced by reading the call path from `bm_fence_hook.py` into
  `resolve_root` through to the allow decision; no test in this project's
  suites exercises a stale or hostile inherited `BROTHERMODE_ROOT` value,
  only scrubbing it from a test's own environment to avoid pollution.
- **Path case-folding is decided by `sys.platform`, not by the filesystem
  actually in use.** `tools/bm_store.py`'s `_CASE_INSENSITIVE_PLATFORMS =
  ("win32", "darwin")` (line 486) treats every Linux mount as
  case-sensitive. A case-insensitive Linux mount (SMB, CIFS, WSL's
  `drvfs`, a casefolded ext4 volume) can map `src/Foo.py` and `src/foo.py`
  to the same file while the fence's own `paths_overlap` (line 564) still
  treats them as two different claims, so a foreign claim can be worked
  around with a different case spelling on such a mount. Not currently
  caught anywhere in this project's suites.
- **A WAL journal mode request is never confirmed to have taken effect.**
  `Store.__init__` (`tools/bm_store.py`, line 6216) runs `PRAGMA
  journal_mode=WAL` and discards the value SQLite hands back, which names
  the mode that actually took effect, not necessarily WAL: some
  filesystems (documented by SQLite itself, notably some network and
  remote mounts) silently keep another mode. `_connect_read_only` later
  treats the absence of a WAL sidecar file as license to open with
  `immutable=1`, which skips normal locking. On a filesystem where WAL
  silently failed to engage, a concurrent writer using a different journal
  mode could then be read with no lock coordination at all. Only a test
  (`tools/test_bm_store.py`'s `test_pragmas_are_set`) checks the mode that
  actually took effect, on the machine running the suite; production
  `Store.__init__` never re-checks it. The named follow-up: assert the
  fetched pragma value at startup rather than discarding it, and fail
  loudly, or fall back to a locking strategy that does not assume WAL,
  when it disagrees.
- **`_refresh_state_view`'s own "warn, never raise" promise has one
  uncaught exception class.** (`tools/bm_store.py`, line 16831) catches
  only `RedactionUnavailable` and `OwnershipRefused`. An `OSError` from the
  underlying atomic write (disk full, EIO, a permission change mid-run) is
  neither of those two, and is not a `StoreCorrupt` either, so it escapes
  to the CLI's generic exception handler and exits 1 as an unexpected
  failure, even though the claim it was refreshing the view for already
  committed in its own transaction beforehand. The caller is told the
  operation failed while an active claim and fence actually remain in the
  store. The named follow-up: catch `OSError` alongside the two exception
  types already caught here, and warn rather than raise, matching the
  function's own stated intent.

## Recovery

Recovery material is compact-boundary autosave snapshots plus store,
registry, and vault continuity, not a continuous backup. A hard kill between
two compactions loses uncommitted working tree state from that window: the
autosave hook runs on the PreCompact boundary, so nothing protects the time
between one compaction and the next. Always-on autosave between compactions
exists as an opt-in (`BROTHERMODE_AUTOSAVE=1` plus a `PostToolUse` tick hook,
`docs/QUICKSTART.md` step 3) and is not the default; wiring it on by default
is a new capability, out of scope for this release. `tools/bm_autosave.py
recover` is the restore path, and the recovery suite proves the snapshot it
takes byte-compares back correctly.

## Hook performance

Investigated as a dedicated measurement pass with a 40 percent median
reduction target on the Bash and Stop hook chains. The result, both measured
and honestly published rather than tuned to look better: no change to
`hooks/hooks.json` was safe to make without breaking a currently-green,
differently-owned test (the consent-gate program-count floor, the Stop
chain's own program-count pin, and the hand-wiring blocks in
`docs/QUICKSTART.md` and `docs/SETUP.md` that must stay byte-identical to
`scripts/install.py`). The best achievable reduction this pass could
quantify, as a projection rather than an applied change, is roughly 10 to 14
percent on the Stop and PreCompact chains, well short of the 40 percent
target. Full method, the exact blockers, and the projection arithmetic are in
`docs/evidence/v3/hook-performance.md`; `docs/PERFORMANCE.md` carries the
generated, currently-shipping cost table.

## Platform support

- **Windows.** The installer refuses on Windows and names the reason; WSL
  works. Only the store job in `.github/workflows/tests.yml` runs on
  `windows-latest`; the suite and gate jobs run on Linux and macOS only, so
  the fence hook suite in particular has never executed on a Windows
  runner. Recovered work being readable only by you (a POSIX file mode of
  `0700`) is unverified on Windows, which governs access by ACLs instead;
  the tool reports the mode it actually achieved rather than the mode it
  wanted, so it does not overstate the guarantee, but a Windows user on a
  shared machine should treat recovered work as potentially readable by
  other local accounts until a real ACL call closes this.
- **Everything is verified on Claude Code only.** `docs/RUNTIMES.md` states
  which runtimes have hook points at all; having a hook point is not the
  same claim as BrotherMode's own hooks running there. No other runtime was
  driven end to end: the generated instruction files under
  `docs/runtimes/` are documentation-verified, not behaviour-verified.

## Retrieval

- **Lexical matching is the default and the only mode most stores use.**
  Ranking is BM25 term-frequency arithmetic; there are no embeddings, and a
  task that shares no words with a rule finds nothing unless the rule is a
  gate.
- **The optional FTS5 fast path is English stemming, not semantic
  matching.** The tokenizer folds case and accent for any script, but its
  stemmer is Porter, English only; a French or Japanese query gets whole-run
  text matching or nothing, never stemmed matching. The measured gain rests
  on one labelled fixture (a stemming pair, "pushing" against "pushed"), not
  a graded corpus at scale.

## The Full-Auto controller (beta)

`tools/bm_controller.py` is measured by its own suite, including a crash and
resume run, and stays beta rather than certified: nobody outside this
project has run it, and several edge cases raised by adversarial review
remain open by design rather than by oversight. The three most consequential:

- **Two real controller processes contending for one store file have never
  been exercised.** Every concurrency probe to date ran inside a single
  process with a delegating wrapper simulating the competing write, which is
  a faithful simulation of the interleaving and not a test of two operating
  system processes against one SQLite file.
- **A unit that declares no write scope is still dispatched and claims an
  empty fence.** A contract with no `allowed_paths` at all is now refused
  outright, but a unit inside a legitimately signed contract whose own
  `write_scope` is `[]` is still judged on its risk class alone. Until this
  is decided, every unit needs an explicit write scope.
- **Controller unit ids are one global namespace across the whole store.**
  Two projects sharing one store cannot both use a unit called the same
  name; the collision is refused cleanly rather than corrupting anything,
  but the fix is a schema change, not yet made. Prefix unit ids per project.

The full, dated list of what each adversarial round closed and left open is
`docs/KNOWN-LIMITS.md`'s L03 sections; `docs/FULL-AUTO.md` is the product
page.

## The live project view and publishing

- **The page is a snapshot, not a live view.** It cannot read your project
  records when you open it; it is only as fresh as the last time it was
  written.
- **Publishing it as a shared page needs conditions this product does not
  control.** A Pro, Max, Team, or Enterprise plan, a session signed in with
  `/login`, the Anthropic API as the model provider, an organisation without
  CMEK, HIPAA, or Zero Data Retention, and Claude Code 2.1.183 or later. It
  is off by default in Agent SDK, GitHub Action, and MCP server contexts,
  and a session using an API key, a gateway token, or a cloud provider
  credential cannot publish at all. The file on disk is what this product
  promises; the published page is an addition that can be unavailable.
- **Nothing on the page can act on your project.** There is no path from a
  button on the page back into a running session; taking a decision back
  copies the exact words for a paste you make yourself.

## What has not been measured at scale

- **Real use exists; graded outcomes do not.** The correction-learning
  system is built and tested, and the founder reports weeks of his own daily
  use plus other people using it on their own machines. None of that use is
  MEASURED: there is no counted set of projects, no recorded rework rate,
  and no comparison against working without the tool.
- **The comparative benchmark is internal evidence only.** Every number the
  harness produces is self-graded, on one machine, with no outside user; it
  compares two configurations of the same model against each other and
  nothing else, is not a market claim, and does not rank BrotherMode against
  any other product. `docs/BENCHMARK-COMPARATIVE.md` states this on the page
  the numbers live on; no page in this repository may cite a benchmark
  number as anything more than that.
- **The documentation consistency suite checks a named list of pages, not
  every page.** `tools/test_bm_docs.py`'s `ACTIVE_DOCS` list is what stays
  current by mechanical check; a page outside that list can carry a stale
  claim in prose that nothing catches. `docs/KNOWN-LIMITS.md` names which
  pages are outside it today.

## Where the rest of this lives

`docs/KNOWN-LIMITS.md` is the full, dated record this page distills, kept
exactly as written on the day each entry was found or closed, including the
entries already marked FIXED, RESOLVED, or CLOSED that this page leaves out.
Resolved incidents with their own write-up live under `docs/closure/` and
`docs/evidence/`, each dated and stated as historical on its own page.
Evidence for a specific claim above is cited inline, next to the claim it
supports.
