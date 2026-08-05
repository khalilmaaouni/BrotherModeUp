# FIX round 6, the STORE half (DECLARATION side): report

Writer: the round-6 STORE writer. Files written, and no others:

* `tools/bm_store.py`
* `tools/test_bm_store.py`
* `docs/KNOWN-LIMITS.md` (one appended section, nothing above it touched)
* `docs/program/absolute-lead/evidence/L03/RED-round6-store.txt`
* this report

`tools/bm_controller.py`, `tools/test_bm_controller.py` and
`docs/FULL-AUTO.md` belong to the other writer of this round and were READ,
never written. That writer closes the EXECUTION side of the same finding
(what the engine does with an entry once it is stored). Defence in depth is
deliberate: nothing below assumes their half landed, and nothing below is
weakened if it did.

Source: `REFUTATION-5-safety.md`, findings S1 (HIGH, PUSH-BLOCKER, data
destruction), S4 (HIGH, silent) and S6 (LOW, loud), plus the brief's third
item (make the refusals at that boundary total). Method: fail first, capture
the failure, fix, re-run the class; then attack the fix and repeat.

---

## 0. READ THIS FIRST: what is closed, and the one gap that is not mine

**S1, S4 and S6 are closed on the DECLARATION side, at the one place a
unit's scope enters the store.** Every spelling in the refutation refuses by
name, with the entry, the unit and the remedy in the sentence, and nothing
is written when it does.

**Two further findings came out of attacking this round's own fix**, and
both are closed in the same round: a refused spelling could be re-spelled
past the gate (`./:!keep.txt` was stored as `:!keep.txt`), and the first
patch for that was itself too narrow (a 2954-spelling property sweep found
two more families). Both are reproduced in `RED-round6-store.txt` under
"SECOND RED".

**The one gap, stated first because it is the one a reader could mistake for
closed.** S4 has two halves. The `write_scope` half is closed end to end:
that field reaches the store untouched by the engine, so a bare string is
refused before anything is stored. The `read_scope` half is closed for a
DIRECT store caller only. The engine canonicalises a read scope BEFORE it
calls the store, and a bare string iterated there arrives as a list of
one-character strings that the store's container check cannot distinguish
from a genuine declaration. Closing that is the controller half's item, in
this same round, by design. It is disclosed in `KNOWN-LIMITS.md`.

---

## 1. Per-finding table

| Finding | Verdict | What closes it | Pinned by |
|---|---|---|---|
| **S1** (HIGH, PUSH-BLOCKER) a git PATHSPEC in `write_scope` makes the engine's rollback restore the whole tree | **CLOSED at declaration** | `literal_scope_entry` refuses any entry whose stripped form begins with `:`, reason `pathspec-write-scope`; plus absolute (`absolute-write-scope`) and empty (`empty-write-scope`) | `TestWriteScopeEntriesAreNotGitPathspecs` (12 tests) |
| **S1**, the re-spelling half (found here, not in the refutation) | **CLOSED** | the gate looks TWICE: the same rules are re-asked of the RESOLVED string, because `.` and `..` collapse | `test_a_pathspec_cannot_be_re_spelled_through_a_relative_prefix`, `test_no_generated_spelling_is_stored_as_a_path_the_rule_refuses` |
| **S4** (HIGH, silent) a bare JSON string scope is iterated character by character | **CLOSED for `write_scope`**; **closed for `read_scope` only against a direct store caller** | `declared_scope_list` validates the CONTAINER before anything is iterated, reason `bad-scope-container` | `TestScopeContainersAreValidatedBeforeIteration` (7 tests) |
| **S6** (LOW, loud) `"write_scope": 7` is an uncaught `TypeError` out of the shipped `plan` | **CLOSED** | same container gate; the refusal names the actual type | `test_every_non_list_container_refuses_naming_its_type` |
| **Brief item 3**: every exception from path handling at that boundary becomes a named refusal | **CLOSED** | `canonical_write_scope_entry` catches everything the resolver can raise, reason `unreadable-scope-path`; an existing named refusal (`path-escape`) passes through unchanged | `TestScopePathHandlingRefusesTotally` (4 tests) |
| S2, S3, S5, S7 | **NOT MINE** | controller-side findings, or disclosure items; untouched by this writer | n/a |

