# FIX L05, WRITER F: the register, the onboarding copy and the disclosure

Writer: Writer F of `docs/program/absolute-lead/DESIGN-visual-surface.md`
section 16. Sections owned: 5, 10, 12.3, and 13.4's docs half.
Date: 2026-08-05. Tree: `/Users/khalil.maaouni/Documents/BrotherModeUp`.

Files written, and only these:

* `references/visual-surface.md` (new)
* `references/terminology.md`
* `references/status-view.md`
* `skills/brotherme/SKILL.md`
* `commands/brotherme-view.md` (new)
* `commands/brotherme-help.md`
* `commands/brotherme-start.md`
* `commands/brotherme-status.md`
* `commands/brotherme-handback.md`
* `tools/test_bm_docs.py` (the `TestNoDashes` target list only, and partially,
  see section 3.2)
* `docs/KNOWN-LIMITS.md`
* `SECURITY.md`
* `docs/program/absolute-lead/evidence/L05/RED-F.txt`
* this report

Files in this writer's allowed set that were **NOT written**, all for one
reason and it is a test rather than a preference: `capabilities.status.json`,
`README.md` and `docs/ROADMAP.md`. Section 3 has the verbatim refusal, the four
drafted rows, and the landing sequence.

No file outside the list was touched. `tools/bm_view.py`, `tools/bm_visual.py`,
`tools/test_bm_view.py`, `tools/test_bm_visual.py`, `tools/bm_store.py`,
`hooks/hooks.json`, `pyproject.toml`, the workflow and every other suite belong
to Writers D and E; the four new ones could not even be read, which is the whole
of section 3.

---

## 0. The two things a reader has to know first

Bad news first, per `references/honesty.md`.

### 0.1 Gate 3 is still shut, so the register did not move

`tools/bm_view.py`, `tools/bm_visual.py`, `tools/test_bm_view.py` and
`tools/test_bm_visual.py` are not in the tree. Checked at the start of this
writer's work and again after the last edit:

    $ ls tools/ | grep -E "bm_view|bm_visual"
    exit=1

All four capability rows this design requires name at least two of those paths
as their evidence, and `tools/test_bm_docs.py:3566` to `3574` refuses an
evidence pointer naming a path that is not in the tree. The rows were NOT
weakened to name a path that exists, and the guard was NOT edited. Section 3
carries the rows, the refusal and the landing sequence. This is the same call
the previous loop's Writer C made for the same reason, and it was right then.

### 0.2 A pinned count moved, and the pin belongs to nobody in this loop

`tools/test_bm.py:5680` `test_exactly_seven_brotherme_commands_ship` pins the
shipped command set by exact equality over `commands/brotherme-*.md`.
`commands/brotherme-view.md`, which design section 12.3 requires, turns it red
the moment it exists. The verbatim before and after runs are in
`RED-F.txt` BLOCK 3, with the one line remedy: add `"brotherme-view.md"` to the
pinned list and extend the comment above it by one clause, exactly as L03 and
L04 each did.

The file was landed anyway rather than withheld, for the reason the pin's own
comment gives: the pin is doing its designed function, and every growth of the
command set is supposed to cost somebody a sentence. `tools/test_bm.py` is
outside every writer's allowed set for this loop, so it was reported rather than
edited.

Nothing else in that class broke. The other seven tests pass, including the two
this writer's edits could plausibly have broken (the deep tour flow existing on
both sides, and the five store backed commands still naming their mechanical
command).

### 0.3 The copy rule and Writer D's new suite collide, and it was not predicted

`tools/test_bm_visual.py` appeared in the tree at 22:21, while this report was
being written. `tools/bm_visual.py`, `tools/bm_view.py` and
`tools/test_bm_view.py` are still absent, so 0.1 is unchanged. But the new file
was checked against the rule design section 13.4 is about to put it under:

    tools/test_bm_visual.py em or en dash lines: [956, 959, 964, 978, 985]

Read at those lines, every one is deliberate hostile fixture data inside
`test_every_text_medium_path_emits_ascii_only`: the test feeds an em dash, an en
dash and an emoji into every text path precisely to prove that none of it
survives into terminal output, and it finishes with an assertion on the em dash
written as a literal character.

