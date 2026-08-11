# BrotherMode long range development plan, written 2026-08-11

Status: CURRENT. This plan SUPERSEDES the wave structure of
docs/plan/PROGRAM-PLAN-2026-08-10.md and
docs/plan/PROGRAM-PLAN-2026-08-11-RATIFIED.md. Those two files stay in the
repo as history, do not delete them. Their standing rules keep governing
every tranche below: two lanes max, RED first (write the failing check
before the fix), receipts over narration (quote command output, do not
describe it), and the spend guard stays active every session.

This plan is built from PRODUCT-DIRECTION.md section 19 (the four-lane
directive) and docs/plan/RECLASSIFICATION-2026-08-11.md (the row-by-row
table of what is built, partial, or missing, with evidence). Every loop
below traces to a numbered row in that table. Read PRODUCT-DIRECTION.md
first if a loop's purpose is unclear; this plan does not repeat that
document's reasoning, only its schedule.

North star for every tranche: Confirmed External Verified Deliveries per
Week (CEVD/W). A loop that cannot name which of the four lanes it serves,
or how it moves CEVD/W or a named quality guardrail, does not belong in
this plan.

The four lanes, no fifth lane, ever:

1. Core verified delivery path
2. Toolkit MVP
3. Trust and data lifecycle
4. External pilot and measurement

---

## How to read this plan

- Each tranche is a stable, tagged release. A tranche ships as a tag only
  when its full battery is green (`python3 tools/test_all.py`, the full
  gate) and every box in its closing checklist is ticked with quoted
  evidence.
- The next tranche does not open until the previous release is tagged and
  stable. No overlap between tranches.
- Every loop names the exact files it touches and ends with a command,
  test name, or grep that must return a specific result. A box only ticks
  when that exact check was run after the last edit and the output is
  quoted next to it.
- Every date range is a range, not a promise, and carries a confidence
  word: HIGH (little unknown, mechanical), MEDIUM (some judgment calls
  expected), MEDIUM-LOW (design work inside the tranche, timing depends on
  what is found), LOW (depends on someone outside this machine, mainly the
  founder or external users).
- Releases are founder gated. No tranche tags itself. The founder says go.
- No unattended overnight or multi-hour stretch runs until R1.4 proves the
  stall sentinel catches a seeded stall end to end. Until then, every loop
  runs attended, in the foreground, with the founder able to see it.

---

## R0, v3.2.0, "V3 Final", ships 2026-08-12

R0 is not planned in this document. It has its own plan already:
docs/plan/V3-FINAL-2026-08-12.md. Read that file for R0's WBS, its file
list, and its done-checks. This plan only records R0 as the release this
plan's R1 builds on top of, and does not duplicate its table.

---

## R1, v3.3.0, "PROVE", target window 2026-08-13 to 2026-08-16

3 to 5 working days, confidence MEDIUM (most of the row is additive schema
work with a known pattern to mirror; the SD2 gate depends on a founder
decision that has not been made yet, which is the main source of
uncertainty).

Theme: the verification contract becomes criterion-linked instead of
task-linked, and the recovery ceremony closes its two remaining gaps
(the opening half of the baton ceremony, and the last live prose fence).

### R1 WBS

| Loop | Title | Lane | Files | Done-check |
|------|-------|------|-------|------------|
| R1.1 | Outcome contract columns | Core | tools/bm_store.py (DDL), tools/bm_project.py (start flags), CANVAS.md rendering | Targeted store and project test suites green |
| R1.2 | Criterion-linked verification | Core | tools/bm_store.py (acceptance_checks, evidence table), tools/bm_project.py (render_delivery_packet, list_evidence) | Delivery packet test names each criterion beside its evidence state; full gate green |
| R1.3 | Ceremony opening half wired | Core (recovery) | tools/bm_sessionstart.sh, hooks/hooks.json | New test: a session that skips detect is told so |
| R1.4 | SD2 sentinel, FOUNDER GATE FIRST | Core (recovery, stop controls) | branch wip/sd2-sentinel-2026-08-11-stopped-session, or discard | Seeded-stall kill test passes end to end |
| R1.5 | Prose fence retirement (RF-3) | Core hygiene | STATE.md (remove the SBE prose fence), fence hook and its tests | grep for live prose fence markers returns empty; fence hook tests green |
| R1.6 | Surface consolidation | Core docs | the 15 legacy command shims (commands/*.md), the 11 advanced skill files (skills/*/SKILL.md) | Docs suite green |