Nothing in `CONTROLLER_STATE_TRANSITIONS` or `AUTONOMY_FLOORS` was widened.
The glob ALLOWANCE rule (a contract's `allowed_paths` may still be a
pattern) is untouched: that is a recorded founder decision and was out of
scope.

---

## 2. The refused-spelling enumeration

Every row below was accepted by the round-5 gate and is refused now. The
"what git does" column is from `REFUTATION-5-safety.md`'s measured probe
table against the system git (every magic row exited 0, so the engine read
its own rollback as a SUCCESS and queued no dirty-write-scope warning), not
from reading documentation.

### 2.1 Git pathspec magic, reason `pathspec-write-scope`

| Spelling | What git does with it in `git restore -- <entry>` | Why it is dangerous here |
|---|---|---|
| `:` | restores the whole repository | this is what `:/` CANONICALISES TO, so it is the string the store actually held |
| `:/` | restores the whole repository, exit 0 | reproduction 2 of S1: every uncommitted file in the project gone, founder told only "dispatch rejected" |
| `:(top)`, `:(top)src` | same, long form | a second spelling of the same damage |
| `:!x` | restores everything EXCEPT x | reproduction 1 of S1: the founder reading `write_scope: [":!keep.txt"]` sees ONE file named, and one file is the only thing that survives |
| `:^x` | same as `:!x` | the `^` spelling |
| `:(exclude)x` | same as `:!x` | the long spelling |
| `:(icase)X` | matches a name the entry does not spell | the fence, the coverage check and the rollback all disagree with the text a founder reviewed |
| `:(literal)x` | matches x literally | still MAGIC: the PREFIX has to go, not only the spellings that look dangerous |
| `:(glob)x` | glob magic, no metacharacter in the string | invisible to the round-5 glob rule, which only reads `*`, `?` and `[` |
| `:(attr:binary)` | names a SET of files by attribute | there is no path in it at all |
| `::` | empty magic plus an empty path | |
| ` :/` (leading space) | as `:/` | `_to_posix` strips first, so this is the same spelling, not a second one |

The rule is a PREFIX test on the stripped string, not a list: a colon is the
only thing that introduces magic in git's pathspec language
(`gitglossary(7)`), so one comparison covers every spelling git has now and
every spelling it grows later.

**Deliberately still accepted:** a colon anywhere other than the start.
`src/a:b.py` is an ordinary filename and is pinned as a control.

### 2.2 Absolute paths, reason `absolute-write-scope`

`/`, `/etc/passwd`, `//srv/share`, `\\srv\share`, `C:/Windows`,
`C:\Windows`, `c:`, and any `os.path.isabs`. Both separator forms and the
drive-qualified form are refused on EVERY platform, not only the one the
process runs on: a plan file is data, and it can be authored on one platform
and executed on another.

The quiet half of this one: an absolute path that happened to resolve INSIDE
the root was accepted before, and silently rewritten to its relative form,
so the plan the founder wrote and the plan the store held were different
strings.

### 2.3 Empty and whitespace-only, reason `empty-write-scope`

`""`, `" "`, `"\t"`, `"\n"`, `"   \t  "`. Before this round these reached
the resolver and raised a bare `ValueError('empty path')`: no reason code,
no unit id, no remedy, out of a method whose whole contract is that it
validates a plan before writing any of it.

### 2.4 The SECOND LOOK, at the resolved string

The three rules above read what the caller DECLARED, which is right: the
refusal has to quote the founder's own spelling back. But `canonicalize_path`
collapses `.` and `..` segments and strips the string as a whole, so a
refused declaration can be re-spelled as an accepted one. A property sweep
over 2954 generated spellings found three families, none of them predictable
from reading the resolver:

| Declared | Stored before the second look | Family |
|---|---|---|
| `./:!keep.txt`, `a/../:!keep.txt` | `:!keep.txt` | pathspec (the tree-destroying one) |
| `./:/`, `sub/../:` | `:` | pathspec (whole repository) |
| `./a:b`, `.//C:` | `a:b`, `C:` | absolute (drive-qualified to a Windows caller) |
| `./ /`, `./ /.` | `" "` | empty (`_to_posix` strips the WHOLE string, not each segment) |