So the design's widening of `TestNoDashes` and that test cannot both hold as
they stand. This was NOT resolved here. `tools/test_bm_visual.py` is Writer D's
file, and narrowing the dash guard to let a test file through would be weakening
a founder ratified copy rule to fit one fixture.

PROPOSED MINIMAL REMEDY, for whoever owns that file: write the hostile
characters as backslash-u escapes rather than as literal characters. The test
means exactly the same thing to the machine, the assertion reads identically,
and the file then carries no dash character, so both rules hold at once.
`tools/test_bm_docs.py`'s own dash check is written that way already, in the
same suite, for the same reason.

---

## 1. Per section table

| Section | What it asks for | State | Evidence or reason |
|---|---|---|---|
| 5.1, minute 0 to 1 | the doorway is a terminal block, zero writes, one question | LANDED | `commands/brotherme-start.md`, "The first minute": runs `bm-view doorway`, reads its block out, states the three questions it answers and that it writes nothing |
| 5.1, minutes 1 to 4 | the goal in his own words, one question at a time, through the decision window | LANDED | same file, "Minutes one to four": every question travels as a decision card through `AskUserQuestion`, chat text carries evidence and never the option list |
| 5.1, minute 4 | consent, the first write, then the FIRST render, and the silent republish disclosure | LANDED | same file, "Minute four": the two sentences in order, the second being that approval is asked ONCE and republishing the same page afterwards does not ask again |
| 5.1, minute 4 to 9 | one real unit of the founder's own project, with a visible object | LANDED | same file, "Minutes four to nine", including the refusal to demonstrate on a made up example |
| 5.1, minutes 9 to 15 | the page replaces the wall of text; the first catch-up at a phase boundary; the handback offered before he asks | LANDED | same file, "Minutes nine to fifteen" |
| 5.2 | the departure from LENS-B (no artifact at minute zero) | LANDED by construction | the doorway is text and the first page is written after consent; no page is produced before it |
| 5.3 | three commands during the first fifteen minutes, the rest surface at their trigger | LANDED | `commands/brotherme-help.md` no longer prints the list at minute zero: three named on request, the full list only when asked for, grouped in four sets. `commands/brotherme-start.md` repeats the three and says the others introduce themselves |
| 5.4 | twelve first run rules; three are content review because a test cannot see chat text | PARTLY, and the part that is mine is done | rules 8, 9 and 10 are the content review half and are satisfied by the command files above; rules 1 to 7, 11 and 12 are enforced by `tools/test_bm_view.py`, which is Writer E |
| 10 | all ten limits reach `docs/KNOWN-LIMITS.md` in the design's own words | LANDED | `docs/KNOWN-LIMITS.md`, `## L05: what the live project view, the drawings and the alerts do NOT do (2026-08-05)`, ten bullets in the design's order plus one closing paragraph on the beta rung |
| 12.3, `commands/brotherme-view.md` | new; snapshot, three ways it updates, the pictures in the chat sentence | LANDED | the file, sections "Say these three things", "The two copies", "About pictures in the chat" |
| 12.3, `commands/brotherme-help.md` | one question plus a reference answer; honesty content unchanged | LANDED | the three honesty answers are carried over word for word into their own section, one question away |
| 12.3, `commands/brotherme-start.md` | doorway, consent sentence, first render | LANDED | as above; the mechanical `python3 tools/bm_project.py start` paragraph is unchanged and still last |
| 12.3, `commands/brotherme-status.md` | one line offering the page, AFTER the eight fields | LANDED | one paragraph inserted between the eight fields paragraph and the advanced paragraph, with the reason it is not first |
| 12.3, `commands/brotherme-handback.md` | names the copy as prompt control and the brief page | LANDED | two paragraphs plus the exact paste block, and the two forms of the developer page named as the same content |
| 12.3, `skills/brotherme/SKILL.md` | the deep tour builds from `bm-view render`, the stored address is republished to, line 44's honest limit kept | LANDED | "Deep tour flow" rewritten in three paragraphs plus the honest limit, which grew rather than shrank |
| 12.3, `references/visual-surface.md` | new register: four surfaces and the choosing rule, five shapes and caps, four rungs and delivery, six slots, empty state anatomy, two level rule | LANDED | the file, one section per item, plus the failure block and the snapshot rule |
| 12.3, `references/terminology.md` | five new rows BEFORE the words are used | LANDED | appended after "trace tag": live project view, insight box, alert rung, empty state, fingerprint. Lines 1 to 33 are byte identical (checked, section 4.3) |
| 12.3, `references/status-view.md` | one paragraph: the eight fields are unchanged and the page is those plus what a page adds | LANDED | appended as "The page is this view, not a second status", so every line range other files cite is unmoved |
| 12.3, `capabilities.status.json` | four rows, each naming a path that exists | BLOCKED, gate 3 | section 3. Ten refusals, all of the form "evidence names X, which is not in the tree" |
| 12.3, `README.md` and `docs/ROADMAP.md` | generated blocks regenerated by bm-docs | BLOCKED, gate 3 | the regeneration is the same step as the register edit; regenerating now would render a block from a register that has not moved |
| 12.3, `docs/KNOWN-LIMITS.md` | one new dated section carrying section 10 | LANDED | as above |
| 12.3, `SECURITY.md` | one paragraph: what the published page contains, the private address, permission gated once then silent, the local file primary | LANDED | new section "The page that shows where your project stands, and what publishing it means" |
| 13.4, `TestCapabilityRegisterIsHonest` | no change; the four rows must satisfy it | HELD | no assertion in that class was touched. It is green as it stands, which is what makes the red between the register edit and the regeneration meaningful |
| 13.4, `TestNoDashes` | target list gains five files | PARTLY LANDED, and one of the four is blocked on a collision | `references/visual-surface.md` is in the list today; the four tools files are named in a comment at the same site. Three of them do not exist yet, and `tools/test_bm_visual.py` now does and carries five deliberate dash lines. Sections 0.3 and 3.4 |
| 13.4, the two consent tests | no change, and they are Writer E's file | NOT TOUCHED | `tools/test_bm_consent.py` was neither read into an edit nor written |

