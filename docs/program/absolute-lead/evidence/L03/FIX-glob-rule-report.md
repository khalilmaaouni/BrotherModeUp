# FIX, the GLOB RULE: report

A FOUNDER DECISION taken on 2026-08-05, implemented. Not a bug fix: the
founder was shown this collision and both alternative remedies with what
each costs, and chose a third rule.

**THE RULE.** An `allowed_paths` entry grants a candidate path ONLY IF it
also grants everything a FENCE over that candidate would cover.

**What that means in one sentence a founder can hold the system to.** A
plain path grants its whole subtree; a pattern grants the FILES it matches
at its own depth, and no directory.

Files written, and no others:

* `tools/bm_store.py`
* `tools/test_bm_store.py`
* `docs/KNOWN-LIMITS.md`
* `docs/FULL-AUTO.md`
* `docs/program/absolute-lead/evidence/L03/RED-glob-rule.txt`
* this report

`SECURITY.md` was NOT written: its line-count guard does not trip (section
6). `tools/bm_controller.py`, `tools/test_bm_controller.py` and every other
file were READ, never written.

Baseline: `FIX-round5-store-report.md` section 3, which measured this exact
collision (55440 triples, 35 violations, all the same shape) and recorded
both rejected remedies with their verbatim test failures.

---

## 1. The four required outcomes, each with the test that pins it

All four live in `TestAPatternGrantsOnlyWhatAFenceOverItWouldAlsoGrant`
(`tools/test_bm_store.py`, at the end of the file), and every one asserts
through `Store.gate_check`, the surface `bm-autonomy gate-check` prints and
the controller branches on, rather than through `path_within_allowed`
directly.

| # | Outcome | Test | Verdict rows it asserts |
|---|---|---|---|
| 1 | `['src/*']` no longer grants `src/app`, and still grants `src/a.py` | `test_a_pattern_no_longer_grants_a_directory_at_its_own_depth` | `src/app` REFUSED-SCOPE, `src/app/deep/keys.pem` REFUSED-SCOPE, `src/a.py` ALLOWED, `src` REFUSED-SCOPE |
| 2 | `['api/*.py']` still grants `api/pay.py` | `test_a_founder_pattern_over_files_still_grants_the_files_it_names` | `api/pay.py` ALLOWED, `api/pay.py/` ALLOWED, `api/notes.md` REFUSED-SCOPE, `api` REFUSED-SCOPE, `api/sub/deep/secrets.env` REFUSED-SCOPE |
| 3 | `['*']` still grants `main.py`, no longer grants `src` | `test_a_bare_star_grants_a_file_at_the_root_and_no_directory` | `main.py` ALLOWED, `src` REFUSED-SCOPE, `src/a.py` REFUSED-SCOPE |
| 4 | The exhaustive sweep shows ZERO violations | `test_no_path_this_gate_allows_names_a_file_it_would_refuse` | 0 violations over 5840400 triples |

A fifth test in the same class, `test_a_plain_path_still_grants_its_whole_subtree`,
is a CONTROL: it was green before the change and is green after, and it
fails if the narrowing takes the non-glob branch with it.

Outcome 2's test and the control were BOTH GREEN in the RED capture, on
purpose and labelled as controls there. Only the two rows the decision
moves went red.

---

## 2. The sweep, before and after

The sweep lives at module level in the test file (`_glob_rule_sweep`) so
that the test and the command below run the SAME generator, with no second
implementation of it anywhere. A violation is a triple (allowance,
candidate, file) where the allowance GRANTS the candidate, a fence over
that candidate COVERS the file, and the same allowance REFUSES that file by
name. Both relations come from the store's own primitives
(`path_within_allowed` for the verdict, `_coverage_key` plus
`_prefix_contains` for the fence coverage, which is the directional half of
the call `tools/bm_fence_hook.py:637` makes), so this measures shipped
semantics rather than a model of them.

Matrix: 1884 allowance shapes (one to three segments over five literal
tokens and seven pattern tokens: `*`, `*.py`, `?pp`, `[ab]`, `**`, `s*`,
`*.pem`), 155 candidate shapes (one to three segments over the literal
tokens, which is the declarable universe since round 5 refused a pattern as
a write scope), and 20 covered paths per pair, six of them directories and
fourteen files.

