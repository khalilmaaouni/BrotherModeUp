# M15: does the installed fence hook treat a PARKED store record as live

Status: CURRENT
Date: 2026-08-21
Question: does `bm_fence_hook.py`, as installed under
`~/.claude/skills/brothermode`, still refuse a foreign write to a path whose
only covering record has been parked, or does it correctly stop enforcing
once that record leaves the active state.

## VERDICT

PARKED IS TREATED AS DEAD (no defect). A foreign session was ALLOWED
(exit 0, no deny reason) against a path whose only covering record was
parked, while the identical foreign session was DENIED (exit 1) at the same
moment against a second path still covered by an active record, on both the
repository hook and the installed hook, with zero fail-open warnings on
stderr anywhere in the run.

## THE POSITIVE CONTROL

Before touching parking at all, a probe record was claimed as session A
(label `bm1-e00f74e60c906a70a425ba9e`, derived from harness id
`m15probe-ownerA`) over a path that exists nowhere else in the project, then
queried as a different foreign session B (label
`bm1-17a8940311e2885e736ad81c`, derived from harness id
`m15probe-foreignB`). The record is genuinely active at this point (state
verified independently below), so the fence MUST refuse this write or the
instrument is dead.

Command (repository hook):
```
python3 tools/bm_fence_hook.py query docs/evidence/m15probe-scratch-target-A.md --session-id m15probe-foreignB
```
Output:
```
DENY docs/evidence/m15probe-scratch-target-A.md: BrotherMode fence: docs/evidence/m15probe-scratch-target-A.md is inside the fence of the active record m15probe-fence-test-A (lifecycle dace851dbe5e44a29a46935d5131adbd, version 1), which is owned by session bm1-e00f74e60c906a70a425ba9e. This session is bm1-17a8940311e2885e736ad81c, so it is not the writer for that path. Claimed as: docs/evidence/m15probe-scratch-target-A.md.
One writer per file is structural, not advisory: do not edit across the fence. Report the needed change to the owner instead. To take the fence over deliberately, run:
  python3 tools/bm_store.py adopt dace851dbe5e44a29a46935d5131adbd --version 1 --session bm1-17a8940311e2885e736ad81c --adopt-from-live-session
then re-claim the paths you need with `bm_store.py claim ... --session bm1-17a8940311e2885e736ad81c`.
```
STDERR: (empty). EXIT: 1.

The identical command run against the installed copy
(`python3 /Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_fence_hook.py query docs/evidence/m15probe-scratch-target-A.md --session-id m15probe-foreignB`)
produced byte-identical stdout, empty stderr, exit 1.

As a second, independent positive control using real production data rather
than a synthetic claim: the live record `night-orchestrator`
(lifecycle `ba297466adf548eabd6706945627b671`) holds an actual active claim
on `docs/plan/GANTT.html` right now, owned by a different real session. Both
hook copies denied a foreign write to it (see THE MEASUREMENT, bonus
section). The instrument can refuse. It is not dead.

A third, unplanned positive control turned up while delivering this very
document: see SECONDARY OBSERVATION below. It is a refusal against this
session's own write, kept separate because it is not evidence about parked
records, it is evidence about a different fence entirely.

## THE MEASUREMENT

Every command below was run from `/Users/khalil.maaouni/Documents/BrotherModeUp`.
`REPO_HOOK=tools/bm_fence_hook.py`,
`INSTALLED_HOOK=/Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_fence_hook.py`.
Two disposable probe records were used, both claimed as session A
(`bm1-e00f74e60c906a70a425ba9e`) over paths that exist nowhere else in the
project and were never written to disk:

- Record A: `m15probe-fence-test-A`, lifecycle `dace851dbe5e44a29a46935d5131adbd`,
  fencing `docs/evidence/m15probe-scratch-target-A.md`. This one gets parked.
- Record B: `m15probe-fence-test-B`, lifecycle `a84cd7d2da284953b7749a93106a1877`,
  fencing `docs/evidence/m15probe-scratch-target-B.md`. This one stays active
  through the whole run, as a running negative control queried at the same
  moment as the parked one, so a repeat of the "swamped, ALLOW for both"
  failure from the prior attempt would show up immediately.

### Setup