---

## 2. What landed, in detail

### 2.1 The first fifteen minutes, as content (section 5)

The design's own claim is that this is content and sequencing rather than
engineering, and that is exactly how it landed: five command files and one skill
file, no code.

`commands/brotherme-start.md` now has five headed stretches instead of three
undifferentiated paragraphs. The first minute is a terminal block and one
question with nothing written anywhere, and it is GENERATED (`bm-view doorway`)
rather than composed, which is the same law that makes every other surface in
this loop a projection of rows. The block's content rules are stated where the
model will read them: three questions answered and no others, one recommended
action, one alternative, no command list, no machinery words.

Minute four carries the two sentences that have to be said in order, and the
second is the one a founder cannot otherwise learn: the permission to publish is
asked ONCE, and after that the page updates silently. Saying it at consent time
rather than letting it be discovered is the whole point of putting it there.

The first render is placed after consent and after the outcome is recorded, and
the file states what the counter will read (2 of 8) and why that is honest in
both directions.

`commands/brotherme-help.md` is the one file where the change is a deletion.
Its old item 2 was a single paragraph naming nine commands and then two more in
the same sentence. That paragraph is gone from minute zero. Three commands are
named if the user asks what he can say right now; the full list is available
when he asks for all of it, grouped into four small sets; and the three honesty
answers (what is verified, what is true about the records, your data is yours)
are carried over unchanged into their own section, one question away. The deep
tour offer and its honest limit are unchanged, which also keeps the pin at
`tools/test_bm.py:5741` green.

### 2.2 The register (`references/visual-surface.md`)

