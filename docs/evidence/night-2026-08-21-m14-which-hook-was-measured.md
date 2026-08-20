# M14: which hook was actually measured

Status: CURRENT
Date: 2026-08-21 (night), measurement agent, BrotherModeUp repository

## The question, in one sentence

Was M14 (docs/plan/QUEUE.json, state "queued") retired by the board and the
newest handover pack on evidence gathered against the wrong hook, given that
M14's own text names "the installed sbe fence hook" and the retirement
evidence names "the repaired hook" from a same-night schema fix?

## VERDICT

M14 WAS RETIRED ON EVIDENCE ABOUT THE WRONG HOOK: the retirement session
tested and repaired `bm_fence_hook.py` (a BrotherMode, SQLite-store defect,
unrelated to STATE.md text) and applied that clean result to M14, whose real
subject is `sbe_fence_hook.py` (BrotherSBE, STATE.md text parser), which this
session measured directly, twice, and found printing 34 "no readable `files:`
scope" warnings on every write, not zero. M14's true status is OPEN and
REPRODUCING, worse than originally reported (34 warning lines, not six).

## WHICH HOOK IS WHICH

| Name | Plugin | Path actually wired right now | Mechanism | Status this session found |
|---|---|---|---|---|
| `bm_fence_hook.py` | brothermode (`brothermode@skills-dir`, v3.3.2, loaded) | `~/.claude/skills/brothermode/tools/bm_fence_hook.py` | Reads `.brothermode/store.sqlite3` directly. Never parses STATE.md text. | Zero STATE.md warnings, structurally cannot show M14's symptom. |
| `sbe_fence_hook.py` | brothersbe (`brothersbe@brothersbe`, v3.2.0, enabled user + project scope) | `~/.claude/plugins/cache/brothersbe/brothersbe/3.2.0/tools/sbe_fence_hook.py` | Parses `STATE.md` as text for `- name (...): files: ...` fence lines, per `docs/HOOKS.md`. | 34 "no readable files: scope" warnings per write. M14 reproduces. |
| `brothersbe@skills-dir` | brothersbe (repo clone) | `~/.claude/skills/brothersbe/tools/sbe_fence_hook.py` | Same code family as above. | NOT LOADED: `claude plugin list` reports it shadowed, the name "brothersbe" is already taken by `brothersbe@brothersbe`. Not the active copy; not used for measurement. |
| repo copy | this repo's own source | `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_fence_hook.py` | Same family as the loaded skills-dir copy. | Not what Claude Code runs; the installed skills-dir copy is what fires (confirmed by `claude plugin list`, "Status: loaded" only appears against `brothermode@skills-dir`). There is no `sbe_fence_hook.py` anywhere under this repo's own `tools/`. |

## THE MEASUREMENT

### 1. M14's own text (docs/plan/QUEUE.json)

```
python3 -c "import json; d=json.load(open('docs/plan/QUEUE.json'));
print([x for x in d['queue'] if x.get('id')=='M14'][0])" 2>/dev/null || true
```

Read directly (state field): `"state": "queued"`. Full title, verbatim:

> "the installed sbe fence hook reads STATE.md's HUMAN PROSE section as live
> fence lines: six historical narrative bullets (finish-and-ship, docs-refresh,
> loop0-builder and three closure notes) are each parsed as a live fence with
> no readable files: scope, and the hook then FAILS OPEN on every one, printing
> a warning per line on every single write. ... (measured 2026-08-20 by the
> day-run closing session by invoking the installed hook directly)"

It names "the installed sbe fence hook" explicitly. "sbe" is the BrotherSBE
product prefix; it is not a shorthand anyone in this project's own vocabulary
uses for BrotherMode's "bm" hook. The two are different plugins, different
code.

### 2. Which hook is wired, and which copy is loaded

```
$ claude plugin list 2>&1 | grep -B1 -A5 "brothersbe@brothersbe" | head -20
  brothersbe@brothersbe
    Version: 3.2.0
    Scope: user
    Status: enabled
  brothersbe@brothersbe
    Version: 3.2.0
    Scope: project
    Status: enabled
  (three more project-scope entries, all enabled, all 3.2.0)

$ claude plugin list 2>&1 | grep -A4 "brothersbe@skills-dir"
  brothersbe@skills-dir: Not loaded, the name "brothersbe" is already taken
  by an installed plugin (brothersbe@brothersbe), which takes precedence.

$ claude plugin list 2>&1 | grep -A4 "brothermode@skills-dir"
  brothermode@skills-dir
    Version: 3.3.2
    Scope: user
    Path: ~/.claude/skills/brothermode
    Status: loaded
```

`~/.claude/plugins/cache/brothersbe/brothersbe/3.2.0/hooks/hooks.json` wires,
on `PreToolUse` matcher `Edit|Write|MultiEdit|NotebookEdit|CreateDirectory|
Delete|apply_patch`: `sbe_authority_hook.py` and `sbe_fence_hook.py`, plus
`sbe_bash_write_guard.py` on `Bash`. `~/.claude/skills/brothermode/hooks/
hooks.json` wires, on `PreToolUse` matcher `Edit|Write|MultiEdit|NotebookEdit|
Bash`: `bm_fence_hook.py`. Both plugins are enabled at once, so both hooks fire
on every Edit/Write in this repository, independently.