A symlink inside the project pointing at a directory whose name begins with
a colon is the same family reached without any `..` at all, and is refused
by the same check (probed, `link` -> `:!keep` -> refused).

The sweep is now a permanent test, and it asserts the PROPERTY rather than
the list: whatever the gate accepts must be a string the gate would also
accept if it had been declared that way. It runs 2954 spellings in the
suite; a wider 20439-spelling version (adding a fullwidth colon, a
zero-width space, `%2A`, tabs, backslash forms and a symlink) was run as a
probe and reports 6581 accepted, 0 violations.

---

## 3. The container rule, and exactly where the None rule bites

A scope is a LIST or a TUPLE of path strings, checked BEFORE anything is
iterated. Refusals name the field, the actual type and what the old
behaviour would have done:

| Declared | Reason | Type named |
|---|---|---|
| `"a.py"` | `bad-scope-container` | `str`, with the explosion spelled out: one scope per character, and `.` is the whole project |
| `7`, `7.5`, `True` | `bad-scope-container` | `int`, `float`, `bool`, "not iterable at all, which reached the shipped plan command as an uncaught TypeError" |
| `None` (key PRESENT) | `bad-scope-container` | `NoneType` |
| `{}`, `{"p": "a.py"}` | `bad-scope-container` | `dict`, "iterating it yields its KEYS" |
| `b"a.py"` | `bad-scope-container` | `bytes`, "yields integers, not paths" |
| `{"a.py"}` | `bad-scope-container` | `set`, "no order, so the same declaration hashes and reads differently" |
| a generator | `bad-scope-container` | `generator` (readable once is not a declaration) |
| `[5]`, `[["a"]]`, `[{"p":1}]`, `[None]` | `bad-path` (unchanged, round-3 vocabulary) | the entry's type |

**Where the None rule bites, and where it does not.** An ABSENT
`write_scope` or `read_scope` key is not a declaration: it still means "no
scope", and a unit that omits it hashes EXACTLY as it did before this round
(asserted by a test that re-upserts the same unit and compares
`definition_hash`), so no persisted unit is silently redefined by the
upgrade. A key that is PRESENT and null IS a declaration, of the wrong type,
and refuses. This is the one behaviour change a plan file can see, and it is
in `KNOWN-LIMITS.md`.

**What `read_scope` does and does not get.** It gets the container rule and
the total path coercion (`bad-path` naming the entry type). It does NOT get
the literal-path, pathspec, absolute or empty rules, and it is not
canonicalised by the store. That is deliberate: a read scope never reaches
`git restore --`, the engine canonicalises it separately, and a
founder-authored pattern over files to READ is a reasonable thing to write.
Disclosed in `KNOWN-LIMITS.md`.

---

## 4. SIGNATURES: build on these, not on this report's prose

### 4.1 Two new PUBLIC module-level functions

```python
def canonical_write_scope_entry(root, f, unit_id=None, cwd=None):
    """the WHOLE write-scope boundary: declaration rules, canonicalisation,
    and the second look at the resolved string."""
    # returns str (the canonical root-relative path that will be stored),
    # or raises OwnershipRefused with one of:
    #   'bad-path'              (from _coerce_path_entry, unchanged)
    #   'empty-write-scope'     NEW
    #   'pathspec-write-scope'  NEW
    #   'absolute-write-scope'  NEW
    #   'glob-write-scope'      (round 5, unchanged)
    #   'path-escape'           (from canonicalize_path, passed through
    #                            UNCHANGED, reason and details intact)
    #   'unreadable-scope-path' NEW: any other exception from path handling
    # details always carry {"entry", "unit_id"}; the second look adds
    # {"resolved"}; the total catch adds {"error_type"}

def declared_scope_list(value, field, unit_id=None):
    """the CONTAINER gate for a declared scope."""
    # returns list, or raises OwnershipRefused 'bad-scope-container'
    # details: {"field", "type", "unit_id", "entry"}  (entry is _safe_repr'd)
```

