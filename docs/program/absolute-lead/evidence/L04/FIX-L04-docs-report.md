# FIX L04, WRITER C: the register and the disclosure

Writer: Writer C of DESIGN-L04.md section 19, the register and disclosure half.
Sections owned: 8.6, 13, 15.3, 16, 17.4's docs half, 18.3, 18.6.

Files written, and only these:

* `references/terminology.md`
* `references/status-view.md`
* `commands/brotherme-brief.md` (new)
* `commands/brotherme-decisions.md` (new)
* `commands/brotherme-handback.md` (new)
* `commands/brotherme-handover-pack.md` (new)
* `commands/brotherme-status.md`
* `commands/brotherme-next.md`
* `commands/brotherme-start.md`
* `commands/brotherme-help.md`
* `SECURITY.md`
* `docs/KNOWN-LIMITS.md`
* `docs/AUTONOMY.md`
* `docs/program/absolute-lead/evidence/L04/RED-L04-docs.txt`
* this report

Files in this writer's allowed set that were **NOT written**, all for the same
reason and it is stated once here: `capabilities.status.json`, `README.md`,
`docs/ROADMAP.md` and `tools/test_bm_docs.py`. All four wait on gate 2 of
section 19, which is not a scheduling preference but a test: four of the six
capability rows name `tools/bm_lead.py` and `tools/test_bm_lead.py` as evidence,
and `tools/test_bm_docs.py:3566` to `3574` refuses an evidence pointer naming a
path that is not in the tree. Neither file existed at any point during this
writer's work. Section 3 below has the verbatim refusal, the drafted rows, and
the exact landing sequence for whoever finishes it.

No file outside the list was touched. `tools/bm_store.py`, `hooks/hooks.json`,
`pyproject.toml`, `.github/workflows/tests.yml` and every test suite belong to
Writers A and B; each was read, none was written. `tools/bm_lead.py` and
`tools/test_bm_lead.py` could not even be read, which is the whole of section 3.

---

## 0. The two things a reader has to know first

Bad news first, per `references/honesty.md`.

### 0.1 The done-check cannot pass, and the cause is other people's untracked pages

`python3 tools/test_bm_docs.py` was RED on the untouched tree, before this
writer changed anything, and it is red for one reason that no writer in section
19 may fix:

    AssertionError: Lists differ: ['docs/program/absolute-lead/DESIGN-L04.md:6 BrotherModeUp'] != []

`docs/program/absolute-lead/DESIGN-L04.md` line 6 reads
`Target tree: /Users/khalil.maaouni/Documents/BrotherModeUp` as bare prose.
`current_pages()` in `tools/test_bm_docs.py:4471` treats every page under `docs/`
that is neither dated nor inside a record directory as a current page, and the
only record directory under `docs/program/absolute-lead` is its `evidence`
folder (`RECORD_DIRS`, 4405 to 4410). So the design document is read as a page a
reader lands on, and the naming rule ratified on 2026-08-04 fires on the
repository slug in prose.

By the end of this writer's work the same test named SEVEN offenders across
THREE untracked files: the design document, plus six lines in two research pages
under `docs/program/absolute-lead/research/`, a directory that did not exist when
this writer started. Section 4.1 has that run verbatim. Nothing in the growth is
this writer's, and the remedy is the same in all three files.

REMEDY, one character pair, for whoever owns the design document: wrap the path
in backticks. `prose_only()` (4458) blanks inline code spans, which is the
allowance documented at 4436 to 4444 for exactly this case, a path a machine
takes rather than a name a reader is taught. Alternatives, both worse: adding
the design to `NAMING_EXCLUSIONS` (empty since 2026-08-04 on purpose, 4412 to
4428), or moving the design under the evidence directory (it is a design, not
evidence).

This writer did not touch `DESIGN-L04.md`: it is in no writer's allowed set,
and weakening the test that catches it was ruled out by the brief.

### 0.2 A seventh existing test collides, and it was reported rather than edited

