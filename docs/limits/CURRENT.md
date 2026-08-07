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