| | Triples | Violations |
|---|---|---|
| Round 5's sweep, for reference | 55440 | 35 |
| This sweep, BEFORE (captured in `RED-glob-rule.txt`) | 5840400 | **95** |
| This sweep, AFTER | 5840400 | **0** |

The 95 were 23 distinct (allowance, candidate) pairs, at allowance depth 1
and 2, every one under a GLOB allowance and every one the same shape round
5 named. Verbatim, after the change:

```
$ python3 -c "
import sys; sys.path.insert(0, 'tools')
import test_bm_store as t
tr, v = t._glob_rule_sweep()
print('triples', tr); print('violations', len(v))
"
triples 5840400
violations 0
```

**What the sweep's universe assumes, stated rather than buried.** Its
directory names carry no extension and its file names do. That is not a
convenience of the fixture: it is exactly the reading the rule now makes of
a name (section 3), so the tree a founder would write is the tree the sweep
runs over. The one case the reading cannot see is a DIRECTORY whose name
carries an extension, and it is disclosed in `docs/KNOWN-LIMITS.md` in the
same paragraph as the rule.

---

## 3. What landed in the store

`tools/bm_store.py`, five hunks, all in the authorisation boundary and its
docstrings. `paths_overlap` was NOT touched: it answers the symmetric
fence question ("can these two declared claims name the same file"), which
is a different question with different semantics, and the fence hook and
the claim-time overlap check both depend on it.

**New private function, `_names_a_file(segment)` (bm_store.py:565).** True
when a path's final segment carries an extension. `a.py` and `keys.pem`
name files; `src`, `app` and `Makefile` do not, and neither does a dotfile
like `.env` (nothing in front of the dot) or a trailing dot like `a.`
(nothing behind it). Every one of those readings errs the same way on
purpose: reading a directory as a file hands out a fence over its whole
subtree, and reading a file as a directory costs a refusal the founder
answers by naming the path literally.

**`path_within_allowed` (bm_store.py:583), glob branch only.** After the
depth-exact segment match it now also requires `_names_a_file` of the
candidate's final segment. Three lines, one comment. Why this is the whole
rule: a pattern grants nothing below its own depth, so a pattern may grant
only a candidate with no subtree, so a pattern may grant only a file.

The NON-GLOB branch is byte-identical, which is deliberate: the 6682-triple
containment property proved over it in round 3 is untouched, and a plain
path is still the recursive spelling.

**`Store.gate_check`'s docstring (check 5).** It already stated the
property a reader may hold the code to. It now also states why depth-exact
matching alone could not deliver it, and names the sweep.

### Signature and behaviour changes

`_names_a_file` is new and private. No public signature moved, no return
shape moved, no new refusal reason, no enumerated constant touched
(`AUTONOMY_FLOORS` and `CONTROLLER_STATE_TRANSITIONS` were not read from or
written to). The one behaviour change is the intended one: a PATTERN entry
in `allowed_paths` no longer authorises a directory-shaped name at its own
depth. It only ever narrows. Every path refused today was granted
yesterday, and nothing granted today was refused yesterday.

Two functions read `path_within_allowed`: `Store.gate_check`
(bm_store.py:13148) and `ControllerEngine._fence_no_longer_holds`
(bm_controller.py:2996 as that file stands right now, READ not written;
the parallel writer described in section 7 is moving lines in it). The second compares a fence's
HELD paths against a unit's write scope; every write scope entry has been a
literal path since round 5 and every shipped fence claim is built from
those same literal entries, so that call site takes the untouched non-glob
branch. The controller suite (183 tests) is green, which is the evidence
for that sentence rather than the argument for it.

---

## 4. The superseded test row, quoted before and after

`tools/test_bm_store.py`,
`TestGlobAllowedPathsAreDepthExact.test_a_bare_star_is_one_segment_and_a_directory_glob_is_one_level`,
at line 17441 before the change and 17450 after. This is the ONLY existing
test in any suite that the decision moves; the whole store suite was run to
find out, and it was the single failure.

BEFORE:

```python
    def test_a_bare_star_is_one_segment_and_a_directory_glob_is_one_level(self):
        _gate_verdicts(self, ["*"], (
            ("main.py", "ALLOWED"),
            ("src", "ALLOWED"),
            ("src/a.py", "REFUSED-SCOPE")))
        _gate_verdicts(self, ["src/*"], (
            ("src/app", "ALLOWED"),
            ("src/app/main.py", "REFUSED-SCOPE"),
            ("src", "REFUSED-SCOPE")))
```