`tools/test_bm.py:5680` `test_exactly_seven_brotherme_commands_ship` pins the
shipped command set by exact equality over `commands/brotherme-*.md`. The four
new command files that DESIGN-L04.md section 15.3 requires turn it red the
moment they exist. Verbatim failure and the proposed remedy are in
`RED-L04-docs.txt`, BLOCK 2.

Why the files were landed anyway rather than withheld: the pin is doing its
designed function, the same shape as the two migrations the design already
predicts (18.1's purge dict, 18.2's consent inventory), and its own comment
records that L03 extended it once already for the three Full-Auto commands. The
remedy is four names added to the pinned list, which keeps the assertion at
exact equality over the whole set and loosens nothing. It was NOT applied here
because `tools/test_bm.py` is outside every writer's allowed set and section
18.8 instructs a writer who finds an unpredicted collision to stop and report.

Nothing else in that class broke: the other seven tests pass, including the five
store-backed command pins (`brotherme-status.md` keeps
`python3 tools/bm_project.py status`, `brotherme-next.md` keeps
`python3 tools/bm_project.py next`, `brotherme-start.md` keeps
`python3 tools/bm_project.py start`) and the deep-tour pin in
`brotherme-help.md`.

---

## 1. Per-section table

| Section | What it asks for | State | Evidence or reason |
|---|---|---|---|
| 8.6, SECURITY.md half | the gated set gains `bm_lead.py watchdog`, plus one disclosure of what a tick does, what it writes when due, and that it writes nothing when not | LANDED | `SECURITY.md`, the consent-config asset entry. `python3 tools/test_bm.py TestProjectSecurityClaims` green (line-count claim and no-network claim) |
| 8.6, KNOWN-LIMITS half | a new dated L04 section in the format of the existing entries | LANDED | `docs/KNOWN-LIMITS.md`, `## L04: what founder mode, the ledger and the watchdog do NOT do (2026-08-05)` |
| 13.1 | six register rows | BLOCKED, gate 2 | drafted and validated below; four rows name Writer B's two files |
| 13.2 | both generated blocks regenerated by bm-docs | BLOCKED, gate 2 | the regeneration is the same step as the register edit (18.3) |
| 13.3 item 1 | `docs/AUTONOMY.md:11`, the "U2, not yet built" sentence | LANDED | one sentence, now naming `tools/bm_controller.py` and `docs/FULL-AUTO.md` |
| 13.3 item 2 | README's capability table gains the rows by construction, no hand edit | BLOCKED, gate 2 | follows 13.2, and no README prose was edited |
| 15.3, four new command files | brief, decisions, handback, handover-pack | LANDED, with the collision in 0.2 | four files, each naming its mechanical command |
| 15.3, four changed command files | status, next, start, help | LANDED | status and next read `bm-lead status`, start records the outcome first, help's list is nine and names the two the coordinator runs |
| 15.3, `references/terminology.md` | eight new rows before the terms may appear | LANDED | appended after "triage", so lines 1 to 25 are byte-identical and the design's own citation of rows 10 to 25 still resolves |
| 15.3, `references/status-view.md` | one short IC mode section | LANDED | appended after line 54, so the cited line ranges 8 to 16, 26 to 27, 43 to 51 and 53 are unmoved |
| 16 | the five deferrals disclosed in the same words | LANDED | all five are bullets of the L04 section, plus two more (handback does not cancel work in flight, and the beta-not-certified reading) |
| 17.4 docs half | the capability classes need no change; TestNoDashes changes | PARTLY | the three no-change classes are green as they stand (section 4); the TestNoDashes edit is 18.6 and is blocked |
| 18.3 | no assertion changes in the capability classes | HELD | nothing in `tools/test_bm_docs.py` was edited at all |
| 18.6 | TestNoDashes target list gains the two `bm_lead` files | BLOCKED, gate 2 | `read()` on a missing path raises, so adding them now turns a green test into an ERROR |

