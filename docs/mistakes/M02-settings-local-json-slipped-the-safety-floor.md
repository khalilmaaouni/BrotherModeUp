# M02: the safety floor named one settings file and missed its twin

## WHAT HAPPENED

Plain language: BrotherMe has a hard floor, a list of places that no permission
slip may ever authorise a machine to write, because writing there means rewriting
the permission system itself. The floor named `.claude/settings.json`. It did not
name `.claude/settings.local.json`, which in Claude Code carries the same power
(permissions and hooks) and takes higher precedence.

So an autonomous session, working under one legitimately signed authorisation,
could get a fence claimed over the local settings file and a work brief dispatched
telling a worker to write it. That is exactly the write the floor exists to
forbid.

Technical detail: `AUTONOMY_FLOOR_PATHS` was `(STORE_DIRNAME, ".git",
".claude/settings.json")`, a list of literal names. The two directory entries were
matched by subtree containment, so every spelling of `.git/...` was caught, but the
settings entry was a single literal, so any sibling name slipped it.

## HOW IT WAS FOUND

By an adversarial refuter driving the shipped command line tools as real
subprocesses against five throwaway roots under `mktemp -d`, with the live store
never touched. It was reproduced end to end, all the way to a dispatched brief,
not merely reasoned about.

Report: `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/REFUTE-auth-gaps.md`
(CONFIRMED A1, lines 38 to 82).

## THE EVIDENCE

From the refute report, the decisive dispatch test with its calibration twin
(`.git/config`, which the floor did catch) in the same run under the same
contract:

```
# unit write_scope=['.git/config']  (known-bad)
step -> note: no selectable unit could be claimed this wave (... gate_check refused ...)
       gitscope   READY   fence=(none)      # never dispatched, never fenced

# unit write_scope=['.claude/settings.local.json']  (the hole)
step -> dispatched: settings
       controller_brief {... "write_scope": [".claude/settings.local.json"]}
       settings   DISPATCHED   fence=5096cc68f2c644e388e2063233019421
```

The failing assertions once the hole was written as a test, from
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L09/RED-auth.txt`
lines 556 to 584:

```
FAIL: test_gate_refuses_the_whole_settings_family_under_a_dot_contract
      (candidate='.claude/settings.local.json')
AssertionError: 'ALLOWED' != 'REFUSED-FLOOR'

FAIL: test_gate_refuses_the_whole_settings_family_under_a_dot_contract
      (candidate='.claude/settings.staging.json')
AssertionError: 'ALLOWED' != 'REFUSED-FLOOR'

FAIL: test_sign_refuses_settings_local_json
AssertionError: OwnershipRefused not raised
```

Note that the refuter also found `settings.staging.json`, a name nobody had
thought of, which is why the fix had to cover a family and not a second literal.

## HOW IT WAS FIXED

In `/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_store.py`:

- `AUTONOMY_FLOOR_PATHS` at tools/bm_store.py:3472 keeps only the two directory
  subtrees (`.brothermode` and `.git`).
- A new predicate `_is_claude_settings_path` at tools/bm_store.py:3495 floors any
  file directly under `.claude` whose name starts with `settings.` and ends with
  `.json`. That covers `settings.json`, `settings.local.json` and any
  `settings.<qualifier>.json`.
- It is wired into `_governance_floor_hit` at tools/bm_store.py:3513, which is the
  one place both enforcement points call: sign time (refusal code `path-is-floor`,
  tools/bm_store.py:13234) and gate time (`REFUSED-FLOOR`).
- Defence in depth for the related gap: `upsert_units` now refuses
  `write-scope-is-floor` at tools/bm_store.py:14433 if a planned unit names a floor
  path, so the class is closed one layer earlier than the gate.

Deliberately NOT floored: an enterprise or managed settings file, because a grep
over `scripts/`, `docs/` and `tools/` found no such path cited anywhere in this
tree, and inventing a path nobody uses would be guessing. That reasoning is
recorded in the fix report at lines 508 to 526.

Verification after the fix, from the fix report's done-check:

```
$ python3 tools/test_bm_store.py
Ran 993 tests in 46.957s

OK
```

## THE RULE THIS PRODUCES

A safety floor written as literal filenames is already out of date: floor the
family (the directory, or the name pattern) and prove it with a spelling sweep,
because the file you did not name is the one an attacker will use.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, but only just, and this is the closest call of the night. The round-1
floor was written, reviewed, tested green and considered done. It was live in the
working tree, not yet committed or pushed, when the refuter drove a real
dispatched write through it. Round 1 and round 2 both landed inside one commit
(ac7ef87), so no user ever ran the incomplete floor. If the refute round had been
skipped for time, this would have shipped.