```
$ python3 tools/bm_store.py claim m15probe-fence-test-A --lifetime ephemeral \
    --objective "M15 measurement probe A: will be parked to test whether the installed fence still treats it as live" \
    --files docs/evidence/m15probe-scratch-target-A.md --session bm1-e00f74e60c906a70a425ba9e
claimed 'm15probe-fence-test-A' as lifecycle dace851dbe5e44a29a46935d5131adbd (version 1, session bm1-e00f74e60c906a70a425ba9e)

$ python3 tools/bm_store.py claim m15probe-fence-test-B --lifetime ephemeral \
    --objective "M15 measurement probe B: stays active throughout as the running negative control" \
    --files docs/evidence/m15probe-scratch-target-B.md --session bm1-e00f74e60c906a70a425ba9e
claimed 'm15probe-fence-test-B' as lifecycle a84cd7d2da284953b7749a93106a1877 (version 1, session bm1-e00f74e60c906a70a425ba9e)
```

### Before park: both records active, queried as foreign session B

| target | via | stdout | stderr | exit |
|---|---|---|---|---|
| P1 (`...target-A.md`) | REPO_HOOK | `DENY ...` (full text in THE POSITIVE CONTROL above) | empty | 1 |
| P1 (`...target-A.md`) | INSTALLED_HOOK | identical to REPO_HOOK | empty | 1 |
| P2 (`...target-B.md`) | REPO_HOOK | `DENY docs/evidence/m15probe-scratch-target-B.md: BrotherMode fence: ... is inside the fence of the active record m15probe-fence-test-B (lifecycle a84cd7d2da284953b7749a93106a1877, version 1), which is owned by session bm1-e00f74e60c906a70a425ba9e. This session is bm1-17a8940311e2885e736ad81c, so it is not the writer for that path. ...` | empty | 1 |
| P2 (`...target-B.md`) | INSTALLED_HOOK | identical to REPO_HOOK | empty | 1 |

### Park record A

```
$ python3 tools/bm_store.py park dace851dbe5e44a29a46935d5131adbd --version 1 \
    --session bm1-e00f74e60c906a70a425ba9e \
    --note "M15 probe: parking record A to test whether the fence still treats it as live"
parked: 'm15probe-fence-test-A' (lifecycle dace851dbe5e44a29a46935d5131adbd) is now parked at version 2
```

Ground truth verified independently of the hook, straight out of the store
(`python3 tools/bm_store.py dump`, filtered to the two probe lifecycle
uuids):
```
dace851dbe5e44a29a46935d5131adbd version 2 state parked name m15probe-fence-test-A
a84cd7d2da284953b7749a93106a1877 version 1 state active name m15probe-fence-test-B
```

### After park: THE decisive pair, queried at the same moment as foreign session B

Command (repository hook, parked path):
```
python3 tools/bm_fence_hook.py query docs/evidence/m15probe-scratch-target-A.md --session-id m15probe-foreignB
```
Output:
```
ALLOW docs/evidence/m15probe-scratch-target-A.md
```
STDERR: (empty). EXIT: 0.

Command (installed hook, parked path):
```
python3 /Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_fence_hook.py query docs/evidence/m15probe-scratch-target-A.md --session-id m15probe-foreignB
```
Output:
```
ALLOW docs/evidence/m15probe-scratch-target-A.md
```
STDERR: (empty). EXIT: 0.

Immediately afterward, the same foreign session against the still-active
record (repository hook):
```
python3 tools/bm_fence_hook.py query docs/evidence/m15probe-scratch-target-B.md --session-id m15probe-foreignB
```
Output:
```
DENY docs/evidence/m15probe-scratch-target-B.md: BrotherMode fence: docs/evidence/m15probe-scratch-target-B.md is inside the fence of the active record m15probe-fence-test-B (lifecycle a84cd7d2da284953b7749a93106a1877, version 1), which is owned by session bm1-e00f74e60c906a70a425ba9e. This session is bm1-17a8940311e2885e736ad81c, so it is not the writer for that path. Claimed as: docs/evidence/m15probe-scratch-target-B.md.
One writer per file is structural, not advisory: do not edit across the fence. Report the needed change to the owner instead. To take the fence over deliberately, run:
  python3 tools/bm_store.py adopt a84cd7d2da284953b7749a93106a1877 --version 1 --session bm1-17a8940311e2885e736ad81c --adopt-from-live-session
then re-claim the paths you need with `bm_store.py claim ... --session bm1-17a8940311e2885e736ad81c`.
```
STDERR: (empty). EXIT: 1.

Same command against the installed hook produced byte-identical stdout,
empty stderr, exit 1.