---

## 2. What landed, in detail

### 2.1 The disclosure, both halves (8.6)

`SECURITY.md`. The consent-config asset entry already enumerated the gated set
and already carried the incident that made the enumeration necessary. It now
reads `..., all three hook-wired bm_telemetry.py commands (outcomes-append,
precompact-brief, stop-warn), and bm_lead.py watchdog`, and the sentence about
the test that reads `hooks/hooks.json` now records that since 2026-08-05 it
reads every module named on a hook line rather than `bm_telemetry.py` alone,
which is Writer B's widening in 18.2. A new block, opening `THE WATCHDOG, added
2026-08-05 and disclosed here because it ships ON BY DEFAULT`, states: that it
is a due check rather than a background process; that it runs on the Stop hook,
once per model turn, on the same line as the telemetry warning; that its first
statement reads the consent record, so before setup it prints nothing and writes
nothing at all; that after consent, when a catch-up is not due, which is the
ordinary case, it still writes nothing and prints nothing; that when one is due
it writes exactly one row into the project's own store and prints the catch-up;
and that it writes nothing into the vault, nothing outside the project, and
makes no network call.

Both halves of the founder decision are in that text: ON BY DEFAULT, and active
only after the consent gate.

`docs/KNOWN-LIMITS.md`. One new dated section in the format of the existing
entries, carrying, in this order: the Stop-hook limit (16.2) with the trade a
later loop would have to measure and `/brotherme-brief` as the manual path; the
chosen-not-measured activity ceiling (16.4) in the words the design asks for;
the ledger-versus-records law (L1) including its cost, that a wrong entry sits
visibly until something supersedes it; the deferred controller event table
(16.1 and 14) with the replay test named and both of its verdicts spelled out;
the ungated store and project command lines (16.3 and 8.5); that a handback does
not cancel work already in flight (9.6); that the pack covers one project
(16.5); and that all six new register rows are beta with the gap named.

### 2.2 The command surface (15.3)

Four new files, each in the house shape (frontmatter with a description, an
"Outcome to produce" line, the mechanical command named literally, the
install-path paragraph copied from the shipped files, and an honesty rule):

* `commands/brotherme-decisions.md` renders each card through
  `references/kickoff.md`, states that the last option is always the user's own
  and that it cannot be omitted because a decision that omits it cannot be
  recorded, and carries the two honesty rules (a reasoned claim says so; a
  preference decision says it was declared rather than detected).
* `commands/brotherme-handback.md` explains the five acts in plain language and
  in their fixed order, says why the order is the safety property, states that
  nothing is deleted and the choice not taken is kept, and instructs the error
  card plus "do not un-pause to tidy a failure" on the failure path.
* `commands/brotherme-brief.md` carries the quiet-stretch behaviour of 7.5 in
  full: no new row, name the one that still stands with its age, the standing
  next step, the options line, and the never-had-one case.
* `commands/brotherme-handover-pack.md` names all seven pages with one line
  each, names the audience, and states the two properties (regenerating changes
  nothing unless the records changed; the pack covers one project).

Four changed files: `brotherme-status.md` now runs `bm-lead status` and reads
the eight computed fields out instead of instructing the model to TRANSLATE a
different command's report into them, with `bm_project.py status --history N`
moved into the advanced paragraph; `brotherme-next.md` takes the recommendation
from the Next step field and keeps `bm_project.py next` as the machinery view;
`brotherme-start.md` records the outcome with `bm-lead outcome --set` before the
guided kickoff continues; `brotherme-help.md`'s list is now nine items and names
`/brotherme-brief` and `/brotherme-handover-pack` as the two the coordinator
normally runs. The count word and the list agree.

### 2.3 The two reference files (15.3)

`references/terminology.md` gains eight rows: insight ledger, evidence class,
briefing, handback, active minutes, watchdog, handover pack, trace tag. They
were APPENDED after "triage" rather than interleaved, which matters
mechanically: the design cites `references/terminology.md:10 to 25` as the row
range the plain-language fixture reads (sections 12 S1 and 17.1), and appending
leaves lines 1 to 25 byte-identical. Two rows carry an allowance clause in the
same style the shipped token row already uses, because the alternative would be
a rule the product breaks on its own command names: `briefing` allows the
command name `/brotherme-brief` while binding the catch-up's own text to the
plain wording, and `watchdog` allows the word on the two pages that have to
disclose it while banning it from a status line.

`references/status-view.md` gains one "IC mode" section, appended after line 54
so every line range the design cites is unmoved. It states the three things 4.3
asks for: IC mode is explicit, through the `--ic` flag or `BROTHERMODE_VIEW=ic`;
every IC render names the switch that turned it on and how to turn it off,
which is what keeps a sticky switch from breaking the page's own
never-sticky-by-assumption rule; and the default view is unchanged, with `--ic`
and `--advanced` independent in both directions.

---

## 3. The six capability rows, drafted and blocked at gate 2

The rows below are the deliverable of section 13.1. They are quoted here as
DRAFTED, not as landed, because `capabilities.status.json` was not written.

### 3.1 Why they did not land

Run against this tree with the six rows appended, the shipped guard refuses:

    decision-record-and-briefing: evidence names tools/bm_lead.py, which is not in the tree
    decision-record-and-briefing: evidence names tools/test_bm_lead.py, which is not in the tree
    handing-control-back: evidence names tools/bm_lead.py, which is not in the tree
    handing-control-back: evidence names tools/test_bm_lead.py, which is not in the tree
    analyst-handover-pack: evidence names tools/bm_lead.py, which is not in the tree
    analyst-handover-pack: evidence names tools/test_bm_lead.py, which is not in the tree

That is `capability_offenders` in `tools/test_bm_docs.py:3539`, the predicate
behind `test_every_entry_carries_a_valid_state_and_real_evidence` (3692). The
three rows naming only files that exist today draw no offender, which is what
proves the check is reading the paths rather than agreeing with the file.

The rows were not weakened to name a path that exists, and no test was edited.

### 3.2 The rows

```json
    {
      "id": "autonomy-contract",
      "title": "The signed authorisation an autonomous session has to work inside",
      "state": "beta",
      "evidence": "tools/bm_autonomy.py is the command line, tools/test_bm_autonomy.py is its suite, and the store job in .github/workflows/tests.yml runs that suite on Linux, macOS and Windows; docs/AUTONOMY.md is the page. It stays beta because docs/KNOWN-LIMITS.md records open items against this layer and no use outside this project is recorded."
    },
    {
      "id": "full-auto-controller",
      "title": "The durable controller that carries a signed outcome to a checked deliverable",
      "state": "beta",
      "evidence": "tools/bm_controller.py is the engine and its command line, tools/test_bm_controller.py is its suite including an end to end run that is killed and resumed (its transcript is docs/program/absolute-lead/evidence/L03/E4-endtoend.json), the store job in .github/workflows/tests.yml runs that suite on Linux, macOS and Windows, and docs/FULL-AUTO.md is the page. Not experimental, because experimental here means not measured and this is measured. It stays beta because docs/KNOWN-LIMITS.md carries its own list of what the controller does not yet do, and no pilot outside this project exists."
    },
    {
      "id": "decision-record-and-briefing",
      "title": "A record of what was decided and why, and the short catch-up built from it",
      "state": "beta",
      "evidence": "tools/bm_lead.py records and renders them over two append only tables in tools/bm_store.py, tools/test_bm_lead.py is its suite, and docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md states what a record has to carry before it may be written. It stays beta because the record holds the coordinator's judgement rather than a measurement, because no continuous integration run covers it yet, and because docs/KNOWN-LIMITS.md names what it does not do."
    },
    {
      "id": "handing-control-back",
      "title": "Handing a decision and the work under it back to the person who owns it",
      "state": "beta",
      "evidence": "Offered on every key decision and enforced by a refusal in tools/bm_store.py rather than by a rendering convention: a key decision that offers no handback cannot be recorded at all. tools/bm_lead.py performs the handback and writes the page a developer picks the work up from, and tools/test_bm_lead.py drives both, including the refusal of a second handback on one decision. It stays beta because no continuous integration run covers it yet and no handback outside this project is recorded."
    },
    {
      "id": "half-hour-watchdog",
      "title": "A half hour catch-up that arrives on its own, on by default after setup",
      "state": "beta",
      "evidence": "hooks/hooks.json wires it to the Stop hook as a due check rather than a background process, tools/test_bm_consent.py drives every hook wired command against a fresh home directory and fails if any of them writes before consent (the suite job in .github/workflows/tests.yml runs that suite), and SECURITY.md discloses that it ships on by default, what it writes when a catch-up is due, and that it writes nothing when it is not. It stays beta because it cannot fire inside a turn that never ends and because its activity ceiling is a chosen constant, both recorded in docs/KNOWN-LIMITS.md."
    },
    {
      "id": "analyst-handover-pack",
      "title": "Handover pages an analyst or a project lead can take a project over from",
      "state": "beta",
      "evidence": "tools/bm_lead.py generates them from rows and tools/test_bm_lead.py checks both directions: every row the store says belongs on a page reaches that page, and every claim on a page resolves back to the row it came from. It stays beta because no continuous integration run covers it yet and because nobody outside this project has read a pack, which is the empty rung docs/ROADMAP.md section 1 describes."
    }