Both are public for the same reason `literal_scope_entry` is: any future
caller that stores what a worker will WRITE should share these rather than
grow a second copy. `Store.claim`'s own `files` argument still deliberately
does NOT go through them.

### 4.2 One private helper added

```python
def _is_absolute_scope(p):   # NEW, private: absolute on ANY platform
_PATHSPEC_MAGIC_PREFIX = ":" # NEW, private constant
_SCOPE_CONTAINER_TYPES = (list, tuple)  # NEW, private constant
```

### 4.3 `literal_scope_entry`: signature UNCHANGED, refusals ADDED

```python
def literal_scope_entry(f, unit_id=None):   # same signature, same return
```

It still returns the declared string or raises. It now raises three more
reasons before the glob check: `empty-write-scope`, `pathspec-write-scope`,
`absolute-write-scope` (in that order, then `glob-write-scope`). Callers
that only catch `OwnershipRefused` see no change in kind.

### 4.4 New refusal reasons

`empty-write-scope`, `pathspec-write-scope`, `absolute-write-scope`,
`unreadable-scope-path`, `bad-scope-container`. All five are new members of
the store's kebab-case refusal vocabulary; none widens an enumerated
constant, and all five are literal codes at the call site, as
`TestLearningApi::test_structural_every_ownership_refusal_names_a_reason_code`
requires.

### 4.5 Return shapes: NONE moved

`upsert_units` still returns `{'count', 'skipped', 'cancelled_dispatches',
'orphaned_fences'}`. Stored `write_scope` values are the same canonical
strings for every entry that was legal before. Stored `read_scope` values
are now the coerced list (identical for the normal case of a list of
strings; a `pathlib.Path` in there used to be an uncaught `TypeError` out of
`json.dumps` and is now stored as its string form).

### 4.6 Behaviour changes an existing caller can see

1. A `write_scope` entry beginning with `:`, an absolute entry, or an
   empty/whitespace entry now refuses where it was accepted. Nothing in
   `tools/`, `docs/`, `references/`, `project-template/`, `commands/`,
   `skills/` or `brotherme/` declares one (grepped for a `write_scope`
   entry beginning with `:` or `/`: the only hits in the tree are this
   round's own test, `REFUTATION-5-safety.md`'s reproductions, and this
   report).
2. An entry that RESOLVES to one of those refuses too, naming both forms.
3. A `write_scope` or `read_scope` that is not a list or tuple refuses.
   An explicitly null one refuses; an absent one does not.
4. An absolute entry that used to be silently rewritten relative now
   refuses instead of being rewritten.

---

## 5. RED first: the evidence

`docs/program/absolute-lead/evidence/L03/RED-round6-store.txt`, 410 lines,
holds the verbatim pre-fix output of all three classes plus the two
second-round findings. Per-class counts at capture time:

```
TestWriteScopeEntriesAreNotGitPathspecs           9 tests, 6 failures, 1 error, 2 ok
TestScopeContainersAreValidatedBeforeIteration    7 tests, 4 failures, 1 error, 2 ok
TestScopePathHandlingRefusesTotally               4 tests, 1 failure,  3 errors, 0 ok
```

The four green-before tests are CONTROLS and are named in the RED file with
what each one controls for. One error was my own test's bug (a failure
message formatted with `%r` over a sweep that includes the object whose
`__repr__` raises); it is named there rather than quietly corrected, and the
correction was to use the store's own `_safe_repr`.

**One existing test collided with the first shape of the fix, and was
obeyed rather than edited.**
`TestLearningApi::test_structural_every_ownership_refusal_names_a_reason_code`
requires every `OwnershipRefused` call to name a LITERAL kebab reason as its
first argument. The second look's first draft forwarded the underlying
reason from a variable, and the guard caught it:

```
FAIL: test_structural_every_ownership_refusal_names_a_reason_code
AssertionError: Lists differ: [(1013, 'first argument is not a literal
reason code')] != []
: OwnershipRefused(reason, message) violated at: [(1013, 'first argument is
not a literal reason code')]
```

Remedy applied: one literal-coded refusal per family, with an explicit
fallback to `unreadable-scope-path` for a family added to
`literal_scope_entry` later. No test was edited.