This is the pair that gives the run discriminating power: the parked path
and the active path were queried back to back, same foreign session, same
process environment, same moment, and they came out opposite. That rules
out the failure mode that killed the previous attempt, where every query
came back ALLOW regardless of state because something upstream (M14's
fail-open warnings) had already swamped the decision. No such warning fired
here, on either copy, at any point in this run.

### Bonus corroboration: real production active claim, not a synthetic one

```
$ python3 tools/bm_fence_hook.py query docs/plan/GANTT.html --session-id m15probe-foreignB
DENY docs/plan/GANTT.html: BrotherMode fence: docs/plan/GANTT.html is inside the fence of the active record night-orchestrator (lifecycle ba297466adf548eabd6706945627b671, version 2), which is owned by session bm1-3989fa298b7bfbb9a5fc71f9. This session is bm1-17a8940311e2885e736ad81c, so it is not the writer for that path. ...
```
EXIT: 1, empty stderr. The installed hook produced the same DENY, same exit
code, same stderr (empty). This is the exact path the M15 queue text names
("this session was refused on docs/plan/GANTT.html by that same fence"): as
of tonight it is refused because a real active claim covers it, which is
correct behaviour, not the parked-record defect the item asks about.

### Cleanup

Both probe records were parked (record A already was; record B parked
afterward as tidy-up, since it is my own throwaway record and the task
permits parking only records I created myself):
```
$ python3 tools/bm_store.py park a84cd7d2da284953b7749a93106a1877 --version 1 \
    --session bm1-e00f74e60c906a70a425ba9e --note "M15 probe: cleanup, measurement complete"
parked: 'm15probe-fence-test-B' (lifecycle a84cd7d2da284953b7749a93106a1877) is now parked at version 2
```
Final independent check: `dace851dbe5e44a29a46935d5131adbd version 2 state
parked`, `a84cd7d2da284953b7749a93106a1877 version 2 state parked`. No
active fence left behind by this probe. `git status --short` after the run
shows no repository-tracked file touched by this measurement; `claim` and
`park` only rewrote the gitignored `STATE.md` view and the gitignored
`.brothermode/store.sqlite3`, which is the tool's own documented behaviour,
not a manual edit.

## WHICH COPY

Every query above was run against both copies explicitly and is labelled
REPO_HOOK or INSTALLED_HOOK in the tables and commands. Both produced
identical decisions, identical stdout text, empty stderr, and identical
exit codes for every one of the eight query calls in this run (2 before
park times 2 copies, 2 after park times 2 copies, 2 GANTT.html bonus times 2
copies).

That identity is not an assumption, it was checked directly:
```
$ diff -u /Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_fence_hook.py tools/bm_fence_hook.py
(no output)
$ diff -u /Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_store.py tools/bm_store.py
(no output)
```
Both files are byte-identical between the installed copy and this checkout
right now, even though the installed copy's own git history sits 11 commits
behind this repository's HEAD (`git -C ~/.claude/skills/brothermode
log --oneline -5` tops out at `eacf249b`, this repo's HEAD is `1b804d6`,
and `git merge-base --is-ancestor eacf249b HEAD` in this repo confirms
`eacf249b` is an ancestor, 11 commits back via `rev-list --count`). Whatever
those 11 commits changed, they did not touch `bm_fence_hook.py` or
`bm_store.py`. The task brief's reported figure of "about 25 commits and one
schema behind, refusing with schema-ahead" does not hold at measurement
time: `SCHEMA_VERSION = 21` in both files, the live store's own `meta` table
reports `schema_version = 21`, and `python3
~/.claude/skills/brothermode/tools/bm_fence_hook.py whoami --session-id
m15probe-check-installed` opened this project's real store cleanly and
printed a label, no schema-ahead refusal. That may have been true at an
earlier point in the store's or the skill's history; it was not true
tonight, and every observation in this file is from tonight.

## SECONDARY OBSERVATION (not the M15 question, kept separate)

While delivering this document, the Write tool itself was refused, by a
DIFFERENT hook belonging to a different plugin (`brothersbe`, not
`brothermode`): `~/.claude/skills/brothersbe/tools/sbe_fence_hook.py`. This
has nothing to do with parked bm_store records; it is recorded here only
because a refusal against one's own write is itself a working positive
control, and because it sharpens a registry-mismatch defect (M13) already
tracked in this project's history.

Verbatim refusal:
```
BrotherSBE fence (L13, one writer per file): docs/evidence/night-2026-08-21-m15-parked-record.md is inside the file scope of a LIVE fence in /Users/khalil.maaouni/Documents/BrotherModeUp/STATE.md, opened by agent (unnamed agent) as sole writer for session bm1-3989fa298b7bfbb9a5fc71f9. This session is d9bad6dc-5ec8-4623-b92f-97ae3d3d7453, so it is not the writer for that path.
The fence line, verbatim:
  - night-m15-parked-measure (f54de3a821374b1186008fd00fa41ccf, version 1, ephemeral) [no tier] owner-session: bm1-3989fa298b7bfbb9a5fc71f9, agent: (no owner) objective: M15 measurement: does the installed fence hook treat a PARKED store record as live files: docs/evidence/night-2026-08-21-m15-parked-record.md |