### R1.1: outcome contract columns

Reclassification row 7. The projects table already has goal, scope,
success_criteria, and risks. It has no kill_criteria and no non_goals
columns, so a project's outcome contract cannot record either, even though
PRODUCT-DIRECTION.md section 5.1 names both as things BrotherMode must own.

Files:
- tools/bm_store.py: add kill_criteria and non_goals columns to the
  projects table DDL. Additive only, same shape as the existing risks
  column (JSON list stored as TEXT, default `'[]'`). Do not touch or
  reshape the risks column itself.
- tools/bm_project.py: add start-time flags so a new project can be
  created with kill_criteria and non_goals filled in, matching how risks
  is already accepted today.
- CANVAS.md: render the two new fields wherever risks is already
  rendered, so a reader sees them without opening the store.

Done-check: run the targeted store and project pytest modules (name them
from tools/test_all.py's SUITES registry per PO-6, do not guess a path)
and quote the pass line. Because this changes tools/bm_store.py, the full
gate must also go green before this loop closes.

### R1.2: criterion-linked verification

Reclassification row 6, the largest loop in this tranche. Today
acceptance_checks is a flat string list on a task
(tools/bm_store.py:2923), and evidence attaches to a task as a whole, not
to one specific criterion inside it. Only controller_units links an
objective to a check result. This means a delivery packet can say "checks
ran" without saying which acceptance criterion each check actually
covered, which is exactly the gap PRODUCT-DIRECTION.md section 5.5 calls
out: "a check that ran after the final edit can still be the wrong
check."

Files:
- tools/bm_store.py: give each acceptance_checks entry a stable id; add a
  criterion_id column to the evidence table; extend list_evidence
  (currently at tools/bm_store.py:13136 and a second definition at
  16577, confirm which is live before editing) to filter by criterion_id.
- tools/bm_project.py: extend render_delivery_packet (tools/bm_project.py:545)
  to print, per criterion: checked (with its evidence), not checked, or
  remaining.

Kill criterion carried from the reclassification table: if this migration
risks the existing test suite (3011 tests at time of writing, reconfirm
the live count from the gate's own summary line before treating that
number as current), ship the rendering half only in this window and
schedule the migration half separately rather than forcing both through
under time pressure.

Done-check: a delivery packet generated against a test project names each
criterion by id, beside checked, not checked, or remaining. Because this
touches tools/bm_store.py, the full gate (`python3 tools/test_all.py`,
run per the PO-1 detach-and-poll recipe, 8 to 13 minutes) must be green
before this loop closes.

### R1.3: ceremony opening half wired

Reclassification row 5. The closing half of the baton ceremony is already
enforced by tools/bm_handover.py verify-close. The opening half, running
`bm_handover.py detect` at session start, is not wired into anything a
new session actually runs. hooks/hooks.json already calls
tools/bm_sessionstart.sh at SessionStart (confirmed at hooks/hooks.json
line 8), so this loop adds the detect call inside that existing script
rather than inventing a new hook path.

Half a day, confidence MEDIUM-HIGH (small, mechanical, and the blocking
fence that used to sit on these files was released 2026-08-11, so nothing
else should be claiming them right now, but confirm with a claims check
before editing in case another lane picked them up since).

Files:
- tools/bm_sessionstart.sh: add the `bm_handover.py detect` call.
- hooks/hooks.json: confirm the wiring still points at the updated
  script; do not add a second hook entry if the existing one already
  covers it.

Done-check: a new test proves a session that skips detect is told so
(the test simulates or checks for the session-start path not having run
detect, and asserts the warning surfaces). Quote the test name and its
pass line.

### R1.4: SD2 sentinel, founder gate first

Reclassification row 4. This is the one loop in this tranche that does
not start until the founder answers a question, because it is a real
decision with real cost either way, not a mechanical step.

FOUNDER GATE, ask before any code moves: resume branch
wip/sd2-sentinel-2026-08-11-stopped-session, which already holds 1618
lines of preserved work on heartbeat durability, or discard it and leave
SD2 at its current passive-sweep state. Recommended: resume, because the
work is already done and unattended stretches stay blocked without it.
But it is the founder's call, not a default.

If resumed:
- Files: the branch's own file list (do not re-derive it by hand; check
  out the branch and read `git diff main...wip/sd2-sentinel-2026-08-11-stopped-session --stat`
  for the real list before starting).
