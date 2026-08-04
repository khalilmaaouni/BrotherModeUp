# Remaining, measured against the founder's original brief

Written 2026-07-26 in answer to a direct question: what is missing from the delivery.
Every entry was checked on disk, not recalled. Ranked by what would embarrass us if a
stranger found it first, not by tidiness.

The original brief had ten items, A through J. Six are substantially delivered, four are
partly delivered, and two things were LOST today and belong on this list rather than in a
footnote.

CORRECTED 2026-08-01. Three items below were true when written and have since moved.
This paragraph does not delete them (see item 2, item 6 and the CI line under "Still
true from the earlier limits list"): it names what changed and where the evidence lives,
and a one-line marker sits inline at each of the three so nobody reads the old claim as
current.

- The CI-never-ran claim ("Still true from the earlier limits list": "Continuous
  integration has never executed"). CI has since run and is green: all nine jobs,
  observed 2026-07-31, per docs/KNOWN-LIMITS.md (the "OBSERVED GREEN 2026-07-31" entry)
  and docs/evidence/RELEASE-CANDIDATE-2.0.0-rc.9.md.
- The no-tagged-release claim (item 6, "No tagged release, and this is a security gap
  not a nicety"). Tagged, annotated releases now exist: v2.0.0-rc.1 through v2.0.0-rc.13, and the public v2.0.0
  at the time of this correction (rc.1 and rc.5 withdrawn for checksum defects, the
  others superseded as each next candidate lands; VERSION names the current one). The
  install command in README.md's Quick start clones a pinned tag, not a
  moving branch, and tools/test_bm_docs.py fails the page if it ever disagrees.
- The learning-redesign-is-only-law-text claim (item 2, "The learning redesign is law
  text, not code"). The correction-learning system is now built and tested:
  tools/bm_learn.py and tools/bm_learning.py implement it, the store schema is at
  version 11, and loops 0 through 5 of the plan have landed. See
  docs/CORRECTION-LEARNING.md and the rc.8/rc.9 entries in CHANGELOG.md.

RESOLVED 2026-08-04 (orchestrator, superseding CHK-2C's CANNOT-FULLY-DECIDE
addendum on the no-tagged-release bullet above,
docs/closure/reports/2026-08-04-CHK-2C-remaining-verdicts.md). CHK-2C
flagged that this local clone's `git tag -l` shows rc.1-rc.9 and rc.13 but
not rc.10-rc.12, and could not decide whether that was a local gap or the
true state upstream without a live remote check. Measured directly with
`git ls-remote --tags origin` and `git tag -l`, two separate facts follow.
First, rc.10, rc.11 and rc.12 were never tagged at all, on either side (the
remote carries only v2.0.0-rc.1, rc.2, rc.4 through rc.9, and rc.13), so the
local tag list is not incomplete and there is nothing to fetch. Second, and
this is a new defect worth recording rather than the one CHK-2C suspected:
`v2.0.0-rc.3` exists as a LOCAL tag only (`git tag -l` lists it) and is
absent from the remote (`git ls-remote --tags origin` does not list it), so
anyone told to pin `v2.0.0-rc.3` cannot resolve it from GitHub.

## 1. The telemetry tool never got its audit pass (biggest gap)

`tools/bm_telemetry.py` is 1,211 lines. It holds the corrections ledger, the outcomes
ledger, the handover export, and project identity. Roughly thirteen of the original
audit's findings live in it and almost none are fixed, because everything today went into
the ownership path (the store) and the recovery path (the autosave).

Confirmed still open by reading the code today:
- Project identity is computed from the CURRENT FOLDER, not the project root
  (`_project_of`, line 889). This is the exact defect fixed everywhere else. Two
  subfolders of one project get different identities, so one project's resume notes and
  intent log can be read as another's.
- A metric that CANNOT MOVE is still printed as if measured (line 572: "collisions=0,
  baton drops=0"). It is a hardcoded string with no variables behind it. It was named as
  the clearest piece of theatre in the system and then not removed.
- Malformed ledger lines are silently discarded, so a maintenance rewrite can
  permanently delete corrupt evidence while its count checks still look healthy.

Why it matters most: this is where YOUR data lives, and it is the half of the system the
learning loops depend on. Publishing a tool whose own honesty gate prints an unmovable
number undercuts the thing the project is selling.

CORRECTED 2026-08-04 (per CHK-2C,
docs/closure/reports/2026-08-04-CHK-2C-remaining-verdicts.md), two counts
only; the three findings above are not re-dispositioned here.
`tools/bm_telemetry.py` is 1995 lines by `wc -l tools/bm_telemetry.py`, not
1,211 as the opening line above says: the file has grown since this entry
was written. And the "Confirmed still open" block above enumerates exactly
THREE findings, not "roughly thirteen": there is no enumerable source for
"thirteen" anywhere in this tree tied to telemetry findings (checked with
`grep -rniE "thirteen|13 (findings|audit)" docs/*.md`, whose only hits are
unrelated: a benchmark scenario count, a law-amendment count, a routing-row
count, and a rule count). Dispositions for the three findings themselves
(project identity from current folder, the hardcoded collisions/baton-drops
line, and silently discarded malformed lines) are PENDING a separate,
currently running audit that is probing them with calibrated tests; that
audit's verdict supersedes any reading-only judgement recorded here.

## 2. The learning redesign is law text, not code

(CORRECTED 2026-08-01: see the correction block at the top.)

Section 8 of the constitution now describes four loops (corrections, revealed taste,
calibration on divergent predictions only, and the division of labour) plus honest NOT
DECIDABLE labelling. Nothing implements them. There is no capture of rework or escaped
defects, no provenance requirement on ratings, no divergence column, and the fictional
metrics still print.

Right now the law promises behavior the tools do not have, which is the same failure that
was just deleted from the time-to-live field.

## 3. Items B and F: the scaffold, the intake, and the sunset path do not exist

Designed and written down, never built:
- No project scaffold template, so the next project still starts from an empty folder.
- No INTAKE template, so the problem-first discipline (the why, the why behind the why,
  value, feasibility, kill criteria) depends on someone remembering it.
- Nothing about SUNSET or graceful evolution, which the brief asked for explicitly. The
  system helps a project start and run; it does not help one end well.

## 4. Item H: the memory onboarding is barely covered

Obsidian appears zero times in the README and zero times in the quickstart. There is no
Mem0 adapter, only mentions in design documents. A stranger can install the tool and run
its tests, and has no guided path to the memory setup that makes it worth using.

## 5. The read-only project server (MCP) is not built

Ratified as the phase right after the engine. The engine is now done, so this is next in
line rather than forgotten. It is what would let any session ask what fences are live and
what decisions are open without reading files.

## 6. No tagged release, and this is a security gap not a nicety

(CORRECTED 2026-08-01: see the correction block at the top.)

The install instruction still clones a MOVING BRANCH into a location whose code runs
automatically on every session. For a tool that reads transcripts and installs hooks,
the original audit called this the weakest link in the design. It needs tagged,
immutable releases with checksums.

## 7. Item G: the private skill is not synced yet

The public branch carries every change from today. The private copy is still at the V1
commit. Good news measured today: the four V1 tool files were byte-identical across both
copies, so the port is contained rather than a merge problem.

## 8. Two things LOST today, named rather than buried

- Checkpoint CLASH DETECTION was removed by the rewire. It has no equivalent in the
  ratified mapping, so this is a feature removal, not cleanup.
- The 320-line GENERATIVE TEST was deleted with the V1 registry it was bound to. It
  historically found a defect nobody had written down. A store-level replacement is being
  built with a requirement that it be proven to fire, because a generative test that
  cannot fire is decoration.

## Still true from the earlier limits list

(CORRECTED 2026-08-01: the "continuous integration has never executed" claim below
is stale; see the correction block at the top.)

Continuous integration has never executed. Windows is designed for, not proven. The
`vault-template` ignore file covers the JSONL ledgers but not the resume briefs, intent
logs, or tick counters (audit finding 31, still open). Audit findings 16 through 63 were
triaged by class rather than each re-proven, so any one of them that matters to a
decision should be re-verified rather than trusted.

## Recommended order, by harm rather than tidiness

1. The telemetry audit pass, including deleting the fake metric. Before publishing.
2. Implement the learning loops so the law stops describing fiction.
3. Scaffold, intake, and sunset templates, because they change how every future project
   starts.
4. Release discipline (tags, checksums), then memory onboarding, then the project server.