AFTER (the comment above the rows in the file says the rule changed, why,
and that it narrows; it is quoted in full because it is the record):

```python
    def test_a_bare_star_is_one_segment_and_a_directory_glob_is_one_level(self):
        # THE RULE CHANGED HERE, by founder decision on 2026-08-05, and
        # these two rows are the ones it moved. Round 4 pinned ('src',
        # ALLOWED) under ['*'] and ('src/app', ALLOWED) under ['src/*']:
        # a pattern matched a plain DIRECTORY at its own depth. Round 5
        # then MEASURED what that costs (FIX-round5-store-report.md
        # section 3): a fence over a directory covers its whole subtree,
        # so 'src/app/deep/keys.pem' was writable under ['src/*'] although
        # gate_check REFUSES that file when it is named directly, and the
        # property gate_check's own docstring states was false 35 times
        # over 55440 triples. Round 5 stopped rather than move a pinned
        # verdict; the founder moved it, choosing this rule over the two
        # measured alternatives (a pattern granting the subtree of
        # everything it matches reinstates the whole-project grant, and a
        # pattern granting nothing breaks ['api/*.py']).
        #
        # It NARROWS: every row below that moved went from ALLOWED to
        # REFUSED-SCOPE, and nothing that was refused became allowed. The
        # rest of this class is untouched and still green, including the
        # ('src/a.py', REFUSED-SCOPE) row directly under this comment,
        # which is the depth-exactness round 4 landed.
        _gate_verdicts(self, ["*"], (
            ("main.py", "ALLOWED"),
            ("src", "REFUSED-SCOPE"),
            ("src/a.py", "REFUSED-SCOPE")))
        _gate_verdicts(self, ["src/*"], (
            ("src/app", "REFUSED-SCOPE"),
            ("src/app/main.py", "REFUSED-SCOPE"),
            ("src", "REFUSED-SCOPE")))
```

**Two rows moved, not one, and both are the same decision.** The brief
named `('src/app', ALLOWED)` under `['src/*']`; required outcome 3
(`['*']` no longer grants `src`) moves `('src', ALLOWED)` under `['*']` in
the same test method. They are the same rule seen at two depths, and the
neighbouring `('src/a.py', REFUSED-SCOPE)` row under `['*']`, which the
brief required to stay green, is green and untouched.

Two docstrings were also amended, no assertions in them changed:

* `TestGlobAllowedPathsAreDepthExact`'s class docstring, which said a
  pattern "grants exactly what it matches at its own depth". Depth-exact
  was necessary and not sufficient; the amendment says so and points at the
  new class.
* `TestGlobAllowancesGrantOnlyWhatTheyLiterallyMatch`'s class docstring,
  which said the directory-shaped residual SURVIVES and that the class
  characterises it rather than asserting it away. It promised to stay green
  if a later round removed the residual, and it did: its loops are now
  vacuous and its guard against a NEW violation shape is unchanged and
  unweakened. Leaving that prose describing a hole that no longer exists
  would have been a false record.

---

## 5. Documentation

**`docs/KNOWN-LIMITS.md`, three places, all consistent.**

1. The paragraph at former lines 985 to 990, which began "A contract that
   allows a path PATTERN" and described the pattern form as a coarser
   boundary than it looks. Replaced: it is no longer a limit, it is the
   rule, stated positively with what it now refuses (`api/notes.md`, `api`
   itself, anything deeper, and any DIRECTORY it matches at its own depth,
   which is the new refusal), and with the naming reading and its one blind
   spot named in the bullet beneath it.
2. The round-4 "THE RULE, in one sentence" entry, which still said "grants
   exactly what it matches at its own depth". Corrected to "grants the
   FILES it matches at its own depth", with a sentence recording that the
   round-4 wording admitted a directory and therefore, through the fence
   over it, a subtree.
3. The "Not closed, and what stands in the way" entry that described this
   exact residual and why round 5 stopped. It is closed, so leaving it in a
   "Not closed" list would have been false; it now records the closure, the
   rule chosen, the two alternatives rejected, and points here.