Do not write across a fence. Any of these releases it, and nothing else does:
  1. Report the change to the fence owner and let that writer make it. L13 says overlapping writers queue, they do not run in parallel.
  2. If that work is finished, CLOSE the fence where it lives, in /Users/khalil.maaouni/Documents/BrotherModeUp/STATE.md, by appending its evidence block to that line: the marker LANDED, the exact command run, and its last lines. This hook stops refusing docs/evidence/night-2026-08-21-m15-parked-record.md the moment that line reads LANDED.
  3. To take the fence over deliberately, append ADOPTED to that line and write a new fence line naming this session (d9bad6dc-5ec8-4623-b92f-97ae3d3d7453) as sole writer, before you edit anything.
```

WHICH COPY: installed (`~/.claude/skills/brothersbe/tools/sbe_fence_hook.py`,
the only copy that runs, wired globally as this session's PreToolUse hook).
This repository does not contain a copy of `sbe_fence_hook.py` at all, so
there is no repository/installed comparison to make for this one; it is a
single-copy tool.

WHAT WAS COMPARED, read directly out of `sbe_fence_hook.py` (lines 823-826
and 384-399 of the installed copy): the fence line's `owner-session` field
holds `bm1-3989fa298b7bfbb9a5fc71f9`, a value in the `bm_fence_hook.py`
derived-label namespace (a one-way hash of a secret token, prefixed
`bm1-`). But `sbe_fence_hook.py`'s own `decide()` never derives or reads
that kind of label: it takes `my_session` from the environment variable
`BROTHERSBE_FENCE_SESSION` if set, else the RAW `session_id` field off the
PreToolUse payload (here, `d9bad6dc-5ec8-4623-b92f-97ae3d3d7453`, the plain
harness session id, unrelated to any `bm1-` derivation), then compares with
`same_session()`, which does prefix matching in both directions and nothing
else (no cross-namespace translation). A `bm1-` label and a raw harness
UUID share no common prefix, so the comparison legitimately returns "not the
same session" no matter which real session is asking, including, on this
evidence, the fence's own declared owner if that owner ever tried to write
through this same code path using its raw session id. This is consistent
with, and adds a concrete mechanism to, this project's own tracked defect
M13 ("the half of the registry mismatch that is still open"): a fence line
was populated with a derived label from one identity system while the hook
that reads it compares raw ids from a different one, so the declared owner
is unverifiable by construction, not just this session. Not investigated
further here: fixing `sbe_fence_hook.py` or its callers is out of scope for
an M15 measurement task, and this session made no edit toward it.

Per instruction from the dispatching session, this document was written to
a scratch path rather than directly to
`docs/evidence/night-2026-08-21-m15-parked-record.md`, precisely because of
the refusal quoted above: no `adopt-from-live-session` flag was passed, no
hand edit was made to `STATE.md`, no fence-off environment variable was
set, and no record this session did not create was closed or parked.

## WHAT WOULD CHANGE THIS VERDICT

A future edit to `active_claims()` in either copy of `bm_store.py` that
selects rows without the `WHERE r.state='active'` filter (or any change
that lets `decide()` compare against a parked record's `session_id`) would
flip this from ALLOW to DENY on a parked-only path and should be caught by
the regression test this item's done-check asks for. Re-run the same
paired query (one parked path, one active path, same foreign session, same
moment, both hook copies) after any change to `bm_store.py`'s claims query,
`bm_fence_hook.py`'s `active_claims()`, or the `park` command's state
transition, and if the parked path ever comes back DENY, or a fail-open
warning appears on stderr where the state table above shows none, that is
new evidence against this verdict.