One new file, in the house shape of the other reference pages (a title, a LOAD
WHEN line, then sections). It carries: the one law that everything is generated;
the four surfaces and the five step first match rule for choosing one; the two
level rule and the one expander; colour as the third carrier, including the rule
that completed things stay uncoloured; the five shapes with their caps and their
wording and escaping rules, and the closed ban on everything else; the four
alert levels defined by delivery first, with the four anti noise rules and the
ASCII only terminal forms; the six slots of the insight box, with the rule that
the evidence label is printed by the renderer and never trusted to the author;
the empty state anatomy and its five rules; the five part failure block and the
rule that a raw log appears in exactly one place; and the snapshot rule that
reconciles byte stability with honest staleness.

It names `tools/test_bm_visual.py` and `tools/test_bm_view.py` as what tests it.
Those two files do not exist yet. That is a forward reference in prose rather
than a machine checked pointer, and it is called out here rather than left to be
found: a reference page is not read by `capability_offenders`, so nothing goes
red on it, and the sentence becomes true when Writers D and E land. If either
does not land, that sentence and the four `bm-view` invocations in the command
files are false and must be reverted with the rest of the loop.

### 2.3 The disclosure, both halves (section 10)

`docs/KNOWN-LIMITS.md` gains one dated section in the format of the existing
entries, carrying all ten of the design's section 10 items in its order and in
its words: the page is not live; publishing may be unavailable entirely, with
all five conditions and the contexts where it is off by default; the page holds
no state; nothing on it can act on the project; there are no pictures in the
chat in the terminal; the status line and the footer links are the founder's
settings and not a plugin's; the product cannot show his application running;
mermaid inside an artifact is unconfirmed and nothing relies on it; the page
reaching his phone is not promised; and the two smaller unknowns, recorded
rather than hidden. One closing paragraph states that every capability this loop
registers is beta and names the gap the four share.

`SECURITY.md` gains one section beside the update check, which is the other
place in that document where something can leave the machine. It states what the
two generated pages contain (which is what the records contain), that both go
through the same one write funnel and the same consent gate as everything else,
that the page itself makes no network call of any kind when it opens, that
publishing is Claude's act and not this toolchain's, that the permission is
asked once and silent afterwards, that publishing can be unavailable for reasons
outside this product, and that the file on disk is the primary artefact.

### 2.4 The two reference files that other suites read by line number

Both were APPENDED to, and that is mechanical rather than stylistic.
`tools/test_bm_lead.py:878` reads the LEFT column of
`references/terminology.md` lines 10 to 25 as the banned machinery words, and
several assertions cite `references/status-view.md` lines 8 to 16, 43 to 51 and
53. Appending leaves every cited range where it was. Checked rather than
assumed, in section 4.3.

The five new terminology rows are the ones the design names, and each right
column is the wording the product must actually say: "the page that shows where
your project stands", "what I now believe, what proved it, and what would change
it", "how much attention something needs" said as one of four plain labels, "the
short note in a section nothing has filled in yet", and "a short code that
changes when your records change", with an explicit ban on calling that last one
a hash in anything a user reads. The paragraph under the table was rewritten to
name both groups (eight for founder mode, five for the visual surface) because
it previously said "the eight rows below triage" and would otherwise have become
false.

---

## 3. The four capability rows, drafted and blocked at gate 3

The rows below are the deliverable of section 12.3's register line. They are
quoted here as DRAFTED, not as landed, because `capabilities.status.json` was
not written.

### 3.1 Why they did not land

Run against this tree with the four rows, through the shipped predicate
(`capability_offenders`, `tools/test_bm_docs.py:3539`, imported rather than
reimplemented):

    live-project-view: evidence names tools/bm_view.py, which is not in the tree
    live-project-view: evidence names tools/bm_visual.py, which is not in the tree
    live-project-view: evidence names tools/test_bm_view.py, which is not in the tree
    live-project-view: evidence names tools/test_bm_visual.py, which is not in the tree
    visual-onboarding: evidence names tools/test_bm_view.py, which is not in the tree
    visual-onboarding: evidence names tools/bm_view.py, which is not in the tree
    alert-ladder: evidence names tools/bm_visual.py, which is not in the tree
    alert-ladder: evidence names tools/test_bm_visual.py, which is not in the tree
    visible-handback: evidence names tools/bm_view.py, which is not in the tree
    visible-handback: evidence names tools/test_bm_view.py, which is not in the tree
    offenders: 10