**`docs/FULL-AUTO.md`**, the founder-facing bullet where `allowed_paths` is
actually documented for a reader (`docs/AUTONOMY.md` does not mention
`allowed_paths`; grepped, confirmed, and not written to). The bullet now
reads: a plain path grants its whole subtree, a pattern grants the FILES it
matches at its own depth and no directory, `src/*` does not authorise
`src/app` because claiming a directory fences its whole subtree and that
would hand out `src/app/deep/keys.pem` which the same contract refuses when
you name it, a name carrying an extension is read as a file, write the
plain directory when you mean the subtree and the file's own name when you
mean one file.

---

## 6. Done-check, run after the last edit

Quoted verbatim from the brief, each with its exit code:

```
$ python3 tools/test_bm_store.py          -> Ran 883 tests, OK, exit 0
$ python3 tools/test_bm_autonomy.py       -> Ran  58 tests, OK, exit 0
$ python3 tools/test_bm_controller.py     -> Ran 183 tests, OK, exit 0
```

The property sweep, after the change: **0 violations over 5840400
triples** (command and output in section 2).

One suite beyond the three was run, because it is the one that actually
READS the two documents this change edits (the three above only mention
them in comments):

```
$ python3 tools/test_bm_docs.py           -> Ran 199 tests, OK (skipped=5), exit 0
```

`tools/test_all.py` was NOT run; the orchestrator runs the gate.

**The SECURITY.md line-count guard does not trip, so SECURITY.md was not
written.** Re-measured with the command from the brief:

```
$ find tools -name "*.py" -o -name "*.sh" | xargs wc -l | tail -1
   93182 total
```

`SECURITY.md:101` claims "about 91,100 lines"; the guard in
`tools/test_bm.py:1105` fails at 15 percent drift and the drift is 0.0223.
Correcting a figure that is inside its own tolerance would have been an
edit to a file I was allowed to touch only if the guard tripped.

---

## 7. Anything blocked, and everything a reader should not have to discover

* **Nothing was blocked.** No existing test outside the one superseded
  method collided, so the STOP protocol was never reached.
* **A parallel writer is live in this tree.** `tools/bm_controller.py` and
  `tools/test_bm_controller.py` were being edited while this work ran (they
  changed at 13:25 during my first controller run, which caught them
  mid-edit and reported 11 failures in `TestCrossFamilyF2NonDictWorkerResult`
  and `TestCrossFamilyF3InheritedGitEnvironment`). Those failures are not
  mine and are gone: I proved it by disabling only this change's own line in
  `path_within_allowed`, re-running the controller suite (OK), restoring,
  and re-running it again (OK). The same writer is also editing the two
  documents I was told to write: `docs/FULL-AUTO.md` carries two hunks that
  are not mine (the reserved lane and the stop path) and
  `docs/KNOWN-LIMITS.md` carries one (round 7's reserved-lane and kill
  switch entries, at the end of the file). My hunks are the
  `allowed_paths` bullet in FULL-AUTO and three in KNOWN-LIMITS, at former
  lines 985, 1022 and 1151. Both files were re-read after every edit and
  all four of my hunks are present, but two writers in one document is a
  lost-update risk that belongs to whoever holds the fence, not to me.
* **The rule reads a NAME, and a name is not a filesystem.** A directory
  whose name carries an extension (`src/data.bak`) is still admitted by a
  pattern at its own depth, and a fence over it would cover what is inside
  it. This is the one shape of the original violation that survives, it is
  disclosed in `docs/KNOWN-LIMITS.md` beside the rule, and it is the reason
  the sweep's universe is described in section 2 rather than presented as
  neutral. Closing it needs a filesystem check inside `gate_check`
  (`os.path.isdir` against the store root), which is a real option and was
  deliberately not taken here: it makes an authorisation verdict depend on
  what happens to be on disk at the moment it is asked, it is still
  defeated by a directory created after the check, and it was outside the
  four outcomes the founder pinned. It belongs to whoever owns the next
  rule decision, with this paragraph as the input.
* **What the rule costs a founder in practice**, so it is not discovered as
  a surprise refusal: a pattern will no longer authorise an extensionless
  file such as `Makefile`, `LICENSE` or `Dockerfile`, or a dotfile such as
  `.env`. Naming those literally works exactly as it always has.