---

## 6. Done-check, run after the last edit

```
$ python3 tools/test_bm_store.py
----------------------------------------------------------------------
Ran 878 tests in 25.914s

OK
STORE EXIT: 0

$ python3 tools/test_bm_autonomy.py
----------------------------------------------------------------------
Ran 58 tests in 22.491s

OK
AUTONOMY EXIT: 0
```

Baseline before any edit, for the record: `test_bm_store.py` ran 855 tests
OK; `test_bm_autonomy.py` exit 0. The 23 new tests are the whole difference.

Targeted run over the new classes, from `tools/`:

```
$ python3 -m unittest test_bm_store.TestWriteScopeEntriesAreNotGitPathspecs
Ran 12 tests in 0.156s   OK
$ python3 -m unittest test_bm_store.TestScopeContainersAreValidatedBeforeIteration
Ran 7 tests in 0.073s    OK
$ python3 -m unittest test_bm_store.TestScopePathHandlingRefusesTotally
Ran 4 tests in 0.018s    OK
$ python3 -m unittest <all three together>
Ran 23 tests in 0.234s   OK
```

`tools/test_all.py` and the controller suite were NOT run, per the brief.

---

## 7. Blocked, not done, and what I did not check

**Nothing in this round's brief is blocked.** The one collision found (the
structural reason-code guard) was resolved by obeying the test, and is
recorded verbatim in section 5.

Stated plainly, in descending order of how much it matters:

* **A bare-string `read_scope` can still be exploded by the CALLER before
  the store sees it.** The engine canonicalises a read scope before calling
  the store, iterating it there; a bare string arrives as a list of
  one-character strings the store's container check cannot distinguish from
  a real declaration. This is the controller half's item in the same round.
  Disclosed in `KNOWN-LIMITS.md`.
* **I did not drive the shipped CLI.** Every result here is at the store
  boundary, through `Store.upsert_units` or the module-level gates.
  `tools/bm_controller.py` was being edited in parallel by the other writer
  while I worked, so running `bm-controller plan` would have measured their
  in-flight file, not mine. The refutation's own CLI reproductions reach the
  store through `upsert_units`, which is the single writer of a unit's
  `write_scope` (confirmed: the only two SQL statements that write that
  column are both inside that method).
* **`expected_artifacts` has no container check at all**, and I found that
  while I was in there: a bare string is stored as a bare string, a number
  as a number. It is not a path any of the three readers touch, so the S1
  and S4 damage does not follow, but it is the same shape and out of this
  round's brief. `dependencies` has the same gap and fails LOUDLY instead (a
  bare string becomes one dependency per character and refuses
  `dangling-dependency`, reproduced). Both are disclosed.
* **A NUL byte in a path is still accepted**, unchanged from the round-5
  disclosure. `os.path.realpath` on darwin swallows it rather than raising,
  so it is not even reached by the new total catch. That remains a separate
  policy decision about path bytes, not taken here either.
* **`.` is still a legal write scope**, which grants and fences the whole
  project. It is pinned as accepted by a round-5 test (an existing test is
  law) and is the same disclosure as a unit with no write scope.
* **`bm_fence_hook.py` was not touched or run.** S1's "smallest fix" note
  suggests re-checking the fence claim and the hook's covering check for the
  same family. The store now refuses the family before it can reach either,
  but I make no claim about a fence claimed by some other route.
* **A caller that passes a hostile MAPPING rather than a dict is out of the
  model.** `upsert_units` validates `u`, writes the validated scope back
  into it, and reads it again when it writes the row; a mapping whose values
  change between those reads could disagree with what was validated. That is
  true of every field, not only these two, and no shipped caller is such a
  mapping.
* **Windows and Linux were not exercised.** Everything ran on darwin with
  Python 3.9.6. The absolute-path rule is written to be platform independent
  precisely because a plan file can cross platforms, but its Windows
  behaviour is reasoned, not observed.
* **Unicode lookalikes are NO-DATA**, as in round 5: a fullwidth colon is
  accepted, and it is not magic to git any more than a fullwidth star is a
  glob. It appears in the 20439-spelling probe sweep with no violation.