Every path each row names that DOES exist today (`tools/bm_lead.py`,
`tools/bm_store.py`, `hooks/hooks.json`, `commands/brotherme-start.md`,
`commands/brotherme-help.md`, `docs/KNOWN-LIMITS.md`) draws no offender, which
is what proves the guard is reading the tree rather than agreeing with the file.

Through the shipped roadmap mapping (`tools/bm_docs.py roadmap_proof_state`),
each row lands on:

    live-project-view -> verified locally
    visual-onboarding -> verified locally
    alert-ladder -> verified locally
    visible-handback -> verified locally

None of the four names a job under `.github/workflows`, deliberately. Writer E's
deliverable adds two CI steps for the new suites, but a step that exists and has
never executed does not prove "the check runs somewhere other than the author's
own machine", which is what that rung means on `docs/ROADMAP.md` section 1.
`verified locally` is exactly true today.

### 3.2 The rows

Each one states what is PROVEN and by what, then what is NOT PROVEN as its own
named half, then what is OPEN. That shape is taken from
`docs/closure/CLOSURE_REGISTER.md`'s "X-01 Second runtime conformance (SPLIT)"
entry, and it is used here for the same reason: a row that averages a proven
half and an unproven half into one adjective is how a register starts lying.

```json
    {
      "id": "live-project-view",
      "title": "One page showing where a project stands, generated from that project's own records",
      "state": "beta",
      "evidence": "PROVEN: tools/bm_view.py writes the page as one self contained file from the records, through the collectors in tools/bm_lead.py rather than a second reading of its own, tools/bm_visual.py draws it, and tools/test_bm_view.py and tools/test_bm_visual.py check the structure instead of the pixels (a drawn node for each row, a label matching the row it came from, no address outside the file, one file, exactly one recommended next action). NOT PROVEN, and it is a separate half: publishing that file as a private page needs a paid plan, a signed in session and four further conditions listed in docs/KNOWN-LIMITS.md, so what the product promises is the file on disk and the published page is an addition that can be unavailable. OPEN: nobody outside this project has opened either one."
    },
    {
      "id": "visual-onboarding",
      "title": "A scripted first fifteen minutes with three commands and something to look at at each step",
      "state": "beta",
      "evidence": "PROVEN: commands/brotherme-start.md carries the opening block that writes nothing before consent and the first page after it, commands/brotherme-help.md asks one question instead of listing every command, and tools/test_bm_view.py drives the path from an empty folder and fails if a fourth command is offered before the first piece of work completes, if anything is written before consent, or if a section with no rows renders blank instead of the short note tools/bm_view.py holds for it. OPEN, and this is the whole gap: fifteen minutes is a target, no first run by a person who has never used this has been measured, and the checks are structural rather than behavioural."
    },
    {
      "id": "alert-ladder",
      "title": "Four levels of alert where exactly one interrupts, computed from the records rather than stored",
      "state": "beta",
      "evidence": "PROVEN: tools/bm_visual.py computes the levels as one function over rows with no table behind them, so a condition that clears takes its alert with it and nothing has to be dismissed, and tools/test_bm_visual.py holds the four anti noise rules to that (at most one interrupting alert on screen, at most two levels in any one message, no promotion by age, one interrupt per cause per catch-up window). NOT PROVEN: that the ladder keeps a reader engaged, which is a claim about a person rather than about code. OPEN: hooks/hooks.json runs the check when a session stops, so it cannot fire inside a turn that never ends, which is the limit docs/KNOWN-LIMITS.md already records for the half hour catch-up."
    },
    {
      "id": "visible-handback",
      "title": "The offer to take a decision and the work under it back, on screen whether or not a decision is open",
      "state": "beta",
      "evidence": "PROVEN: tools/bm_view.py renders the standing panel on every page, its wording comes byte for byte from tools/bm_lead.py rather than being retyped, tools/test_bm_view.py fails a page that drops it and fails a drawn decision whose last branch is not the handback, and tools/bm_store.py already refuses to record a key decision that offers no handback at all. NOT PROVEN, and by design: nothing on the page can act on the project, the control copies a prompt the reader pastes back into the session, and docs/KNOWN-LIMITS.md states that as a limit rather than dressing it up. OPEN: no handback by anyone outside this project is recorded."
    }
```

