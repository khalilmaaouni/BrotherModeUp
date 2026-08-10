# Agent 2, Architecture Refuter: refutation of the v3 freeze

HISTORICAL. Written 2026-08-07 and committed unchanged on 2026-08-10.
An adversarial review of the freeze document beside it, kept verbatim because a
findings list rewritten by the party it judges stops being independent. It uses
the pre-rename product name in places; that name is retired and those mentions
are part of the record, not current usage. For what is true today read
`docs/limits/CURRENT.md`.
Superseded by `docs/limits/CURRENT.md` as a source of current status.


Target: `~/Documents/BrotherModeUp-handovers/V3-FREEZE-2026-08-07.md`
Plan: `~/Downloads/BrotherMode_v3_Gap_Closure_Execution_Plan.md`
Evidence repository: `<repo root>/.claude/worktrees/silly-dubinsky-bb7735` (branch `fix/r3-installed-arm`)
Model tier: opus, effort xhigh. Read-only. No repository or git writes, no suite runs.

Counts: 5 BLOCKER, 6 HIGH, 5 MEDIUM, 4 LOW.

Every BLOCKER and HIGH below carries a line "Freeze answers it?" per the plan's
gate rule (plan section 14: architecture may not freeze while an unexplained
BLOCKER or HIGH remains).

---

# BLOCKER

## B1. Freeze answer 11 promises killed-session recovery from mechanisms that cannot restore a killed session

**Mechanism.** Freeze answer 11 states recovery is "store rows plus STATE.md
registry plus vault session log". None of those three restores working-tree
files, and the component that does is not named.

The only producer of restorable snapshots is `tools/bm_autosave.py`, which
writes git snapshot refs and whose `cmd_recover` (line 1788) checks the
snapshot out into a NEW git worktree (line 1821, `_prepare_recovery_worktree_dir`,
line 1759). That producer has exactly two entry points:

- `cmd_precompact` (line 1620), wired at PreCompact in `hooks/hooks.json` line 44
  and in `scripts/install.py` line 165.
- `cmd_tick` (line 1649), documented in its own docstring as the "PostToolUse hook
  target, opt-in via `BROTHERMODE_AUTOSAVE`".

`cmd_tick` is wired in **neither** install path. `hooks/hooks.json` PostToolUse
carries one command only, `tools/bm_bash_audit.py post`. `docs/HOOKS.md` line 541
states the shipped shape is "six wired events and seven hook commands", and
`tools/test_install.py:123` (`test_wires_all_six_events_including_the_fence`)
hard-asserts it. Even where the tick is wired by hand it returns immediately
unless `BROTHERMODE_AUTOSAVE` is set (line 1659).

