# Remaining, measured against the founder's original brief

Written 2026-07-26 in answer to a direct question: what is missing from the delivery.
Every entry was checked on disk, not recalled. Ranked by what would embarrass us if a
stranger found it first, not by tidiness.

The original brief had ten items, A through J. Six are substantially delivered, four are
partly delivered, and two things were LOST today and belong on this list rather than in a
footnote.

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

## 2. The learning redesign is law text, not code

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