`updated` moves to `2026-08-05` in the same edit.

### 3.3 One thing the orchestrator should decide, and it is not this writer's call

`capabilities.status.json` does NOT carry L04's six rows either. Its `updated`
field still reads `2026-08-04`, and the six rows drafted in
`docs/program/absolute-lead/evidence/L04/FIX-L04-docs-report.md` section 3.2
were never landed, even though `tools/bm_lead.py` and `tools/test_bm_lead.py`
are both in the tree now and L04's gate 2 is therefore open. Those rows are not
in this design's scope and were not added here. Whoever lands the four rows
above should almost certainly land L04's six in the same edit and run the two
regenerations once, because two register edits mean two regenerations and one
extra chance for the generated blocks to be out of step with the register.

### 3.4 The landing sequence for whoever finishes it

1. Confirm `tools/bm_view.py`, `tools/bm_visual.py`, `tools/test_bm_view.py` and
   `tools/test_bm_visual.py` are all in the tree.
2. Append the four rows of 3.2 to `capabilities.status.json` and move `updated`
   to the landing date. Consider L04's six at the same time, per 3.3.
3. Expect `TestGeneratedCapabilityStatusBlock` and
   `TestGeneratedRoadmapStatusBlock` to be RED at this point. That red is the
   guards working, and it must not leave the step.
4. `python3 tools/bm_docs.py capability-status --write` and
   `python3 tools/bm_docs.py roadmap-status --write`. Do not hand edit either
   block.
5. Add the four tools files to the `TestNoDashes` target list at
   `tools/test_bm_docs.py:4774` to `4779`, where a comment names them and says
   this. Clear the five dash lines in `tools/test_bm_visual.py` first, per 0.3,
   or that step lands red on purpose and stays red.
6. Add `"brotherme-view.md"` to the pinned command set at
   `tools/test_bm.py:5696` to `5702` and extend its comment by one clause (0.2).
7. `python3 tools/test_bm_docs.py` and `python3 tools/test_bm.py`.

---

## 4. Verification

Every command below was run from `/Users/khalil.maaouni/Documents/BrotherModeUp`
after the last edit.

### 4.1 The done check: `python3 tools/test_bm_docs.py`

    $ python3 tools/test_bm_docs.py
    .................................................................
    .................................................................
    ...................................s.ss.s.s......................
    ....
    ----------------------------------------------------------------------
    Ran 199 tests in 17.779s

    OK (skipped=5)
    exit=0

Green, and 199 is the same count as the baseline captured before any edit
(`RED-F.txt` BLOCK 0). No test was deleted, weakened or skipped to reach it, and
the one test that CHANGED (`TestNoDashes`) reads one more file than it did.

**No bm-docs regeneration command was run.** `python3 tools/bm_docs.py
capability-status --write` and `python3 tools/bm_docs.py roadmap-status --write`
are steps 4 of the landing sequence in 3.4, and running either now would render
a generated block from a register that has not moved, which changes nothing and
records a step as done that is not. There is therefore no regeneration output to
paste, and that absence is the honest form of gate 3 being shut.

### 4.2 The classes that govern the pages this writer changed

    $ python3 tools/test_bm_docs.py TestNoDashes TestCapabilityRegisterIsHonest \
        TestGeneratedCapabilityStatusBlock TestGeneratedRoadmapStatusBlock \
        TestCurrentPagesUseTheCanonicalNames TestNoUnbackedAbsolutes \
        TestNoStaleCurrentNumbers TestVersionAndSchemaAgree
    ................................................
    ----------------------------------------------------------------------
    Ran 48 tests in 1.056s

    OK
    exit=0

The two generated block classes passing BEFORE the register moves is the claim
that makes their red during step 3 of 3.4 meaningful rather than noise. The
naming, absolutes, stale number and version classes all read
`docs/KNOWN-LIMITS.md`, which is the page this writer grew most.