```

`updated` moves to `2026-08-05` in the same edit.

### 3.3 One deviation from the design's evidence list, stated as a deviation

DESIGN-L04.md 13.1 lists the evidence pointers for each row and none of them
names `.github/workflows/tests.yml`. Three of the drafted rows name it anyway,
and the reason is that omitting it would print a FALSE sentence on a generated
page rather than a modest one.

`tools/bm_docs.py roadmap_proof_state` (1542) maps a beta row to `verified in
CI` when its evidence names a job under `.github/workflows`, and to `verified
locally` otherwise, and `docs/ROADMAP.md` section 1 defines `verified locally`
as "the evidence names a file or a test in this tree, and NO continuous
integration job covers it yet". For the autonomy contract and the controller
that denial is untrue: `.github/workflows/tests.yml` lines 213 to 221 run
`tools/test_bm_autonomy.py` and `tools/test_bm_controller.py` in the `store`
job, on ubuntu, macos and windows, at Python 3.9 and 3.x. For the watchdog, the
test that proves the gate is `tools/test_bm_consent.py`, which the `suite` job
runs at lines 113 to 114, and that test is UNCHANGED by L04: it already drives
every command string in `hooks/hooks.json`, so naming the watchdog in that file
brings it inside a check that already runs off this machine.

The three rows that depend on `tools/test_bm_lead.py` deliberately do NOT name
the workflow, even though Writer B's own deliverable adds a CI step for that
suite. A step that exists and has never executed does not yet prove "the check
runs somewhere other than the author's own machine", which is what the rung
says. Those three read `verified locally`, and that is exactly true today.

Verified by running the shipped mapping over the drafted rows:

    autonomy-contract -> verified in CI
    full-auto-controller -> verified in CI
    decision-record-and-briefing -> verified locally
    handing-control-back -> verified locally
    half-hour-watchdog -> verified in CI
    analyst-handover-pack -> verified locally

If the orchestrator prefers the design's list read strictly, deleting the
clause naming `.github/workflows/tests.yml` from the first two rows and the
parenthesis from the fifth is the whole change, and the three rows drop to
`verified locally`. The cost of that choice is the false denial above, on a
page whose entire purpose is that a reader does not have to take a claim on
trust.

### 3.4 The landing sequence for whoever finishes it

1. Confirm `tools/bm_lead.py` and `tools/test_bm_lead.py` are in the tree.
2. Append the six rows of 3.2 to `capabilities.status.json` and move `updated`
   to the landing date.
3. Expect `TestGeneratedCapabilityStatusBlock` and
   `TestGeneratedRoadmapStatusBlock` to be RED at this point. That red is the
   guards working (18.3), and it must not leave the step.
4. `python3 tools/bm_docs.py capability-status --write` and
   `python3 tools/bm_docs.py roadmap-status --write`. Do not hand edit either
   block.
5. Add `tools/bm_lead.py` and `tools/test_bm_lead.py` to the `TestNoDashes`
   target list at `tools/test_bm_docs.py:4759` to `4763` (18.6).
6. `python3 tools/test_bm_docs.py`. The only failure left should be the one in
   section 0.1, and that one is not fixable from inside this writer's set.

---

## 4. Verification

Every command below was run in
`/Users/khalil.maaouni/Documents/BrotherModeUp` after the last edit in the
section it verifies.

### 4.1 The done-check: `python3 tools/test_bm_docs.py`

NOT DONE. It exits 1, and every failing assertion belongs to the one test named
in section 0.1. Verbatim tail:

    FAIL: test_no_current_page_uses_a_retired_name_as_the_product_name (__main__.TestCurrentPagesUseTheCanonicalNames)
    ----------------------------------------------------------------------
    Traceback (most recent call last):
      File "/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py", line 4531, in test_no_current_page_uses_a_retired_name_as_the_product_name
        self.assertEqual(

    First list contains 7 additional elements.
    First extra element 0:
    'docs/program/absolute-lead/DESIGN-L04.md:6 BrotherModeUp'

    ... current page(s) using a name the identity contract does not allow there:
    docs/program/absolute-lead/DESIGN-L04.md:6 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-B-onboarding.md:717 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-B-onboarding.md:718 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-B-onboarding.md:719 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-B-onboarding.md:720 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-C-visual-language.md:1143 BrotherModeUp,
    docs/program/absolute-lead/research/visual-surface/LENS-C-visual-language.md:1144 BrotherModeUp

    ----------------------------------------------------------------------
    Ran 199 tests in 20.306s

    FAILED (failures=1, skipped=5)
    exit=1

Three untracked pages, none of them written by this writer and none in this
writer's allowed set, all dropped under `docs/program/absolute-lead/` by
concurrent workstreams. `docs/program/absolute-lead/research/` did not exist when
this writer started; it appeared mid-run and added six of the seven offenders.
The single failure at the start of this writer's work named one offender, the
design document (RED-L04-docs.txt BLOCK 1). Every other test in the suite is
green, including all 199 minus this one, with my changed pages inside them.

REMEDY, unchanged from 0.1 and now needed in three files: backtick the paths, or
have the workstream that owns each page do it. NOT taken here, and one candidate
remedy is explicitly rejected: adding `docs/program/absolute-lead/research` to
`RECORD_DIRS` (`tools/test_bm_docs.py:4405`) would make the suite pass by reading
FEWER pages, which is a weakening of a naming rule the founder ratified, and
`tools/test_bm_docs.py` is in this writer's allowed set only for the one target
list change of 18.6.

### 4.2 The classes that govern the pages this writer changed

    $ python3 tools/test_bm_docs.py TestNoStaleCurrentNumbers TestVersionAndSchemaAgree \
        TestNoUnbackedAbsolutes TestNoDashes TestHistoricalDocumentsSaySo \
        TestCapabilityRegisterIsHonest
    ........................
    ----------------------------------------------------------------------
    Ran 24 tests in 0.159s

    OK

    $ python3 tools/test_bm_docs.py TestGeneratedCapabilityStatusBlock \
        TestGeneratedRoadmapStatusBlock TestTheRoadmapPageIsEvidenceGated \
        TestProductIdentityIsOneRecord
    ----------------------------------------------------------------------
    Ran 28 tests in 1.023s

    OK

The second run is the 18.3 claim made executable: the four capability and
roadmap classes are green BEFORE the register moves, which is what makes the red
they will show between the register edit and the bm-docs regeneration meaningful
rather than noise. `TestVersionAndSchemaAgree` passing also confirms no page
this writer touched states a schema version other than the one Writer A has
already moved to.

### 4.3 The suites that govern the command files and SECURITY.md

    $ python3 tools/test_bm.py TestProjectSecurityClaims
    ----------------------------------------------------------------------
    Ran 2 tests in 0.042s

    OK

That is the line-count claim and the no-network claim, both of which read
`SECURITY.md`. For the record, since the figure is a claim about a tree two
other writers are still growing: the page says the tools are about 91,100 lines
and they measure 95,607 today, a drift of 4.7 percent against a 15 percent
tolerance (`tools/test_bm.py:1104` to `1128`). Writer B's two files would have to
add roughly 25,000 lines to break it. No edit was made to that figure, because
moving it now would mean moving it again after Writer B lands.

    $ python3 tools/test_bm.py TestTheGuidedLoopLawIsWrittenAndWired
    ----------------------------------------------------------------------
    Ran 3 tests in 0.001s

    OK

    $ python3 tools/test_bm.py TestTheSeventhCommandAndTheDeepTourAreWired
    ----------------------------------------------------------------------
    Ran 8 tests in 0.003s

    FAILED (failures=1)

One failure, and it is the collision of section 0.2. The other seven pass.

### 4.4 The copy rule

    files checked: 15
    em or en dash offenders: []

Every file this writer wrote, including this report and the RED file, swept for
U+2013 and U+2014.

---

## 5. What this writer did NOT verify, and what it depends on

Stated plainly rather than left for a reader to infer.

1. **Nothing in `capabilities.status.json`, `README.md` or `docs/ROADMAP.md` was
   verified end to end**, because none of it landed. What WAS verified is that
   the drafted rows pass every part of the shipped guard except the two paths
   that do not exist (3.1), and that the roadmap mapping puts each row on the
   rung 3.3 names.
2. **The disclosure describes behaviour Writer B has not landed.** `SECURITY.md`
   now says `hooks/hooks.json` wires `bm_lead.py watchdog` and that the consent
   inventory test reads every module on a hook line. Both are Writer B's
   deliverables (design 8.2 and 18.2). If either does not land, those two
   sentences are false and must be reverted with the rest of the loop. The same
   holds for the eight command files, which name `bm-lead` subcommands.
3. **The replay verdict of section 14 is not in `docs/KNOWN-LIMITS.md`.** The
   L04 section states the deferral, names
   `TestControllerEventsReplayFromAttribution` in `tools/test_bm_store.py`, and
   spells out what each verdict would mean, but it does not claim a verdict. The
   test did not exist in the tree while this writer worked, so there was nothing
   to run and nothing honest to record. Whoever lands that test owes one
   sentence beside that paragraph.
4. **No founder-facing output was read**, because `tools/bm_lead.py` does not
   exist. The plain-wording rows in `references/terminology.md` are therefore a
   contract Writer B's renderer has to meet, not an observation of what it
   prints. One note for Writer B, because it decides a fixture: the eight new
   rows were appended so that lines 10 to 25 of that file are byte-identical to
   before, which is the range `DESIGN-L04.md` sections 12 (S1) and 17.1 cite for
   the plain-language fixture. If that fixture instead parses the whole table, it
   will also ban the eight new left-column words, and `brief` output that says
   "briefing" would fail it. The right column is what the output should say.
5. **`tools/test_bm.py` is red** and will stay red until the four command names
   are added to the pin (0.2). This writer's own done-check does not cover that
   suite, but the loop's gate does.
6. **Not run at all**, per the brief: `tools/test_all.py`, the store suite and
   the controller suite. Writers A and B own those files and the orchestrator
   runs the gate.