### 3. STATE.md still carries the shape M14 describes

`STATE.md` is 3439 lines. Lines 7 to 842 are `<!-- BEGIN/END GENERATED
BROTHERMODE STATE -->`, rendered by `bm_store.py`. Everything after line 842
is hand-written prose. Line 884 onward:

```
## Live fences (wave 7, finish-and-ship, 2026-08-01, session 17838b98)
...
- finish-and-ship (main session, Fable 5, SOLE WRITER of tracked files):
  the whole working tree. ...
## Wave 7 amendment (2026-08-01): one builder fence carved out
- docs-refresh (agent, sonnet, Builder profile): docs/REMAINING.md and
  docs/NOT-FINALIZED.md item 11 ONLY. Tier T1. TTL 2h. ...
- docs-refresh agent fence closed clean (only its two files, suite green).
...
- loop0-builder (agent, sonnet, Builder profile, T2, TTL 4h, budget 100k):
  VERSION, pyproject.toml, ...
```

This is present, unchanged, and shaped exactly like a fence declaration in
plain narrative. The section did not disappear and did not change shape; that
is not why M14 would retire.

### 4. Measuring `sbe_fence_hook.py`, the actually-named, actually-active copy

First, its own documented CLI diagnostic (`docs/HOOKS.md`, "Check what it can
see before you trust it"), run from the repo root:

```
$ cd /Users/khalil.maaouni/Documents/BrotherModeUp
$ python3 /Users/khalil.maaouni/.claude/plugins/cache/brothersbe/brothersbe/3.2.0/tools/sbe_fence_hook.py fences .
exit code: 0
STDOUT: (empty)
STDERR (134 lines total):
  line 1: registry patterns: ./STATE.md
  lines 2-35 (34 lines): sbe_fence_hook: ./STATE.md carries a live fence line
    with no readable `files:` scope, so this hook cannot tell what it owns
    and did NOT enforce it. Line: - finish-and-ship (main session, Fable 5,
    SOLE WRITER of tracked files): the whole working tree. ...
    [continues for docs-refresh (x2), loop0-builder, and 30 more historical
    bullets spanning wave 7 through wave 15b and fences V7 to V11]
  lines 36-133 (98 lines): LIVE STATE.md | agent ... | session ... | files ...
    [these are the real, current, generated-block fences: legitimate]
  line 134: 98 live fence line(s) enforceable from .
```

Second, the real wire contract: a PreToolUse JSON payload on stdin, matching
the fields `docs/HOOKS.md` documents (`tool_name`, `tool_input`, `session_id`,
`cwd`, `project_dir`), targeting this very deliverable's own path:

```
$ cat pretooluse_payload.json
{
  "session_id": "m14probe-9f1c2a",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/Users/khalil.maaouni/Documents/BrotherModeUp/docs/evidence/night-2026-08-21-m14-which-hook-was-measured.md",
    "content": "probe payload, not actually written by this hook call"
  },
  "cwd": "/Users/khalil.maaouni/Documents/BrotherModeUp",
  "project_dir": "/Users/khalil.maaouni/Documents/BrotherModeUp"
}

$ python3 /Users/khalil.maaouni/.claude/plugins/cache/brothersbe/brothersbe/3.2.0/tools/sbe_fence_hook.py < pretooluse_payload.json 1>stdout.txt 2>stderr.txt
exit code: 0
$ wc -c < stdout.txt
0
$ wc -l < stderr.txt
34
$ grep -c "no readable" stderr.txt
34
```

Path invoked: `/Users/khalil.maaouni/.claude/plugins/cache/brothersbe/
brothersbe/3.2.0/tools/sbe_fence_hook.py`, the exact file `claude plugin list`
confirms is the enabled, loaded copy. Stdout empty means allow (per the
documented wire contract); stderr carries 34 verbatim "no readable `files:`
scope" warning lines, quoting `finish-and-ship`, `docs-refresh` (twice),
`loop0-builder`, and 30 more historical bullets. M14 named six as
illustration; the real count on every write is 34, because the same defect
recurs through every "Wave" section in the archived narrative, not only Wave
7. This is a live reproduction against the exact component M14 names, using
the exact wire format Claude Code uses.

### 5. The same payload against `bm_fence_hook.py`, for direct comparison

```
$ python3 /Users/khalil.maaouni/.claude/skills/brothermode/tools/bm_fence_hook.py < pretooluse_payload.json 1>stdout.txt 2>stderr.txt
exit code: 0
$ wc -c < stdout.txt
0
$ wc -l < stderr.txt
1
$ cat stderr.txt
bm_fence_hook: FAILING OPEN, the write is allowed and the fence was NOT
checked. Reason: the store at /Users/khalil.maaouni/Documents/BrotherModeUp/
.brothermode/store.sqlite3 holds no active claims, so there is no fence to
enforce
```

Zero "no readable" warnings, one line total. `bm_fence_hook.py` never parses
STATE.md text at all under any code path this session found: it reads
`.brothermode/store.sqlite3` directly and stops there. It was structurally
unable to show M14's symptom before tonight's repair, and remains unable to
show it after, because that was never its mechanism.

### 6. The retirement evidence itself, read in full, names only `bm_fence_hook.py`

`docs/plan/GANTT.html`, `docs/handover/2026-08-20-day3-fence-repair/GANTT.html`,
and the newest pack's copy at `docs/handover/2026-08-21-night-2026-08-21/
GANTT.html` all carry the identical span at the M14 tick:

> "Zero warning lines across every probe against the repaired hook. The 3.2.0
> era copy that showed six warnings per write aborted on the STORE READ before
> it could ever reach STATE.md parsing, so the symptom cannot occur there.
> Three sessions had given M14 three different causes."

The tick immediately before it in the same GANTT, titled "The fence was dead
repository wide, and it was the INSTALLED copy, not this tree's code",
describes: "stderr: 'FAILING OPEN, ... Reason: store ... schema 21; this
BrotherMode only understands up to schema 20'." The tick after it, "Repaired,
and proven by a refusal fired at the live store", describes: "Install clone
main moved to origin/main ... the same GANTT.html payload -> DENY". Both
neighboring ticks are unambiguously about `bm_fence_hook.py` and
`.brothermode/store.sqlite3` (schema numbers, the store, `docs/plan/
GANTT.html` as the test path, "Install clone main moved to origin/main"); the
M14 tick reuses the same "the repaired hook" pronoun mid-paragraph with no
hook name change.

`docs/handover/2026-08-20-day3-fence-repair/01-HANDOVER.md` (human-written,
preserved verbatim) confirms it item by item: item 2, "FOUND AND FIXED A DEAD
FENCE... because the store is at schema 21 and the installed copy understood
at most schema 20... Fixed by pointing the clone's main at origin/main."; item
4, directly under it, "M14 DID NOT REPRODUCE. Zero warning lines across every
probe against the repaired hook."

`docs/handover/2026-08-20-day3-fence-repair/03-RULES-AND-PROCESS-FIXES.md`,
the session's own stated lesson: "ASK WHICH COPY OF A HOOK ACTUALLY FIRES,
BEFORE MEASURING ANYTHING ABOUT IT. This project ships tools/bm_fence_hook.py
and Claude Code runs ~/.claude/skills/brothermode/tools/bm_fence_hook.py.
Tonight those two disagreed completely... M14 has now been reported with
three different causes by three sessions. Tonight's contribution is that the
symptom does not reproduce at all on current code, and that the earlier copy
aborted before it could ever occur."

A case-insensitive, whole-word search of the entire
`docs/handover/2026-08-20-day3-fence-repair/` pack for "sbe" or
"sbe_fence_hook" or "brothersbe" returns nothing that is about this hook: the
only "BrotherSBE" hits are one unrelated queue item (M13, a different fix
entirely) and routine mentions of the sibling project's own overnight grant
and consumer fields. `sbe_fence_hook.py` is never invoked, quoted, or named in
the pack that retired M14.

The newest handover pack, `docs/handover/2026-08-21-night-2026-08-21/`, does
not re-test anything: its `07-NEXT-SESSION-PROMPT.md` line 48 states "M14 does
not reproduce on current code" as an inherited fact, carried forward from the
2026-08-20 pack, with no new measurement of its own. This is the exact
failure mode `03-RULES-AND-PROCESS-FIXES.md` in the SAME prior pack warns
against: "WHEN A FINDING IS INHERITED, RE-RUN ITS PRECONDITION BEFORE
INHERITING ITS CAUSE." Nobody did, for M14, across the hand-off.

### 5-in-the-method (constructed reproduction): not needed and not run

The task allowed a constructed scratch-project STATE.md as a fallback for the
case where the live estate came back clean. It did not: section 4 above is a
live reproduction, against the real repository, the real installed hook, and
the real wire contract, which is stronger evidence than a synthetic fixture
would add. Building one was skipped as redundant.

## WHAT WOULD CHANGE THIS VERDICT

- If `claude plugin list` is re-run later and `brothersbe@brothersbe` is no
  longer enabled, or a newer version's `sbe_fence_hook.py` no longer parses
  `STATE.md` as text (an architecture change parallel to what happened to
  `bm_fence_hook.py`), the 34-warning measurement in section 4 would need
  re-running against whichever copy is then active.
- If a future session edits `STATE.md` to remove or fence off the hand-written
  prose after line 842 (for example, actually moving it into
  `docs/evidence/2026-08-01-state-md-wave-era.md`, which line 3 of STATE.md
  already claims happened but which section 3 above shows did not), the
  warning count would drop, possibly to zero, and M14 would then be correctly
  retired for a stated reason.
- If someone finds a probe this session missed where the day3-fence-repair
  session did invoke `sbe_fence_hook.py` directly and got a clean result, that
  would contradict this measurement and both would need reconciling; no such
  probe was found in the pack, the board, or a repo-wide search for "sbe" in
  that pack.