### 4.3 The two files other suites read by line number

    $ git show HEAD:references/terminology.md | sed -n '1,33p' | md5
    95aee08c00cca9b6209c59226d6a61f7
    $ sed -n '1,33p' references/terminology.md | md5
    95aee08c00cca9b6209c59226d6a61f7

Lines 1 to 33 are byte identical, so `tools/test_bm_lead.py`'s fixture (which
reads lines 10 to 25 as the banned machinery words) sees exactly what it saw
before, and the five new rows are outside its range by construction.

    $ cd tools && python3 test_bm_lead.py
    ----------------------------------------------------------------------
    Ran 77 tests in 44.010s

    OK
    exit=0

Run because it reads both reference files this writer changed, not because it is
this writer's suite. Green, including the plain language fixture and every
assertion citing `references/status-view.md` by line number.

### 4.4 The command file suite

    $ python3 tools/test_bm.py TestTheSeventhCommandAndTheDeepTourAreWired
    Ran 8 tests, FAILED (failures=1)

One failure, and it is 0.2: the command set pin. Seven pass.

    $ python3 tools/test_bm.py TestTheGuidedLoopLawIsWrittenAndWired
    Ran 3 tests in 0.001s
    OK

    $ python3 tools/test_bm.py TestProjectSecurityClaims
    Ran 2 tests in 0.062s
    OK

The second is the line count claim and the no network claim, both of which read
`SECURITY.md`, which this writer changed.

### 4.5 The copy rule

    files checked: 12
    em or en dash offenders: []

Every file this writer wrote, swept for U+2013 and U+2014. The nine copy files
(the register, the two reference files, the skill, the five command files) were
additionally swept for any character above U+007E and are pure ASCII, which is
the same property the design requires of terminal output.

---

## 5. What this writer did NOT verify, and what it depends on

Stated plainly rather than left for a reader to infer.

1. **Nothing in `capabilities.status.json`, `README.md` or `docs/ROADMAP.md` was
   verified end to end**, because none of it landed. What WAS verified is that
   the four drafted rows pass every part of the shipped guard except the paths
   that do not exist, and that the roadmap mapping puts each of them on the rung
   3.1 names.
2. **The copy describes behaviour Writer E has not landed.** Four command files
   and the skill now name `bm-view` subcommands (`render`, `doorway`,
   `brief-page`), `references/visual-surface.md` names two suites, and
   `SECURITY.md` and `docs/KNOWN-LIMITS.md` describe a page and its publishing
   behaviour. All of it is Writer D's and Writer E's deliverable. If either does
   not land, those sentences are false and must be reverted with the rest of the
   loop, not left standing.
3. **No generated page was read**, because `bm-view render` cannot be run. The
   empty state anatomy, the six slots, the caps and the four rungs in
   `references/visual-surface.md` are a contract those two modules have to meet,
   not an observation of what they print.
4. **PROBE 0 was not run** (design section 17 step 2: one publish of a five line
   HTML file, recording whether the `Artifact` tool is available in the founder's
   session, his plan, his authentication method and his model provider). It is
   not in this writer's set, and its result belongs in the onboarding copy: the
   sentence in `commands/brotherme-view.md` and `docs/KNOWN-LIMITS.md` currently
   states the conditions in general rather than naming which of them the founder
   himself meets. Whoever runs the probe owes one sentence to
   `commands/brotherme-view.md`.
5. **`tools/test_bm.py` is red** and stays red until the one name is added to
   the command pin (0.2). This writer's done check does not cover that suite; the
   loop's gate does.
6. **Not run at all, per the brief:** `tools/test_all.py`, and every suite owned
   by Writers D and E. `tools/bm_store.py`, `tools/test_bm_project.py` and
   `tools/test_bm_store.py` showed as modified in `git status` throughout this
   writer's work, and `tools/test_bm_visual.py` appeared near the end. That is
   Writer D working in parallel on files this writer never opened for an edit.
   `tools/test_bm_visual.py` was READ, once, to check it against the copy rule
   it is about to come under, which produced the finding in 0.3.