**Reasoning path.** A kill is not a compaction. `kill -9`, a crashed terminal, an
OOM, a power loss, or the founder pressing Ctrl-C never fire `PreCompact`.
Therefore a session that was killed before it ever compacted has zero snapshot
refs, and `bm_autosave.py recover` has nothing to check out. The freeze's own
proof requirement in the same answer ("the recovery canary must byte-compare
restored fixtures") will pass only if the canary triggers a compaction first,
which is not what "killed-session recovery" means and is not what the plan's
canary describes (plan lines 844 to 852: "create modified + untracked fixture,
trigger recovery snapshot path, destroy fixture working state, recover,
byte-compare"). The phrase "trigger recovery snapshot path" is where the gap
hides: in the shipped product nothing triggers it on a kill.

**Affected files.** `tools/bm_autosave.py:1620,1649,1659,1788,1821`;
`hooks/hooks.json:38-52` (PreCompact) and `:56-70` (PostToolUse);
`scripts/install.py:159-168`; `docs/HOOKS.md:541`; `tools/test_install.py:123`.

**Acceptance condition for closure.** The freeze names the actual restorer
(`bm_autosave` git snapshot refs) as the recovery authority, and either (a) the
run wires an always-on snapshot trigger that fires without compaction and proves
it with a canary that kills the session process rather than compacting it, or
(b) the freeze restates answer 11 as "recovery of compacted sessions only" and
`docs/limits/CURRENT.md` carries the kill-without-compaction case as a stated
limit. A canary that compacts and calls that a kill does not close this.

**Freeze answers it?** No. The freeze names three mechanisms, none of which is
the restorer, and never mentions `bm_autosave` or the compaction precondition.

---

## B2. STATE.md is declared a generated view and a source of truth at the same time, and the freeze picks both

**Mechanism.** Two live, current authorities disagree in the tree today:

- `tools/bm_store.py:23`: "`STATE.md` is a GENERATED view, never hand-edited
  truth: `render_state_md`/`write_state_view` regenerate it".
- `STATE.template.md:3-4`: "It is the single source of truth for in-flight work:
  any compaction, kill, or new session resumes from this file, never from
  memory."

Freeze answer 3 endorses the first ("Views ... are renders, never authorities").
Freeze answer 11 endorses the second (STATE.md as recovery registry). The freeze
therefore ratifies both sides of a contradiction that plan law 5.5 ("No two
active authorities ... project state") exists to forbid.

**Compounding fact.** `.gitignore:3` excludes `STATE.md`, and
`tools/bm_store.py:5501` appends `.brothermode/`, `threads/` and `STATE.md` to the
git common-dir excludes. `tools/bm_autosave.py:119-120` states plainly that
`git add -A -- .` "never stages a path that `.gitignore`, `.git/info/exclude`, or
the global excludesFile already" ignores. So the recovery snapshot mechanism
provably cannot contain STATE.md, the store, or `threads/`. A worktree produced
by `bm_autosave.py recover` is state-less by construction.

**Acceptance condition for closure.** One sentence in the freeze naming STATE.md
either a render (in which case answer 11 drops it and the store is the only
durable half) or an authority (in which case answer 3 is amended and
`STATE.template.md`'s claim is either enforced or deleted), plus a test that
fails if the two files disagree again, in the shape of the existing identity test
`tools/test_bm_docs.py:3807`.

**Freeze answers it?** No. The freeze contains both positions and reconciles
neither.

---

## B3. The rename revokes a ratified, machine-enforced identity contract without recording the decision, and the twelve breaks it enumerates are unowned

**Mechanism.** `product.identity.json` (root, `"updated": "2026-08-04"`) and
`docs/brand/IDENTITY-CONTRACT.md` ("Status: CURRENT as of 2026-08-04") are a live
contract that deliberately splits the namespace:

- `durable_state_namespace.spelling = "brothermode"`, "Everything a user already
  has written to disk. Renaming any of these breaks a real install."
- `code_identity_namespace.spelling = "brotherme"`, "Separate from the
  durable-state namespace on purpose, and permanently so." It owns `plugin id
  brotherme`, `marketplace id brotherme-marketplace`, `python import package
  brotherme`, `~/.brotherme/config.json`, `BROTHERME_CONFIG`.
- Contract section 2: "the split between them is permanent and intentional. It is
  not drift waiting to be tidied up ... unifying either direction would break real
  state on the disk of every person who has already installed the tool."

Freeze decision 1 unifies exactly the direction the contract forbids, and never
names the contract, its date, or the fact that a prior founder ratification is
being reversed. The founder's standing order-of-work rule states that deciding
not to do something the user explicitly chose is a DECISION that gets recorded
with its alternatives at the moment it is taken.

The contract is not advisory. `tools/test_bm_docs.py:3807`
(`test_the_identity_record_agrees_with_the_shipped_manifests`) reads
`product.identity.json`, `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` and `pyproject.toml` and refuses a
disagreement. Contract section 5 enumerates twelve surfaces where the rename
"breaks something a user already has", including the consent config
`~/.brotherme/config.json` and `BROTHERME_CONFIG` (76 occurrences in the tree,
created only by `scripts/setup.py:113`, removed only by `scripts/uninstall.py`),
the Python import package `brotherme/` (a real package: `brotherme/__init__.py`,
`brotherme/core/schema.py`, mapped in `pyproject.toml:92`), and the hook-ownership
marker `brothermode-install.json` (`scripts/install.py:128`).

The freeze's Wave A ownership skeleton assigns Lane A `.claude-plugin/`,
`skills/`, plugin metadata, and Lane B the CLI, adapters and CLI contract tests.
`product.identity.json`, `docs/brand/IDENTITY-CONTRACT.md`, `pyproject.toml`,
`brotherme/`, `scripts/setup.py`, `scripts/uninstall.py` and `commands/` are in
neither lane's writable scope, yet the identity test fails the moment Lane A
touches `plugin.json` without a matching edit to `product.identity.json`.

**Reasoning path.** Lane A edits `.claude-plugin/plugin.json` `name` to
`brothermode`. `tools/test_bm_docs.py:3825` compares it against
`identity["plugin_id"]`, still `brotherme`. Lane A's done-check goes red on a file
Lane A does not own. Plan section 9: "A task that cannot name its writable files
is not ready to dispatch."

**Acceptance condition for closure.** The freeze records the reversal of the
2026-08-04 contract explicitly (what changed the call, what it costs), assigns an
owner lane for `product.identity.json`, `docs/brand/IDENTITY-CONTRACT.md`,
`pyproject.toml`, `brotherme/`, `scripts/setup.py`, `scripts/uninstall.py` and
`commands/`, and states per contract section 5 which of the twelve break surfaces
are renamed and which are held, with the release-note line each renamed one owes
an existing install.

**Freeze answers it?** No. Decision 1 asserts the rename and lists only skills,
plugin id, marketplace and CLI. It never names the contract it overturns, the
consent config, the Python package, or the ownership gap.

---

## B4. The compatibility-removal condition guarantees deletion of exactly the shims a real upgrade needs, and a renamed plugin id installs a second plugin rather than upgrading the first

**Mechanism, part one (the self-defeating condition).** Freeze answer 13 permits
`brotherme` shims "only if the migration canary needs them". Freeze answer 14
deletes, at the release court, "every shim without a live consumer", and the
court fails if an unexplained shim remains.

The migration canary is a **fresh** install (plan lines 809 to 828: "From a fresh
throwaway config/project: 1. add marketplace, 2. install BrotherMode ...").
A fresh install never runs the v2-to-v3 upgrade path. Therefore no shim can ever
acquire a "live consumer" inside the canary, therefore answer 14 deletes all of
them, therefore the only users a shim exists for (the five pilot installs and the
founder's own live install) lose their upgrade path at the release court by
construction.

**Mechanism, part two (double install).** Claude Code keys an installed plugin by
its id. Renaming `brotherme` to `brothermode` does not upgrade the installed
plugin; it publishes a different one. `commands/brotherme-update.md` teaches, and
`tools/test_bm.py:5764` and `tools/test_bm_consent.py:1333` pin, the literal
update lines `/plugin marketplace update brotherme-marketplace` and
`/plugin update brotherme`. Both keep resolving to the old identity. An existing
user who follows the shipped instructions and then installs the new one has two
plugins registered, and `hooks/hooks.json` ships with each: two SessionStart
chains, two consent probes, two `bm_fence_hook.py` PreToolUse registrations, two
`bm_bash_audit.py` pre and post pairs, two Stop chains each running
`bm_view.py render --if-stale` against the same project.

**Reasoning path.** `tools/test_bm_plugin_install.py:72-74` pins
`PLUGIN_NAME = "brotherme"`, `MARKETPLACE_NAME = "brotherme-marketplace"`,
`PLUGIN_ID = "brotherme@brotherme-marketplace"`. `README.md:214` publishes
`claude plugin install brotherme@brotherme-marketplace`. Change the id and every
published install line and the pinned test address a plugin that no longer
exists at that name, while the previously installed one keeps running its hooks.

**Acceptance condition for closure.** Either (a) the freeze adds an
**upgrade** canary distinct from the fresh-install canary, which installs v2
first, upgrades, and asserts exactly one hook chain and one consent config
afterwards, and makes that canary the "live consumer" test answer 14 keys off; or
(b) the freeze states plainly that v2 installs are abandoned rather than upgraded
and names the founder-facing uninstall-then-reinstall instruction and who
delivers it to the five pilot users. A removal condition of "v3.0.0 tag" with no
upgrade canary is not enforceable, because nothing at the tag can observe a
consumer.

**Freeze answers it?** Partially and incorrectly. Answers 13 and 14 exist and
name a default removal condition, but the condition is untestable against the
only canary the plan defines, and the double-install consequence is unaddressed.

---

## B5. Fifteen shipped public commands map to nine canonical skills; seven have no destination and the freeze is silent

**Mechanism.** `commands/` ships fifteen files, pinned by name in
`tools/test_bm.py:5708` (`test_exactly_seven_brotherme_commands_ship`, whose
`expected` list at lines 5725 to 5732 is the fifteen). The canonical v3 public
surface (plan section 3.2, freeze answer 4's CLI verbs) is nine.

Mapped: `start, status, next, review, deliver, view, help, update` (eight).
Introduced: `doctor` (no command exists today; `scripts/doctor.py` does).
**Orphaned, with no destination anywhere in the freeze or the plan:**
`brotherme-auto.md`, `brotherme-auto-status.md`, `brotherme-stop.md` (the
Full-Auto controller family, backed by `tools/bm_controller.py`, 5,804 lines, and
`docs/FULL-AUTO.md`), `brotherme-brief.md`, `brotherme-decisions.md`,
`brotherme-handback.md`, `brotherme-handover-pack.md` (the founder-mode family).

`tools/test_bm.py:5712-5720` records their provenance explicitly: "L03 added the
three Full-Auto controller commands ... a deliberate new family ... L04 adds four
more (brief, decisions, handback, handover-pack), the founder-mode family".

**Reasoning path.** Plan section 3.2: "No additional public skills are introduced
in this run", so the seven cannot become skills. Plan section 2.1 item 2 says to
"remove duplicated/legacy current-facing command semantics once proven
equivalent", but these seven have no v3 equivalent to prove against. Plan section
2.2 forbids new features but says nothing about removing shipped ones. So Lane A
faces three illegal options: keep `commands/` (contradicts freeze decision 1 and
the "eliminate current-facing naming duplication" requirement), create seven more
skills (contradicts 3.2), or delete seven working public capabilities (an
unauthorized product change, and it strands `bm_controller.py`'s entire public
surface).

**Acceptance condition for closure.** The freeze states, per orphan, one of:
promoted to a canonical skill (with the 3.2 list amended and the founder told the
public surface grew), demoted to an internal skill hidden from the slash surface
(plan 3.3 last line permits this), or retired (with the founder's answer recorded
before Wave A dispatches, because retiring Full-Auto is a product decision, not a
migration detail).

**Freeze answers it?** No. The freeze's answer 4 lists ten CLI verbs and its
decision 1 lists the skill namespace; neither mentions the seven, and the Wave A
ownership skeleton does not name `commands/` at all.

---

# HIGH

## H1. Worktree isolation and the one-writer fence do not compose; freeze answer 10 asserts both as if they did

**Mechanism.** Freeze answer 10: "one writer per fence, worktree isolation for
parallel writers, two active writer worktrees maximum". These two controls
conflict at the path level.

`tools/bm_fence_hook.py:868` calls `bs.resolve_root(cwd or None)` with
`refuse_past_git_boundary` left at its default `False`
(`tools/bm_store.py:340-390`). Verified on disk: the main repository
`<repo root>` HAS `.brothermode/`; the worktree
`<repo root>/.claude/worktrees/silly-dubinsky-bb7735`
does NOT. Because Claude Code nests worktrees inside the repository, the marker
walk climbs out of the worktree and returns the main repository as `root`.

`canonical_target(root, raw, cwd)` (`tools/bm_fence_hook.py:340`) then computes
the target as a path relative to that main root. A writer in worktree A editing
`pyproject.toml` yields `.claude/worktrees/A/pyproject.toml`. A writer in
worktree B editing the same logical file yields `.claude/worktrees/B/pyproject.toml`.
A claim filed on `pyproject.toml` matches neither. Two writers can edit the same
logical file simultaneously and the fence never fires.

**Second half.** `enforced_mode` (`tools/bm_fence_hook.py:675`) documents that
fail-open is the DEFAULT and unchanged, and lists nine conditions that each
allowed a write across another session's active fence, including "store present
with ZERO active claims, which is the state a fresh project sits in".
`fence_mode` (line 654) returns advisory unless `BM_FENCE_MODE=enforced`. Freeze
answer 8 says "PreToolUse fence deny ... stays blocking and synchronous"; by
default it does not deny at all.

**Acceptance condition for closure.** The freeze states which of the two controls
is authoritative for this run, and if the fence is claimed as live it names
`BM_FENCE_MODE=enforced` in the dispatch environment, requires claims to be filed
in the shared root store before each writer starts, and adds a canary that proves
a cross-worktree collision is refused. Otherwise answer 10 drops the fence for
parallel writers and says plainly that worktree disjointness plus Fable's
integration order is the only isolation, with the ledger as the audit trail
(`docs/HOOKS.md:385-392` already states this limit).

**Freeze answers it?** No. Answer 10 lists both mechanisms without noticing that
worktree nesting defeats the fence's path matching, and answer 8 describes the
default mode incorrectly.

---

## H2. Wave A runs two lanes in parallel on a dependency, and their writable scopes overlap on four files neither owns

**Mechanism, ordering.** The freeze's amendment A4 keeps the plan's wave order.
Plan section 15 runs Lane A (semantic surface) and Lane B (runtime boundary) in
parallel, then states the integration order as "1. runtime contract, 2. semantic
surface". Lane A's mission is to rewrite public skills so they call the
`brothermode` CLI (freeze answer 4: "Skills call ONLY it"). That CLI does not
exist until Lane B ships it. Lane A must therefore either write skills against an
unwritten contract or keep the `tools/bm_*.py` calls it was dispatched to remove.

**Mechanism, ownership.** Files both lanes must write, owned by neither in the
freeze's skeleton:

- `pyproject.toml`. Lane A needs `[project] name` and version semantics
  (`pyproject.toml:40`, pinned against `product.identity.json` by
  `tools/test_bm_docs.py:3818`). Lane B needs a `brothermode` entry in
  `[project.scripts]` (line 66) and, if the Python package moves, `package-dir`
  (line 92) and the explicit `py-modules` list (line 97), which
  `tools/test_bm.py`'s packaging test already fails on when it disagrees with
  `tools/`.
- `product.identity.json`. See B3.
- `tools/test_bm.py` (the largest single test file in a 63,156-line suite). Lane A
  owns the command and skill pins at 5668 to 5835 and 6946 to 6992; Lane B's
  "CLI contract tests" have no other natural home given the suite's flat layout
  (test reorganization is Agent 8, Wave C).
- `commands/`. Unowned entirely, and it is the source of Lane A's migration.

**Reasoning path.** Plan section 9: "If implementation discovery reveals
overlapping write responsibilities: stop the affected lanes, redraw boundaries,
do not let the agents negotiate file ownership while writing." Combined with H1,
the mechanical guard that would catch the collision is not active across
worktrees, so the first symptom will be a lost edit at integration.

**Acceptance condition for closure.** The freeze's full Wave A ownership table
(which it defers to dispatch) assigns each of the four files to exactly one lane
and forbids it to the other by name, and Lane A's dispatch either follows Lane B's
CLI contract landing (serial) or is scoped to naming and metadata only, with the
CLI call-site rewrite moved to a later, dependent lane.

**Freeze answers it?** No. The skeleton names three path groups for Lane A and a
description for Lane B, and says the full table is "written at dispatch". The
overlap is not visible in what is frozen.

---

## H3. Four shipped tests currently mandate the opposite of the v3 law, and the plan forbids deleting them without an equivalence proof

**Mechanism.** These are not incidental name pins; they encode the pre-v3
architecture as a requirement.

1. `tools/test_bm.py:5741` (`test_the_five_store_backed_commands_name_the_mechanical_command`)
   requires each of five command files to contain the literal string
   `python3 tools/bm_project.py <verb>`, with the stated rationale that "a command
   file that never names the mechanical command leaves the model free to answer
   from memory". Freeze answer 4 requires the exact opposite: skills call only the
   `brothermode` CLI, and `tools/bm_*.py` become internal adapters.
2. `tools/test_bm.py:5806` requires the beginner conductor to contain
   `bm_docs.py generate`. Same conflict.
3. `tools/test_bm.py:6963` (`test_every_bm_tool_invocation_names_claude_plugin_root_or_a_fallback`)
   carries a `known_bare` allowlist of **exact file and line numbers**
   (lines 6982 to 6992: `commands/brotherme-auto.md:10`, `skills/brotherme/SKILL.md:43`,
   and nine more). Any rename, move, or reflow of those files invalidates every
   entry, and the test's failure message instructs the next editor to add new
   entries rather than to notice the files moved.
4. `tools/test_install.py:123` hard-asserts the six-event, seven-command hook
   shape that Agent 5 (Wave B) is dispatched to consolidate, and
   `docs/HOOKS.md:541-545` states that "removing either entrypoint turns the suite
   red".

**Reasoning path.** Plan section 17 rule: "preserve old complete gate until
replacement proves equivalent or stronger; no test deletion without coverage
equivalence proof". Tests 1 and 2 have no v3 equivalent because the behavior they
protect is being removed on purpose. They must be **inverted**, not replaced, and
an inversion is not an equivalence.

**Acceptance condition for closure.** The freeze names these four pins, states
that inverting a pin whose protected behavior is deliberately retired counts as
closure under section 17, and requires each inversion to carry the freeze answer
number that authorizes it in its docstring. The line-numbered allowlist at
`tools/test_bm.py:6982` is rewritten to key off content rather than line numbers
before any file it names is moved.

**Freeze answers it?** No. The freeze does not mention the test suite except
through the plan's general rules.

---

## H4. "One deterministic public runtime boundary" has no enforcement, and four other public entry points survive it

**Mechanism.** Freeze answer 4 declares the `brothermode` CLI the single public
runtime boundary and says `tools/bm_*.py` become internal adapters. Nothing in the
freeze removes or hides the surfaces that make that false:

- `pyproject.toml:66-83` installs **seventeen** console scripts on the user's
  PATH: `bm-store`, `bm-threads`, `bm-telemetry`, `bm-learn`, `bm-packs`,
  `bm-docs`, `bm-docs-export`, `bm-runtimes`, `bm-score`, `bm-project`,
  `bm-ledger`, `bm-sentinel`, `bm-autonomy`, `bm-controller`, `bm-lead`,
  `bm-view`, `bm-statusline`. Adding an eighteenth named `brothermode` produces
  eighteen public entry points, not one. `docs/brand/IDENTITY-CONTRACT.md`
  section 2 additionally states "the console prefix stays `bm-` ... None of the
  three changes."
- `mcp/bm_mcp_server.py` is a second live runtime surface reading the same store,
  with its own documented safety model (`mcp/README.md`). The freeze never
  classifies it.
- `hooks/hooks.json` invokes `tools/bm_telemetry.py`, `tools/bm_lead.py`,
  `tools/bm_view.py`, `tools/bm_autosave.py`, `tools/bm_fence_hook.py`,
  `tools/bm_bash_audit.py` and `tools/bm_sessionstart.sh` directly. Those calls
  are the plugin's own, not a skill's, but they are the runtime, and freeze
  answer 4's "one boundary" does not cover them.
- `tools/bm_sessionstart.sh` itself spawns four further Python processes
  (`scripts/setup.py --consent-state`, then three `bm_telemetry.py` invocations).

There is no done-check in the freeze that would fail if a skill kept calling
`tools/bm_project.py`. The plan's Agent 4 done-check says "public skills can
invoke only the stable boundary" but names no mechanism.

**Acceptance condition for closure.** A deterministic gate: a test that greps
`skills/` for `bm_[a-z_]*\.py` and `bm-[a-z-]+` and fails on any hit outside an
explicit, dated allowlist; plus a freeze statement on whether the seventeen
console scripts stay public (in which case "single boundary" is a skill-facing
rule, and the freeze should say so) or are reduced (in which case the identity
contract's `bm-` clause is the third thing decision 1 overturns).

**Freeze answers it?** Partially. Answer 4 states the rule and names the
adapters, but supplies no enforcement and does not account for the console
scripts, the MCP server, or the hook-invoked scripts.

---

## H5. Freeze answers 8 and 9 misclassify the hook surface, and one misclassification is load-bearing for recovery

**Mechanism, four errors against `hooks/hooks.json` and the shipped code:**

1. **The consent gate is not a blocking hook.** Answer 8 lists it beside the
   PreToolUse fence deny as "blocking and synchronous". It is a
   `SessionStart`-time check inside `tools/bm_sessionstart.sh` lines 17 to 21
   that shells to `scripts/setup.py --consent-state` and, when not consented,
   prints one sentence and `exit 0` having written nothing. SessionStart hooks
   cannot deny anything. It is a write-suppression gate, not a blocking hook.
2. **The status line is not a hook at all.** Answer 9 lists "statusline" among
   informational hooks. `docs/STATUS-LINE.md:16-19` states, with a cited source,
   that a plugin's own settings.json "recognizes exactly two keys, `agent` and
   `subagentStatusLine` ... `statusLine` is not one of them, so a plugin cannot
   install a status line at all." `tools/bm_statusline.py` ships as the console
   command `bm-statusline` that a user pastes into their own settings. It is not
   in `hooks/hooks.json` and Agent 5 cannot consolidate it.
3. **PreCompact autosave is not a notification.** Answer 9 says "autosave
   notifications ... may consolidate or go async only where correctness cannot
   depend on them". `hooks/hooks.json:44` runs `bm_autosave.py precompact`, which
   per B1 is the **only** producer of recoverable snapshots in the shipped
   product. Correctness depends on it entirely, and making it async means
   compaction can proceed while the snapshot is in flight. The word
   "notifications" in answer 9 is the whole risk: an engineer reading only the
   freeze would classify it as droppable.
4. **PostToolUse bash audit is unclassified.** `hooks/hooks.json:60-68` runs
   `tools/bm_bash_audit.py post`, the retroactive fence-crossing detector
   (`_raise_breach_alert`, `tools/bm_bash_audit.py:723`). It is in neither answer
   8's blocking list nor answer 9's informational list, so Agent 5 has no
   instruction for the one hook that carries a correctness signal without being
   able to deny.

**Acceptance condition for closure.** Answer 9 names `bm_autosave.py precompact`
explicitly as synchronous and correctness-critical, never async; answer 8 renames
the consent gate a SessionStart write-suppression gate; the status line is removed
from the hook lists and recorded as a user-settings surface; and
`bm_bash_audit.py post` is classified in writing before Wave B dispatches.

**Freeze answers it?** No on all four. Answers 8 and 9 exist but are wrong about
what the shipped surface is.

---

## H6. The rename ships un-proven through two waves because the installed canary is scheduled at Wave C

**Mechanism.** Freeze amendment A1 confirms the installed-plugin canary already
EXISTS (`probe-installed`, "HOOK FIRED three times tonight", flakes fixed in
63bfb8c) and that Agent 7 extends it to the 19-step lifecycle. But Agent 7 is
Wave C (plan section 17), two waves after Lane A performs the rename in Wave A.

The rename is precisely the class of change that only a live install can falsify:
whether `/brothermode:start` resolves under the new plugin id, whether the nine
skill directories register, whether `hooks/hooks.json` still binds under the new
`${CLAUDE_PLUGIN_ROOT}`, whether `claude plugin validate . --strict` accepts nine
skills where it accepted one. Wave A's stated done-check is `claude plugin
validate . --strict` plus repository name scans (plan lines 573 to 583), which
proves the manifests parse, not that a command runs.

**Reasoning path.** Under the plan's own proof ladder (freeze answer 12: "live
installed canary > integration > contract > unit > inspection"), Wave A closes on
the fifth rung for a change whose whole risk sits on the first. If the rename is
wrong, the discovery point is Wave C, after Wave B's hook consolidation has
already been layered on top of it, and the plan's merge protocol (section 10) will
have declared two lanes closed on a false green.

**Acceptance condition for closure.** The existing `probe-installed` canary runs
against the renamed plugin as part of Wave A's integration green, before Wave B
dispatches, at minimum proving: marketplace add, install, installed version
matches `VERSION`, namespace discovery for all nine advertised skills, and one
live `/brothermode:help` invocation. Given A1 this is a scheduling change, not
new work.

**Freeze answers it?** No. Amendment A1 establishes the canary exists but leaves
it in Wave C, and the baseline rule addresses main's greenness rather than the
rename's proof point.

---

# MEDIUM

## M1. `doctor` and `recover` are new public surfaces in a run whose feature policy is NO NEW FEATURES

Freeze answer 4's CLI includes `doctor` and `recover`; plan 3.2 lists
`/brothermode:doctor` as a canonical skill. No `brotherme-doctor` or
`brotherme-recover` command exists in `commands/`. `scripts/doctor.py` and
`tools/bm_autosave.py recover` exist as scripts a user runs by path. Promoting
them to public skills is a public-surface expansion under plan 2.2, defensible as
exposure of existing capability but currently undeclared. Ask the freeze to say
which it is.

## M2. Shipped agent definitions hardcode model tiers, including opus, for every installing user

Plan Agent 6 requires `agents/` entries pinned to `model: haiku`, `sonnet`, and
`opus` with `effort: xhigh` for navigator and reviewer. Those ship inside the
plugin to users whose accounts may not carry opus or whose cost tolerance differs.
The freeze's "Fable is not required by the plugin" rule (plan line 778) is
satisfied in the current tree (no `Fable` string appears in `SKILL.md`,
`references/`, `commands/` or `skills/`; only three test files mention it), but
pinned opus agents reintroduce a strong-tier runtime dependency by another name.
Ask for a fallback tier or an inherit-by-default policy.

## M3. Hook-triggered writes bypass the fence entirely

The Stop chain (`hooks/hooks.json:31`) runs `bm_lead.py watchdog --tick` and
`bm_view.py render --if-stale`, both of which write files (`PROJECT-VIEW.html`,
alerts) as plugin subprocesses. `docs/HOOKS.md:385-392` already states the limit:
"A bare `Bash` write, a write from a subprocess the wrapper launched ... none of
these reach a PreToolUse hook". The product's own hooks are in that category.
With two writer worktrees resolving to one root (H1), two Stop chains render the
same view concurrently. Not a correctness break on its face, since the view is a
render, but it is a write authority the freeze's answer 10 does not enumerate.

## M4. The consent config rename orphans consent for every existing install

`~/.brotherme/config.json` and `BROTHERME_CONFIG` are the single gate that decides
whether SessionStart writes anything (`tools/bm_sessionstart.sh:17-21`,
`scripts/setup.py:113`). If the rename moves them, every existing install reads as
NOT CONSENTED on first v3 session, prints "BrotherMode setup is not complete yet",
and silently stops loading project memory until the user reruns `setup.py`. If the
rename does not move them, `BROTHERME_` survives as a permanent second namespace,
which is what the identity contract already concluded. Either answer is
defensible; the freeze picks neither.

## M5. The benchmark harness carries `brotherme` and the auth law simultaneously

`scripts/benchmark_comparative.py` (10 occurrences, including
`~/.brotherme/config.json` at lines 1696, 1726, 2216), `scripts/bench_env.py:142`
and `scripts/rehearse_fresh_install.py`. Freeze amendment A2 puts the benchmark
lane out of v3 scope "except via the rename sweep", while answer 12 makes the same
file the authority for the sanctioned headless auth path. A rename sweep editing
the file that holds the auth law is exactly the mix A2 was written to prevent.
Name an owner and a single sweep window for it.

---

# LOW

## L1. `product.identity.json` `persona_scope` is already stale

It reads "skills/brotherme and its seven `/brotherme-*` commands". Fifteen ship
(`tools/test_bm.py:5725-5732`). The contract's own machine-readable half has drifted
from the tree it governs, before v3 touches anything.

## L2. `.claude-plugin/marketplace.json` describes "the BrotherME plugin"

Contract section 1 restricts `BrotherME` to the persona voice, "nowhere else as a
current name". The marketplace description is a current user-facing page.

## L3. Two SKILL.md files carry conflicting `name:` frontmatter

Root `SKILL.md` declares `name: brothermode` (the expert law, invoked as
`/brothermode` on a clone install per `README.md:307`). `skills/brotherme/SKILL.md`
declares `name: brotherme`. Only the second is registered in
`.claude-plugin/plugin.json` (`"skills": ["./skills/brotherme"]`). After the
rename the personal-skill `/brothermode` and the plugin namespace `/brothermode:*`
become the same word on two different surfaces. Harmless if deliberate; state it.

## L4. The rename's true scale is larger than the freeze implies

845 occurrences of lowercase `brotherme` across 123 non-historical files in this
worktree (`*.py`, `*.md`, `*.json`, `*.sh`, `*.html`, excluding `docs/closure/`,
`docs/evidence/`, `docs/craft/`, `CHANGELOG.md`). The 2026-08-04 survey in
`docs/brand/IDENTITY-CONTRACT.md` section 5 counted 466 in 70 tracked files, so the
surface has grown by roughly 75 percent since the last time anyone measured it.
Whatever the janitor's sweep budget is, it should be set from the current number.

---

# Summary table

| ID | Severity | One line | Freeze answers it? |
|---|---|---|---|
| B1 | BLOCKER | Killed-session recovery has no snapshot trigger outside PreCompact | No |
| B2 | BLOCKER | STATE.md is both a render and an authority, and is gitignored out of the snapshot | No |
| B3 | BLOCKER | Rename revokes the ratified identity contract; its 12 break surfaces are unowned | No |
| B4 | BLOCKER | Shim removal condition is untestable; renamed id double-installs rather than upgrades | Partially, incorrectly |
| B5 | BLOCKER | Seven shipped public commands have no v3 destination | No |
| H1 | HIGH | Worktree nesting defeats the fence's path matching; fence is fail-open by default | No |
| H2 | HIGH | Wave A lanes run in parallel on a dependency and overlap on four unowned files | No |
| H3 | HIGH | Four shipped tests mandate the pre-v3 architecture, including a line-numbered allowlist | No |
| H4 | HIGH | "One boundary" is unenforced; 17 console scripts, the MCP server and hook scripts survive | Partially |
| H5 | HIGH | Answers 8 and 9 misclassify four hook surfaces; PreCompact autosave is called a notification | No |
| H6 | HIGH | The rename is not proven by a live install until Wave C, two waves late | No |

Per plan section 14, none of the five BLOCKERs and none of the six HIGHs is
explained by the freeze document as written. B4 and H4 are partially addressed and
would close with the amendments named above; the other nine need an answer that
does not currently exist in the freeze.

---

## Method and disclosure

Evidence is the tree at `fix/r3-installed-arm`. Every file and line reference was
read in this session. The one empirical filesystem check performed was
`ls -d` on `.brothermode` in the main repository and in this worktree, which is
what establishes the root-resolution behavior in H1.

Not covered, and stated rather than left implied: I did not run the test suite,
so every claim about a test is a claim about what its source asserts, not about
its current pass state. I did not run `claude plugin validate`. I read
`tools/bm_store.py` (17,884 lines) and `tools/bm_controller.py` (5,804 lines) by
targeted grep rather than in full, so a contradicting statement could exist deeper
in either. I did not audit `references/` (21 files) for internal-path coupling
beyond counting `bm_*.py` mentions; `references/autonomy.md` (5),
`references/mistakes.md` (4) and `references/learned-rules.md` (4) are the
densest and are unowned by any Wave A lane. I did not evaluate Claude Code's
current official skill frontmatter controls, so plan section 3.3's per-skill
"model auto-invocation: Disabled" column is unverified here; that is Agent 1's
scope and it should be confirmed before Lane A designs nine skills around it.