- Work: land heartbeat durability, then build a seeded-stall kill test
  that runs the sentinel end to end against a simulated stall and checks
  that it actually stops the stalled work.

1 to 2 days from the branch's existing state, confidence MEDIUM (the
code exists; the risk is integration against whatever else landed on main
since the branch was cut).

Done-check: the seeded-stall kill test passes, run and quoted after the
merge. This is also the gate mentioned above: no unattended stretch runs
in this plan until this exact check has passed once.

### R1.5: prose fence retirement (RF-3)

Reclassification row 22. The store is supposed to be the only fence
surface in this repository. It is, except for one holdout: a prose fence
written directly into STATE.md for the SBE work, which blocked a plain
edit to README.md on 2026-08-11 because its owning session was already
dead. That is the exact two-parsers failure this row was written to
prevent, not a hypothetical.

Files:
- STATE.md: remove the live SBE prose fence line.
- the fence hook and its existing tests (find them by grepping for the
  fence-check logic before editing, do not assume a path from memory).

Done-check: `grep` for any remaining live prose fence marker in the repo
returns empty, and the fence hook's own test suite stays green.

### R1.6: surface consolidation

Reclassification-adjacent, drawn from PRODUCT-DIRECTION.md section 12
(the six-command public surface) and section 13.3 (scope budget: no new
public command). There are 15 legacy command shims in commands/ and 11
advanced skills that should read as internal, not first-class public
surface, so a new user is not choosing between 20+ commands.

R0's A2 already lands the documentation half (deprecation banners on the
15 shims, internal marking language in the six-name surface docs), so this
loop is the PHYSICAL half only; closing it by re-doing A2's documentation
would be closing it by doing nothing.

Files:
- the 15 legacy command shims under commands/*.md: physically retire them
  (delete or fold into the skills routing), with every reference updated
  and the docs suite proving no dangling pointer remains.
- docs/book/ (the solo-builder booklet): update its command-surface
  content, which R0 shipped one release stale by an explicit written
  decision in docs/plan/V3-FINAL-2026-08-12.md.
- the 12 advanced skill files under skills/*/SKILL.md: mark each
  internal in its own frontmatter or opening line, mirroring however an
  existing internal-only skill in this repo already marks itself.

Done-check: the docs suite (the SUITES entry that checks commands/ and
skills/ documentation, named from tools/test_all.py's registry per PO-6)
is green.

### R1 closing checklist

- [ ] R1.1 done-check quoted (store and project suites green)
- [ ] R1.2 done-check quoted (delivery packet test names criteria; full
      gate green)
- [ ] R1.3 done-check quoted (skip-detect test passes)
- [ ] R1.4 founder gate answered and recorded; if resumed, seeded-stall
      kill test quoted; if discarded, that decision recorded with its
      reason and what would reopen it
- [ ] R1.5 done-check quoted (grep empty, fence hook tests green)
- [ ] R1.6 done-check quoted (docs suite green)
- [ ] Full gate (`python3 tools/test_all.py`) green on the exact commit
      being tagged, HEAD confirmed not to have moved since that run
- [ ] CHECKSUMS.sha256 regenerated last, after every new file is
      `git add`ed (scripts/checksums.sh CHECKSUMS.sha256)
- [ ] Baton ceremony close half run: skeleton, fill every FILL-BY-HAND
      slot, zip, verify-close, verdict quoted
- [ ] Board republished, tag v3.3.0 cut only after founder go

---

## R2, v3.4.0, "TOOLKIT MVP", target window 2026-08-17 to 2026-08-26

5 to 8 working days, confidence MEDIUM-LOW (this is new subsystem work,
not additive schema work, and the inventory step in particular has an
unknown surface area until it is actually attempted).

Theme: build exactly the 12-step MVP named in PRODUCT-DIRECTION.md
section 8.6 and P3, no more. Find, Trust, Compose, Prove, Learn. Nothing
in this tranche builds a marketplace, community-wide discovery, or
automatic skill generation; those are explicitly out per section 8.6 and
14 (P3).

### R2 WBS

| Loop | Title | Lane | Files | Done-check |
|------|-------|------|-------|------------|
| R2.1 | Inventory | Toolkit | tools/bm_toolkit.py (new), store tables for capability manifest | Inventory command lists installed skills, plugins, MCP servers, CLIs with source and version where knowable |
| R2.2 | Trust inspection record | Toolkit | tools/bm_toolkit.py, store schema | Trust record printed before any install proposal, fields match section 8.2 Trust list |
| R2.3 | Minimal toolkit proposal plus allowlisted install | Toolkit | tools/bm_toolkit.py | One task completes through a recommended toolkit; install scope, pin, and rollback command all recorded |
| R2.4 | Receipts | Toolkit and Core seam | tools/bm_store.py (evidence/receipt model), tools/bm_project.py | Receipt rows carry executor identity, capability versions, artifacts changed, claimed result, verification result |
| R2.5 | Cleanup | Toolkit | tools/bm_toolkit.py | Every install this tranche produced has a working reversal command, run and confirmed |
| R2.6 | Learn stage | Toolkit | tools/bm_store.py (capability memory table), tools/bm_toolkit.py | A second task on the same capability type shows the prior outcome influencing selection, without any core rule file changing |

### R2.1: inventory

Reclassification row 8, first step. Today there is no command that lists
installed skills, plugins, MCP servers, and CLIs visible to the runtime.
This is the foundation the rest of R2 depends on; nothing else in this
tranche can run before this exists.

Files:
- tools/bm_toolkit.py (new file, mirror the CLI argument and output
  conventions of an existing tools/bm_*.py entry point, name which one
  you used as the template).
- store tables for the capability manifest, added the same additive way
  as R1.1's columns.

Kill criterion, carried verbatim from the reclassification table: if
inventory alone exceeds one week, cut scope to Claude Code surfaces only
and record the cut as a decision, with what was dropped and what would
reopen it.

Done-check: the inventory command lists installed skills, plugins, MCP
servers, and CLIs visible to the Claude Code runtime, with source and
version recorded wherever it is knowable, and states plainly where it is
not.

### R2.2: trust inspection record

Per PRODUCT-DIRECTION.md section 8.2 (Trust), before any capability is
proposed for installation this loop must record: publisher, source,
version or commit, license, install scope, permissions surface, network
use, and credentials required. A skill description or plugin manifest
claim is not proof by itself (section 8.2); this record has to come from
inspecting the source or observed behavior, not from repeating the
publisher's own claim.

Files: tools/bm_toolkit.py, plus the store schema addition needed to
persist a trust record per capability.

Done-check: for at least one real installed capability, the trust record
prints in full before any install proposal is shown, and every field
named above is populated or explicitly marked unknown.

### R2.3: minimal toolkit proposal plus allowlisted install

Official or allowlisted sources only (Tier 0/1 per PRODUCT-DIRECTION.md
section 8.4). Local scope by default. Version pinned. Provenance
recorded. Exactly one visible approval point, matching section 8.5's
installation policy. A rollback command is recorded before or at
install time, not written up after the fact.

Files: tools/bm_toolkit.py.

Done-check: one real task completes end to end through a toolkit proposal
that a human approved once, with install scope, pin, and rollback command
all present in the record.

### R2.4: receipts

Reclassification row 9, this is the 5.8 evidence normalization and 5.7
capability provenance work named directly in PRODUCT-DIRECTION.md.
Receipts get folded into the same evidence model R1.2 already extended
with criterion_id, so this loop should read that schema first rather than
building a second, parallel evidence table.

Files: tools/bm_store.py, tools/bm_project.py.

Done-check: a receipt row for a real toolkit-assisted task carries
executor identity, capability versions, artifacts changed, the claimed
result, the verification result, and any exceptions or omissions, all
in one place a delivery packet can read.

### R2.5: cleanup

Section 8.5's rule: disable or remove task-specific additions after
delivery unless retention is justified, and provide one cleanup command
that reverses the installation.

Files: tools/bm_toolkit.py.

Done-check: every capability installed during this tranche's own testing
has its reversal command actually run once, and the reversal is confirmed
(the capability is gone, or explicitly retained with a stated reason).

### R2.6: Learn stage

Section 8.7 Layer 1, capability memory: remember which capability served
which task and with what outcome. This loop also folds in the parked
SL-quick notes from the superseded program plan (reclassification row 19)
rather than leaving them as a separate, forgotten lane. This is explicitly
learning about selection, not a mechanism that can rewrite a core rule
file; PRODUCT-DIRECTION.md section 8.7 and Rule 9 (section 17) both draw
that line, and this loop must not cross it.

Files: tools/bm_store.py (capability memory table), tools/bm_toolkit.py.

Done-check: run a second task of the same type used in R2.3; the toolkit
proposal for the second task visibly reflects the first task's recorded
outcome (for example, ranks the previously successful capability first),
and no file under the core rule set changed as a side effect.

### R2 closing checklist

- [ ] R2.1 through R2.6 done-checks quoted
- [ ] Full gate green on the commit being tagged
- [ ] CHECKSUMS.sha256 regenerated last
- [ ] Every install made during R2's own work is either cleaned up or
      its retention is justified in writing
- [ ] Baton ceremony close half run and verdict quoted
- [ ] Board republished, tag v3.4.0 cut only after founder go

---

## R3, v3.5.0, "TRUST AND PILOT", target window 2026-08-27 to 2026-09-05

4 to 6 working days of BrotherMode-side work, confidence MEDIUM for the
engineering loops and LOW for the pilot loop specifically, because
recruiting five qualified external users is outside this machine's
control and does not run on a fixed schedule the way a code change does.

Theme: finish PRODUCT-DIRECTION.md P4 (data lifecycle and trust) and take
the first real steps of P5 (external pilot) and P6 (measurement).

### R3 WBS

| Loop | Title | Lane | Files | Done-check |
|------|-------|------|-------|------------|
| R3.1 | Data lifecycle completion | Trust | bm_project.py purge/dry-run path, docs/HANDOVER-BY-HAND.md or SECURITY.md, public example paths | Purge dry-run test proves nothing is removed; private vulnerability reporting enabled; grep for personal paths in public examples returns empty |
| R3.2 | Founder decisions batch | Trust | vault history decision record, ECOSYSTEM-REFRESH.md arming | Both decisions recorded with the founder's actual answer, not assumed |
| R3.3 | Pilot protocol | Pilot | a pilot recruitment and task checklist document (new, under docs/pilot/) | At least 5 qualified users named or in active recruitment; six required pilot tasks written as a per-user checklist; support channel named |
| R3.4 | Adoption L2 | Pilot | the status-page-first-contact feature (files depend on R3.3 findings, name them once the feature is scoped) | Kill criterion kept verbatim: if the page says nothing its owner did not already know, it dies |
| R3.5 | Measurement counters live | Pilot measurement | store views/evidence/delivery tables, a counters reader | CEVD/W is counted from real rows only; no dashboard built before rows exist |

### R3.1: data lifecycle completion

Reclassification row 11. R0 shipped the purge dry-run AND the
data-locations doctor check (pulled forward by decision D6, 2026-08-11).
This loop is the remaining completion half: purge proof documentation,
private vulnerability reporting, and the synthetic-paths sweep.

Files: the purge and dry-run path in bm_project.py (confirm the current
line-1564 area is still the right spot before editing, code may have
shifted since the reclassification sweep), SECURITY.md, and every public
example path in the repo (README.md, docs/, ECOSYSTEM.md and similar).

Done-check: private vulnerability reporting is enabled (a founder click
on GitHub, not something this plan can tick by itself, record who clicked
it and when); the purge proof is documented, citing the R0 dry-run test by
name; and a grep across public example files for real personal paths (home
directory names, this machine's actual paths) returns empty, replaced with
synthetic paths only.

### R3.2: founder decisions batch

Reclassification's "open founder items carried forward," items 3 and 4.
Two decisions the founder has not yet made, both time-boxed to before the
pilot starts.

Files: wherever the vault-name decision gets recorded (this is a decision
record, not new code), and docs/ECOSYSTEM-REFRESH.md's arming switch.

Done-check: both decisions are recorded with the founder's actual answer
(rewrite history or accept as-is for the vault name; arm or do not arm
the weekly refresh, with its known weekly token spend stated up front
before the yes, not after).

### R3.3: pilot protocol

PRODUCT-DIRECTION.md section 14 P5. At least five qualified users
matching the primary persona (section 4): technical solo founders, senior
solo builders, or maintainers doing serious multi-session AI-agent work,
comfortable with git and a terminal. Six required pilot tasks per P5:
one multi-session task, one forced interruption and recovery, one
parallel or ownership-sensitive task, one Toolkit-assisted task, one
verified delivery, one cleanup or uninstall check.

Files: a new pilot recruitment and task checklist document under
docs/pilot/ (create the directory if it does not exist; check first).

Done-check: at least 5 qualified users are named or in active
recruitment with their qualification stated against the persona
definition; the six required tasks are written as a literal checklist
per user; a support channel is named and reachable.

### R3.4: Adoption L2, status-page-first contact

Reclassification row 12, kill criterion kept verbatim per the founder's
own ratified wording: if the page says nothing its owner did not already
know, it dies. This loop is explicitly allowed to fail and be discarded;
that is the actual spec, not a soft escape.

Files: depend on how the feature is scoped once R3.3's pilot users are
in hand; name them at the start of this loop rather than guessing now.

Done-check: run the page against at least one real external repository
outside this machine and confirm, in writing, whether it told that
repository's owner something they did not already know. If not, stop
and record the kill, do not keep iterating past the stated criterion.

### R3.5: measurement counters live

PRODUCT-DIRECTION.md section 14 P6: do not build dashboards before the
rows exist. This loop only wires counters to real rows produced by R3.3
and R3.4's pilot activity; it does not add a UI.

Files: the store's views, evidence, and delivery-packet tables (already
built by R1 and R2 work), plus a counters reader that computes CEVD/W
from those rows.

Done-check: CEVD/W for the pilot period is computed from real,
non-founder rows only (per PRODUCT-DIRECTION.md section 3, dogfooding
and fixture runs do not count), and the reader states plainly when a
guardrail metric has zero rows rather than reporting a false zero.

### R3 closing checklist

- [ ] R3.1 through R3.5 done-checks quoted
- [ ] Full gate green on the commit being tagged
- [ ] CHECKSUMS.sha256 regenerated last
- [ ] Both R3.2 founder decisions recorded with actual answers
- [ ] R3.3's five qualified users named, with the six-task checklist per
      user in hand
- [ ] Baton ceremony close half run and verdict quoted
- [ ] Board republished, tag v3.5.0 cut only after founder go

---

## R4, "EVIDENCE RERANK", 2026-09-06 onward, open-ended

No fixed window and no confidence word attached to a date, because this
tranche's entire premise is that its own content is not decided yet.
PRODUCT-DIRECTION.md section 18 step 7 is explicit: after the first five
external users, rerank everything based on what actually blocked a
verified delivery, what users bypassed, what they repeatedly asked for,
what caused rework, which external capabilities worked, and which runtime
demand was real. Planning R4's WBS today, before that evidence exists,
would be exactly the mistake this whole document exists to avoid: work
started because it seemed interesting rather than because evidence
demanded it.

What is already known to be eligible once the 5-user threshold is hit,
in the order PRODUCT-DIRECTION.md's own backlog names them:

1. L5 measurement reader, now buildable because pilot rows exist
   (reclassification row 13).
2. Benchmark run (scripts/benchmark_comparative.py, already built per
   reclassification row 14), optional if the pilot alone already yields
   10 confirmed deliveries.
3. Executor adapters for Codex and Cursor as compatible executors
   reached through the Toolkit (not a verified-runtime port); this is
   explicitly not the same thing as the parked Codex verified-runtime
   port below, and must not be treated as reopening that.
4. V1 cross-model verifier (reclassification row 17).

None of these four start before the rerank itself happens and produces
a written table in the same shape as RECLASSIFICATION-2026-08-11.md.
That rerank document is R4's actual first deliverable.

---

## Parking lot

One list, each with the exact flip condition that would move it into an
active tranche. Nothing here gets worked on speculatively.

| Item | Flip condition |
|------|-----------------|
| G1 governor and graph work | An incident traces to a missing governor |
| CC generated command center | Two consecutive board drift incidents |
| Codex verified-runtime port | An outside adopter asks, or the benchmark shows runtime choice is blocking adoption |
| MCP write tools | After the read surface has automated end-to-end coverage (PRODUCT-DIRECTION.md section 9.2) |

Plus, by name, the park-indefinitely list from PRODUCT-DIRECTION.md
section 15: new internal planning methodology, new internal TDD
framework, new code editor, new model router, new deployment platform,
new issue tracker, general cloud execution platform, general operating
system sandbox, a BrotherMode-owned clone of a popular skill, a broad
public skill marketplace, enterprise project management and role-based
access, autonomous modification of core safety rules, and production
deployment without an explicit human gate. None of these reopen without
external evidence changing the founder's decision, per section 15's own
header.

---

## Cadence and caps, binding for every tranche in this plan

- Two lanes max, one loop per lane. A loop closes before the next opens
  in that lane: its done-check ran after the last edit and is quoted,
  every change recorded as needed in another file was applied by name,
  and the evidence is filed.
- The board is republished and marked DELIVERED at every loop close, not
  batched up for the end of a tranche.
- Every release is founder gated. No tag gets cut without the founder's
  explicit go, stated after the closing checklist is fully ticked.
- Every subagent brief in this plan's execution states its tier and the
  reason, in the brief itself: haiku for mechanical bulk work, sonnet for
  well scoped implementation and search from a precise spec, opus or the
  session default for judging, adversarial review, and synthesis. An
  unstated tier is a violation of this plan, not a default to fall back
  on.
- Spend guard ceilings (~/.claude/hooks/spend_guard.py and
  ~/.claude/spend-guard.json) stay active in every session that executes
  this plan. Nobody removes or bypasses that hook to get a loop closed
  faster.
- No unattended, multi-hour, or overnight stretch runs under this plan
  until R1.4 proves the stall sentinel catches a seeded stall end to end.
  Before that check has passed once, every loop in this plan runs
  attended, in the foreground, with a human able to see and stop it.
