Status: CURRENT. Written 2026-08-15.

# The team's problems, one by one, and what the two products do about each

Source: `Verified_Delivery_Team_Feedback (1).docx`, five reviewers (the analyst lead,
the engineering lead, the delivery lead, the non-developer reviewer, the senior reviewer) plus one live change, the reference change.
Every status line below was checked against code read today, not against
the feedback's description of the code and not against memory. Where a
claim could not be checked in the time available it says so.

## The finding that changes how the rest of this document reads

The team reviewed a build that is generations behind the code.

    installed:  ~/.claude/skills/brothersbe/VERSION  ->  1.0.0-rc.2
    source:     ~/Documents/BrotherSBE/VERSION       ->  3.2.0 (5ef7da4)

Their two heaviest findings, the one the engineering lead called the largest gap
(nothing in the design folder says what the software should do) and the
one nobody could answer (the QC lead finds unnatural behaviour, UX and
translation problems that no acceptance criterion names), both have
working answers in the source repository, landed 2026-08-15, after the
review was written:

    f65cf07  feat(design): the behaviour table, in the analyst's words
    9bee153  feat(design): the spine artifact stops certifying its own demo rows
    0010130  feat(testkit): the behaviour table becomes the tester's working document
    ea1f25d  fix(design): an id written B-1 no longer hides a deleted rule

This is not a reason to discount the review. It is the review's own point
made a second way: a fix that exists in a repository nobody has installed
is not a fix, and the version string did not warn anybody, which is
already filed as SBE1 (the installed clone and the repository can
disagree while both report the same version).

So the first action is not engineering. It is getting that work in front of
the five reviewers and asking for a re-read of items P9 and P14 specifically.

CORRECTION, added after an adversarial check was asked to disprove this page
and did: an earlier version of this section said the work could be shipped
with no push, because the tag `v3.2.0` is already public. The tag is public.
It does not contain the work. `git ls-tree` on the tag and on `origin/main`
returns nothing for `templates/dossier/08-behaviour.md` or
`tools/sbe_testkit.py`, and 43 local commits are unpushed. The public 3.2.0
carries the version STRING and neither of the two answers. Shipping needs a
push and a NEW version number, and both are founder decisions.

Three instances of one failure in a single day, then: an installed clone
generations behind while reporting a version, this page calling a defect open
28 minutes after it was fixed, and a published tag promising contents it does
not carry. Nothing anywhere binds a version to what is inside it. That is
finding G3 below, and it has now produced every error in this document.

## What is working, and what that costs us

Keep these, because they are load bearing and four of them constrain
every solution below.

- W1. Checks written before the build caught real contradictions in the
  specification (the senior reviewer). This is the tier's whole argument.
- W2. Bad news first, no flattery, no jargon (the senior reviewer). Every solution
  below has to preserve this register, which rules out any fix that
  reports a green verdict it cannot defend.
- W3. The diagnosis matches lived experience: the queue numbers from the
  7 August report (41 waiting on development, 22 waiting on test
  resource, 23 waiting on the QC lead, 11 in Testing (the QC lead), 48 with a TBD end
  date) are the agreed measure of success (the delivery lead). No gate verdict
  replaces them.
- W4. NO-DATA as a real answer (the delivery lead, the engineering lead): absent evidence is never
  a pass. Every solution below must return NO-DATA where it cannot see,
  never PASS.
- W5. Each rule names what enforces it, and the parts no software
  computes are marked as such (the engineering lead). A solution that is only a
  sentence in a document is written UNENFORCED here, in those words.

## The problems, one by one

Format: who raised it, what is true in the code today, the solutions,
and which one is recommended. A solution names the product that owns it,
the files it touches, and the check that proves it.

---

### P1. Setting up is hard without a developer background

Raised by the non-developer reviewer. Python and the Claude command line tool were not on the
machine, the `sbe` command was not on the PATH on Windows, and each
problem had to be solved alone.

Status today. Half fixed and half unchanged. BrotherSBE's CI now runs
Linux, macOS and Windows, with the two POSIX shell tools excluded on
Windows by name (README.md, PARITY.md). So the tools themselves are
tested on Windows. Nothing about the first hour on a fresh Windows
machine changed: there is still no installer that puts the command on
the PATH, and Python plus the CLI are still prerequisites the person has
to satisfy alone.

Why it happens. The install path was designed for engineers who already
have both. the non-developer reviewer is the person the product most needs, and the least
equipped path is hers.

Solutions.

1. RECOMMENDED. A single Windows first-run script, `install.ps1`, that
   detects Python and the Claude CLI, installs neither silently, prints
   exactly what is missing with the one command that fixes it, and adds
   the tool directory to the user PATH. Done-check: a clean Windows
   runner in CI executes it and then runs `sbe --help` at exit 0. Cost:
   small, one file plus one CI leg. This is a diagnosis-and-instruct
   script, not an installer, which is the difference between something
   we can support and something we cannot.
2. A doctor command, `sbe doctor`, that prints a numbered list of what
   is wrong and the command for each. Cheaper, works on all three
   platforms, and it does not solve the PATH problem, because a person
   who cannot run `sbe` cannot run `sbe doctor` either.
3. Remove the prerequisite: run the checks from inside the assistant
   session with no shell at all. Largest change, and it deletes the CI
   story, so it is filed as a direction to decide, not as a fix to
   schedule.

Note. BrotherMode's own limits page already states the installer refuses
Windows by design and WSL is the documented path. That is the honest
current answer, and it is also why the non-developer reviewer lost an afternoon.

---

### P2. The guide describes how BAs work here, incorrectly

Raised by the analyst lead. BAs do not hand over conversations, they hand over a
full specification document with the core acceptance criteria in the
ticket.

Status today. The guide's description is wrong about the adopter team practice, and
the reviewer's warning is the important half: people stop trusting a
document that describes their own job incorrectly.

Why it happens. The line was written from the BrotherMode world, where a
single operator's session history really is the context, and was carried
across without checking whether it described the reader's job.

Solutions.

1. RECOMMENDED. Rewrite the BA section around the specification document
   as the source of context, and keep the underlying principle where it
   belongs: the AI needs the specification, not the chat. Done-check: the
   revised page read and agreed by the analyst lead in writing.
2. Also give the specification a mechanical use: make it the declared
   input to the behaviour table (artifact 08), so the BA's document
   produces the behaviour rows rather than sitting beside them. This is
   the version that makes the correction worth more than an apology.
3. Delete the practice-to-stop list entirely and describe only what to
   start. Least effort, and it loses a real teaching point.

---

### P3. Discussion before planning is not enforced

Raised by the senior reviewer (it must be mandatory, you should not have to ask
for it) and independently by the engineering lead (the tool's own rules said a request
of that shape begins with a brainstorming step, it did not happen,
nothing flagged it or failed).

Status today. CONFIRMED OPEN, and wider than reported. A search of the
whole BrotherSBE repository for any brainstorming or
discussion-before-planning enforcement returns nothing outside scratch
worktrees. BrotherMode mentions brainstorming only in a delegation
reference and in a learning module. Neither product has a check that a
discussion happened, and neither logs its absence.

Why it happens. It was written as an instruction to the model. An
instruction to the model is not a control, which is this product's own
first law, applied here against itself.

Solutions.

1. RECOMMENDED. Make it a state, not a sentence: an intake cannot be
   written until a `clarify` record exists for the change, carrying the
   questions asked and the answers received, and `sbe intake` refuses
   with the exact command that creates one. This lands in the one place
   the process already forces people through, so nothing new has to be
   remembered. Done-check: an intake attempted with no clarify record
   exits nonzero and names the command; with one, it proceeds.
2. Detect and report rather than refuse: a session-close check that
   names every change whose intake has no clarify record. Softer, and it
   fails in the direction the team complained about, which is silence.
3. Put the questions in the skill's own first turn, so the discussion
   happens by default and skipping it is the deliberate act. Cheapest,
   still UNENFORCED, and it changes the default, which is most of the
   value.

The honest note that travels with this one: option 1 is the only version
where nothing can silently skip it.

---

### P4. The decisions record stays empty while decisions get made

Raised by the senior reviewer (the table has zero rows, decisions ended up in
commit messages and a separate notes file, so we pay twice) and the engineering lead
(three memory systems running in parallel, none aware of the others, the
built-in one empty for the whole project).

Status today. Real and only half owned. BrotherMode's conflict detection
carries multi-memory-authority as a named class and reports NO-DATA
rather than pretending to check it: no mechanical detector exists. The
empty decisions table itself is a BrotherSBE defect.

Why it happens. Recording a decision is a separate act from making one,
and every separate act loses. Meanwhile the decision genuinely does get
written, into a commit message, so the information exists and only the
index is missing.

Solutions.

1. RECOMMENDED. Harvest instead of asking: read decisions out of where
   they already land. A `decisions harvest` verb that scans commit
   messages and the notes file across the change's range, proposes rows,
   and writes only what a person confirms. Nobody is asked to type
   anything twice, and the empty table fills from real history.
   Done-check: run over the the reference change range, propose rows,
   and show a non-empty table where the previous run showed zero.
2. Refuse to close a change whose architecture decision record cites an
   alternative that no decision row explains. Stronger, and it adds an
   obligation to a team that is already over-obligated.
3. Name one system as the authority and demote the other two to
   pointers, which is the parity item already filed (O23, one fence
   owner, one shared evidence definition). This is the real fix for
   the engineering lead's version of the complaint, and it needs a founder
   ratification, not an engineer.

---

### P5. Hard for a first-time user, a wall of text, and stale status after clearing

Raised by the senior reviewer. Three separate things: no suggested next command
after each phase, too much text on return to an old session, and status
returning irrelevant or out-of-date information after the working
session was cleared.

Status today. Mixed, and the reviewers' own note is right: the
next-command suggestion exists in the current version and the most
recent release was aimed at first-time users, so parts of this were
already answered by a build they did not have. The stale-status report
could not be reproduced and needs exact steps.

Why the third one is different. Clearing a session destroys the
in-context state, so status is then read from disk. If it comes back
wrong, either the disk state is wrong or two surfaces derive the answer
differently. That second failure mode is documented in this codebase:
four separate hand-rolled next-action ladders were found giving three
different answers to the same dossier, which is why one reducer now owns
the ladder.

Solutions.

1. RECOMMENDED. Ask the senior reviewer for one reproduction (the commands, in
   order, and both status outputs), and re-test on 3.2.0 first. This
   costs one message and may close the whole item.
2. If it reproduces: bind every status line to the commit and timestamp
   it was derived from, and print that stamp, so an out-of-date answer
   is visible as out of date instead of merely wrong. A wrong answer
   that announces its own age is a much smaller defect.
3. For the wall of text: a short form by default, with the long form
   behind an explicit flag. This is BrotherMode's own status-view rule,
   already written, not yet applied to the sibling.

---

### P6. The check that confirms a check ran grades only the shape

Raised by the engineering lead. The gate inspects that the result is a whole number and
the duration positive, so a hand-written file claiming success passes as
well as a real one. Trust evidence produced by the build system, not by
somebody's laptop.

Status today. CONFIRMED, and narrowed since. `gate_ran` in
`tools/sbe_gate.py` now binds the receipt to the current commit, so
evidence produced before the code moved is refused. What it still does
not do is ask WHERE the receipt came from: there is no provenance field
and no CI-only mode.

Why it happens. The gate was designed to be runnable anywhere, and
anywhere includes a laptop.

Solutions.

1. RECOMMENDED. Adopt the engineering lead's own operating rule mechanically: a receipt
   records its producer (CI job id and run url, or the string `local`),
   and `--strict` accepts only receipts whose producer is the build
   system. One configuration value in the pipeline sets it. A local run
   still gets a verdict, it just cannot be the one that closes a change.
   Done-check: a hand-written receipt PASSes without the flag and FAILs
   with it, both proven by a test written failing first.
2. Sign the receipts. Stronger, and it needs key handling that this team
   does not have today.
3. Leave it and document the limit. This is the current state, and the
   product's own rule says an unenforced rule gets written UNENFORCED,
   which is what P6 would then be.

---

### P7. The gate never opens the plan that says which checks were owed

Raised by the engineering lead. Evidence containing one check passes exactly as green
as evidence containing all of them. They closed it in their own project
with a small extra check and think it belongs in the tool.

Status today. CONFIRMED for the general case, with one exception that
matters: the behaviour check added on 2026-08-15 compares the
verification plan (artifact 07) against the behaviour table (artifact
08) in one direction, so a verification plan citing a behaviour id that
no longer exists now FAILs. The reverse direction, every owed check
appearing in the evidence, is still not checked.

Why it happens. The gate was written to read evidence. Reading the plan
means the gate has to know what the plan promised, which is the same
missing link as P9, expressed at the other end of the pipeline.

Solutions.

1. RECOMMENDED. Complete the loop the behaviour check opened: every
   behaviour row's Proof names a check, and the ran-receipt must contain
   a check of that name, or the gate FAILs naming the missing rows. This
   reuses a table that now exists rather than inventing a plan format,
   which is why it is cheap. Done-check: delete one check from a
   receipt, gate goes red naming the row it belongs to.
2. Adopt the engineering lead's own extra check as written and ship it, crediting them.
   Fastest, and it makes the team a contributor rather than a reporter,
   which is worth more than the code.
3. Count only: report how many owed checks appear, as NO-DATA when the
   plan cannot be parsed. Weakest, honest, and it never blocks.

---

### P8. Ordinary changes are sized as heavy ones

Raised by the analyst lead, and proven on the live change: the reference change, a
new field pulled through Strapi and the API to the client, was sized T2.

Status today. FIXED AT 15:39 ON 2026-08-15, in commit `4912bd8`, by a
concurrent session, 28 minutes after this page was committed saying it was
open. `compute_tier` now reads `v[CONTRACT] == "breaking"` for T2 and
`v[CONTRACT] == "additive"` for T1, which is solution 1 below, landed.

That correction is left in place rather than tidied away, because it is this
document reproducing the exact failure it opens with: a page describing a
build that has already moved. The lesson is the same one, and it now has two
instances in one day.

What was true when this page was written, and what the reviewers hit:

    if v["touches_sensitive"] or not v["reversible_under_hour"]:
        return "T3"
    if v["changes_contract"] or v[CONSUMERS] == "many":
        return "T2"
    if v["crosses_boundary"] or v[CONSUMERS] == "some":
        return "T1"
    return "T0"

Answering yes to the contract question alone produces T2, with no other
answer needed. Crossing a service boundary alone produces T1, which is
the reviewers' one correction to their own account, and it sharpens the
point: on an architecture where nearly every change touches an API
contract, one question decides the ceremony for everything.

Why it happens. The question asks whether a contract changed. It does
not ask what KIND of change it is, and the two most common kinds are not
alike: adding an optional field that no existing consumer reads is not
the same risk as changing the meaning of a field three consumers depend
on.

Solutions.

1. RECOMMENDED, AND LANDED at `4912bd8`. Split the contract question in
   two: additive or breaking. Additive plus few consumers lands at T1,
   breaking stays at T2, and T3 is untouched. The remaining work is a
   check rather than a build, and that check has now been run here rather
   than taken from the commit message. The live change's own five answers,
   through `compute_tier` at HEAD:

       the live change, additive: T1
       same change, breaking:     T2
       legacy yes answer:         T2
       required artifacts T1:     ['01', '08']
       required artifacts T2:     ['01', '02', '03', '05', '06', '07', '08']

   Three things that output proves, beyond the tier moving. The vocabulary
   is now `('no', 'additive', 'breaking')`. A legacy answer of plain `yes`
   still resolves to T2, the stricter side, so no existing dossier is
   silently re-sized downward. And the concrete win is the last two lines:
   the same ordinary change now owes two artifacts instead of seven.
2. Let the diff answer instead of the person: derive additive versus
   breaking from the API schema where one exists. More accurate, much
   more work, and it returns NO-DATA on estates with no machine-readable
   schema.
3. Keep the tier and cut what T2 costs: make artifacts 02, 05 and 06
   optional for an additive contract change. Reaches the same felt
   outcome by another route, and it weakens what a tier means, so it is
   the third choice rather than the first.

This is the highest-value item in the whole review, because it is the one
that makes every ordinary change expensive, every day, for everybody.

---

### P9. Nothing in the design folder says what the software must do

Raised by the engineering lead, and called the largest gap: seven documents covering
purpose, process, decisions, technology, data, diagrams and verification,
none of which states the rules the software must follow. Acceptance
criteria live in a ticket, outside the folder and outside every check.

Status today. CLOSED IN SOURCE, 2026-08-15, and absent from the build
they reviewed. `templates/dossier/08-behaviour.md` is a table of
`ID | Starting point | Trigger | Required outcome | Proof`, it is
required from T1 upward (`REQUIRED` in `tools/sbe_intake.py`), and
`check_behaviour` in `tools/sbe_design.py` refuses four distinct ways to
fake it:

- a row with no Required outcome, or no Proof, or a Proof reading TBD,
  fails, because a rule nobody agreed how to check is not finished;
- rows that are still the shipped example rules fail, so deleting the
  template marker does not certify the demo;
- a verification plan citing a behaviour id the table no longer has
  fails, so deleting a rule cannot go unnoticed;
- an unreadable table is a FAIL, an absent one is NO-DATA, never a pass.

That answers every clause of the finding except one: it does not say who
writes the table. The reviewers' sharpest structural observation stands,
that CLARIFY is the only step whose tooling reads "talk to people", and
the fix is to make the BA's specification the input to this table (P2,
solution 2).

Solutions.

1. RECOMMENDED. Ship 3.2.0 to the reviewers and ask the engineering lead to re-audit
   this item specifically. No new engineering, and it converts our
   biggest open finding into either a close or a much sharper reopen.
2. Declare the BA's specification as the input to artifact 08, so the
   table has an owner and a source instead of appearing from nowhere.
3. Nothing further. The gap the review named is covered, and the
   ownership question it exposed belongs to P2.

---

### P10. Nothing handles a requirement changing

Raised by the engineering lead (no version history, no way to mark a design superseded,
no staleness warning, so a design describing an abandoned intention
stays green indefinitely, and a change that starts small keeps its
original obligations) and by the analyst lead from the other end (developers find
edge cases during coding, the specification is updated, and QC then has
to revisit a proof list instead of testing what is ready).

Status today. CONFIRMED OPEN. The word supersede does appear in
`src/brothersbe/lifecycle.py`, and it is about which next action
supersedes which in the priority ladder, not about a design being
superseded by a later one. There is no design version, no supersession
link, and no staleness clock. On the BrotherMode side this is item 2 of
the integrity intake, planned and not built.

This is the most structurally serious item in the review, because it is
the one that gets worse with time rather than staying constant. P13
(fifty point-in-time designs after a year) is the same defect observed a
year later.

Solutions.

1. RECOMMENDED and smallest. A staleness clock with no new concepts: a
   dossier records the commit and date its intake was answered, and any
   check reports NO-DATA with a stale-since line once the change's own
   code has moved past it by a declared distance. NO-DATA, not FAIL,
   because a stale design is an unknown rather than a defect, and this
   product's own rule is that an unknown never reads as a pass.
   Done-check: a dossier whose code moved reports stale, one that did
   not reports normally.
2. Supersession as a link: a dossier can name the dossier it replaces,
   and status refuses to read a superseded one as current. This is what
   makes a year of designs navigable, and it is the real answer to P13.
3. Re-sizing on churn rather than on risk alone: if the diff grew past a
   threshold since the intake, the tier is recomputed and the delta
   reported. This answers the analyst lead's version directly, and it is the most
   work of the three.

All three are the same object designed once, which is why the intake
already treats them as one item. Recommended order is 1, then 2, then 3.

---

### P11. The step called PROVE checks the paperwork, not the work

Raised by the team collectively, on the live run. Everyone assumed step 7
checks that what was built matches what was designed. It checks that the
documents exist, are not empty, and that certain evidence files are
present. The comparison against the design is a different command, which
the step never runs, and the step never looks at review findings at all.

Status today. CONFIRMED. Their suggestion is also the right one, and it
splits into two independent parts, which is why it is cheap.

Solutions.

1. RECOMMENDED, and both halves are documentation, not code. Rename and
   re-describe step 7 as a completeness check, name the comparison
   command beside it so it actually gets run, and move the step off QC
   and onto the engineer, because what it checks is whether the engineer
   produced the documents they owe. Done-check: the revised process page
   read and agreed by the team.
2. Make the completeness step invoke the comparison itself, so the two
   verdicts arrive together and neither can be skipped by not knowing
   about it. Slightly more work, removes the failure mode permanently.
3. Give QC's real question a tool of its own. That is the exploratory
   sheet described under P14, and it answers the deeper half of this
   complaint, which is that QC currently has no tool in the process at
   all.

---

### P12. We use Bitbucket, not GitHub

Raised by the whole team, about the pipeline, the approval step, the
sign-off check, and branch protection.

Status today. SHIPPED on the BrotherMode side and standing law: GitHub
canonical, Bitbucket first class, `docs/BITBUCKET.md` with executed proof
and UNVERIFIED labels where a leg is not yet observed, and
`bitbucket-pipelines.yml` running the full gate. OPEN on the BrotherSBE
side, whose approval and pipeline steps are still worded in GitHub terms.
There is also a live blocker outside the code: the test workspace is
read-only because it exceeds its user limit, so the Bitbucket half of any
two-host check is BLOCKED rather than merely unverified, and no session
should retry a push hoping it lands.

Solutions.

1. RECOMMENDED. Port the two-host pattern from BrotherMode to
   BrotherSBE: host-neutral scripts, one thin pipeline definition per
   host, and any host-specific command reporting NO-DATA naming the host
   rather than erroring or silently passing. Done-check: the same
   fixture through both host legs, with the Bitbucket leg labelled
   BLOCKED by name until the workspace is writable.
2. Make the approval check host independent instead of host specific: a
   signed trailer verified locally beats any provider approval API, and
   it works identically on both. This is the cheaper and better answer
   for the specific step the team named.
3. Decide first, build second, which is what the team actually asked
   for: whether the first phase should run on this repository at all is
   a decision, and it is owed before expansion, not during.

---

### P13. Fifty point-in-time designs after a year, none describing the system

Raised by the engineering lead, over a longer horizon.

Status today. CONFIRMED OPEN, and it is P10 observed later. Nothing
merges, supersedes or indexes dossiers today.

Solutions.

1. RECOMMENDED. P10's solution 2 (supersession links) plus one index
   command that walks all dossiers and prints the current behaviour
   rows across them, newest wins, conflicts named. That is a system
   description assembled from what exists rather than a document
   somebody has to maintain, which is the only version that survives.
2. A living system dossier that every change updates. Better to read,
   and it reintroduces exactly the maintenance burden that made the
   first one go stale.
3. Accept it and say so. Honest, and it is what we are doing now by
   default rather than by decision.

---

### P14. The question nobody could answer

Raised by the analyst lead and by the QC lead's own position. QC verifies far more slowly
than AI-assisted developers build, so a proof list written early adds a
step without removing the bottleneck. the QC lead will not accept against
acceptance criteria: what she finds is unnatural behaviour, UX problems
once she is hands on, misunderstandings between her and the BA, and
awkward text where the translator lacked context. The closing finding is
the sharpest sentence in the document: a green gate will systematically
under-represent how much checking remains.

Status today. Split in two, and the split is the answer.

The tooling half is CLOSED IN SOURCE and, again, absent from the build
they reviewed. `tools/sbe_testkit.py`, landed 2026-08-15, turns the
behaviour table into the tester's working sheet, one case per row, and it
appends an exploratory tail of charters. The first charter is named
`unnatural-behaviour`, described as "the software does something nobody
asked it to". That is the QC lead's category, in her words, in a tool. The tool
also reads a filled sheet back and drafts new behaviour rows from every
finding, so what the QC lead discovers becomes a rule for next time instead of a
comment on a ticket. Deliberately, it is not a CONTENT gate: an empty table
and malformed rows both exit 0, named in the sheet rather than refused, which
is right, because the moment exploratory testing becomes a gate it stops
being exploratory.

One precision, from the adversarial check that refuted the looser wording
this page first carried: it is NOT true that it cannot fail a build. Executed:
exit 1 on an unreadable behaviour file, exit 2 on bad usage. So a CI step
invoking it can go red on an input or usage error, never on what a tester
found. Worth knowing before anybody wires it into a pipeline.

The queue half is NOT ours and must never be gated by us. QC being slower
than AI-assisted development is a capacity fact. No tool fixes it. The
honest posture, already doctrine: measure it, reveal it, remove labour
that feeds it, and never add an obligation and call it a fix. The measure
stays the team's own numbers (41, 22, 23, 11, 48), not any gate verdict.

Solutions.

1. RECOMMENDED. Ship the testkit to the QC lead and run it once on
   the reference change, then ask her the only question that matters:
   did the sheet plus the four charters catch what she would have caught
   anyway. Her answer is the acceptance test for the whole idea.
2. Carry the under-representation warning into the product's own output:
   any all-green summary prints the classes it did not examine
   (regression, cross-device, performance, UX) as NO-DATA by name rather
   than staying silent about them. This makes the closing finding
   structural instead of a paragraph in a review, and it is a small
   change.
3. Measure the queue before and after, on the team's five numbers, and
   publish the delta whether or not it moved.

Solution 2 deserves emphasis: it is the cheapest way to make sure a green
verdict never lies about its own scope again.

---

## The new capability the founder asked for: knowing when to stop and ask

The ask, in the founder's words: the system should recognise when it is
stuck and has tried every method possible, and then ask for help, ask for
guidance, give a recommendation, or hand over to a human.

What exists today, which is three partial answers and no whole one.

- BrotherMode's Full-Auto controller escalates after a unit fails twice
  (`tools/bm_controller.py`, "unit %s failed twice (%s); escalating
  rather than"). Real, mechanical, and confined to autonomous runs. An
  ordinary interactive session has none of it.
- BrotherSBE's worker brief carries `maxAttemptsPerApproach: 2` and the
  sentence "stop after two attempts at the same approach fail from the
  same root cause; report" (`src/brothersbe/work.py`). That is an
  instruction to a subagent, which this product's own first law says is
  not a control.
- Both products have stall detectors (`tools/bm_stall.py`,
  `tools/sbe_stall_detector.py`) that are genuinely good and watch the
  wrong thing: dead workers, stale fences, disk floor, an owed handover.
  They detect a stuck MACHINE. Nobody detects a stuck LINE OF REASONING.

So the gap is exact and small: no counter anywhere records that the same
objective has defeated three different approaches, and no rule converts
that count into a decision to stop.

The design, in one paragraph. One small tool records attempts against an
objective and answers one question, continue or escalate. Three triggers,
all mechanical, any one is enough: three distinct approaches have failed
on the same objective; two attempts have failed with the same observed
root cause, which means no new information was bought; or a declared
budget (wall clock, tokens, or attempts) is spent with no done-check
having passed since it started. The verdict is a state, not advice, and
the escalation packet uses the checkpoint shape this product already
defines: what I found, my recommendation, the alternatives I have not
tried, the one decision I need, and what I will do if you say nothing.

The part that makes it a control rather than a sentence. A session close
hook refuses a silent ending while an escalation is open. That is the
only place a hook can observe the failure mode the founder is describing,
which is a session that quietly gives up, reports something vague, and
stops. Everything else in the design is bookkeeping; this is the check.

What it must not do, stated now so it does not get added later. It never
answers the question itself, it never retries automatically, and it never
escalates on a single failure, because a system that asks for help too
early is as useless as one that never asks. Escalating with no
recommendation is also refused: the packet requires a recommended option
and a default action, because handing a person a problem with no proposal
moves the work without reducing it.

Where it lives. BrotherMode owns it, because BrotherMode governs one
person's session and this is a property of a session. BrotherSBE ports it
under the existing porting rule (PARITY.md), where it replaces the prose
in the worker brief with the same counter the parent uses.

---

## What the two products together now cover, and what they do not

Covered by shipped or source code today: P9 behaviour (source), P14
tooling half (source), P12 on the BrotherMode side, P5's next-command
half, P7's one direction, P6's commit binding.

Covered by a named plan, not built: P10 and P13 (one object, the
integrity intake), P4's authority question (parity item O23).

Not covered, and needing engineering decided here: P8 tier inflation, P3
discussion enforcement, P6 provenance, P7's reverse direction, P11's
rename, P1's Windows first run, P14's solution 2 (unexamined classes
printed as NO-DATA), and the escalation capability.

Never ours, and the tooling must keep saying so: QC capacity, the QC lead's
acceptance standard, and whether the first phase runs on this repository.
The team's five queue numbers remain the only measure that decides
whether any of this worked.

## The holes nobody complained about

The fourteen problems above share one weakness: every one was RAISED. The
list is therefore shaped by what five people happened to hit in one review of
one change, which is a good sample of the visible failures and a poor sample
of the silent ones. A separate pass walked the whole lifecycle, ideation to
acceptance, asking what has no tool at all. Eight findings, ranked by damage
per unit of effort to close. Each names its owner, because three of them are
not ours to fix.

G1. THE AGREED SUCCESS MEASURE IS NOT COMPUTED BY ANYTHING. The five queue
numbers are named throughout as the only thing that decides whether any of
this worked, and they were hand-counted from a report. Nobody can recompute
them today, so a before-and-after would be a second hand count. Reveal only,
the decision is the team's. Smallest close: one command that reads a tracker
export and prints each number it can compute, reporting NO-DATA by name for
any the export cannot supply. Check: reproduce 41, 22, 23, 11, 48 from the
7 August export, or name which of the five it cannot.

G2. THERE IS NO ACCEPTED STATE. The chain ends at a green gate and a merge.
No acceptance record, no accepting party, no status line for it. So the last
thing the system knows about a change is that its evidence passed, and
whether anybody accepted it is not represented at all. This is the same gap
the QC lead's position describes, seen from the data model. BrotherSBE.
Smallest close: an acceptance record (who, when, against what) with status
printing acceptance as NO-DATA until one exists, never FAIL. Check: an
all-green change reports acceptance NO-DATA, then accepted once written.

G3. EVIDENCE BINDS TO A COMMIT, NEVER TO WHAT IS RUNNING. A change can be
certified against a commit with nothing recorded about which build a human
actually exercised. That is precisely how five reviewers spent a week on a
build generations behind the source and no verdict noticed. BrotherSBE.
Smallest close: a deployed-ref field on the delivery record, and a status
line reporting DRIFT when it differs from the evidence commit. Check: set a
deployed ref one commit behind, status prints DRIFT naming both refs.

G4. A DEFECT CANNOT BE ENTERED AS A DEFECT. Intake has no origin field and no
path for work that starts from a broken behaviour rather than a
specification. A bug fix must be described as if it were new work, and the
fix carries no link to the behaviour that failed, so an escaped defect leaves
no trace in the table that should have caught it. Whether people therefore
skip the tool is UNMEASURED and is not claimed here. BrotherSBE. Smallest
close: intake accepts a defect origin and requires exactly one artifact, the
behaviour row that should have caught it, instead of the tier's full list.
Check: a defect intake naming a regression row proceeds at T1; one naming no
row refuses and prints what is missing.

G5. NOTHING RECORDS WHAT HAPPENED AFTER MERGE. No reopen, rollback, escaped
defect or emergency fix is captured against the change that caused it, so no
data exists to compare a tier against its real outcome. Concretely: the tier
split that just landed will ship with no way to measure whether it classifies
better than the rule it replaced. BrotherSBE. Smallest close: an outcome
field stamped at close, plus one report of tier against outcome that refuses
to compute under five samples. Check: six closed changes print the table,
four print NO-DATA.

G6. A REQUIREMENT DISCOVERED DURING THE BUILD TELLS NOBODY. P10 covers a
requirement that changes and goes stale. A requirement that APPEARS mid-build
is the opposite direction and has no event at all. A behaviour row added
after a test sheet was generated leaves that sheet unchanged and unmarked, so
the sheet is one case short with nothing saying so. This is the analyst
lead's own account of how a sprint actually goes, and it is the half of it
that has no answer. BrotherSBE. Smallest close: a new row stamps itself as
discovered in build and marks any already-generated verification plan or
sheet stale by row id. Check: add a row after generating a sheet, the sheet
reports stale naming the new id.

G7. REVIEWER AND TESTER CONCENTRATION IS INVISIBLE TO THE ROUTER. 23 changes
wait on one reviewer and 11 sit in one tester's column. The reviewer route
selects by capability and prints no count of what that person already holds.
Whether routing worsens the concentration is unmeasured; the point is that
the router cannot see it either way. Reveal only, staffing is the team's
decision. Smallest close: the route prints how many open changes are already
routed to that name. Check: route three to one reviewer, the third prints
three.

G8. NO CHANGE CARRIES AN OPENED-AT AND CLOSED-AT PAIR. Commitment and end
dates are the team's own call and no tool should set them. The tooling answer
is narrower: the duration of a T1 or a T2 is not recorded anywhere, so the
whole tier-cost argument has no measurement on either side, and 48 undated
tasks cannot be compared against anything. BrotherSBE. Smallest close: stamp
both timestamps on the change record and print median duration by tier,
refusing under five samples per tier. Check: a fixture prints a median for T1
and NO-DATA for T3.

G9. THE ONE-WRITER CONTROL IS INERT IN THE ASSURANCE REPOSITORY ITSELF.
Found while trying to use it, which is the only way this kind of thing gets
found. Asked directly rather than grepped, `python3 tools/sbe_fence_hook.py
fences` answers, about twenty times in a row:

    STATE.md carries a live fence line with no readable `files:` scope, so
    this hook cannot tell what it owns and did NOT enforce it.

Every one of those lines is a legacy fence from July, and the hook fails open
by design, which is right. The consequence is that BrotherSBE's own
single-writer protection currently enforces nothing in its own tree, while
STATE.md reads as though about twenty writers hold claims. The sibling
product's equivalent hook, in the other repository, refused a write across a
live fence during this very session, correctly and by name, so the mechanism
works: it is the registry that has rotted. BrotherSBE. Smallest close: the
hook already knows how to say a line is unreadable, so make an unreadable
line a reported STALE with the command that clears it, and clear the July
lines. Check: `fences` prints zero unenforceable lines on a clean tree, and
one after a malformed line is added.

This one is filed with a note about its own discovery: the drift check in
this session refused a plan to answer the fence question with a grep, and
insisted the control be asked. The grep would have listed twenty live fences
and I would have believed them. Asking the control returned twenty refusals
to enforce, which is the opposite conclusion.

WHAT THE SAME PASS FOUND ADEQUATELY COVERED, which matters as much, because a
gap hunt that reports gaps everywhere has not hunted: design (the eight
artifacts, the decision record with real alternatives, the behaviour check
refusing four distinct fake-outs), build execution for one person (claims,
fences, single writer, worker dispatch), code review routing and reviewer
independence, test design (the behaviour table, the verification plan, the
exploratory charters), evidence execution and its binding to a commit,
migration rollback specifically (a migration plan with no reverse task is
refused), and cross-person handover.

THE PATTERN IN G1, G2, G3, G5 AND G8, worth naming because it is one hole
seen five times: the system is complete up to the merge and blind after it.
Everything it knows is about whether a change was PROVEN. Almost nothing it
knows is about whether the change WORKED. That is also where the north star
lives, so this is not a tidy-up list.

## The outside architecture proposal, judged

A second document arrived mid-analysis: BROTHERS-VERIFIED-DELIVERY-
ARCHITECTURE-WBS.md, 3,178 lines, written by ChatGPT after reading the same
team feedback. The founder's instruction was to judge what to implement, why
and how. This section is that judgment. It is worth reading: its
complaint-by-complaint structure, its traceability matrix and its escalation
chapters are better than anything we had written on those subjects.

### Adopted immediately, and already in the code as of this session

- Its escalation ladder (canonical local facts, then a trusted machine
  source, then one bounded test, then a human) is the front half of the
  problem, and our attempt counter was only the back half. Adopted.
- Its "escalate immediately" list becomes the `forcing_condition` trigger:
  seven named conditions where guessing is the danger, so the count never
  applies and the escalation fires at zero attempts. This is BrotherSBE's L6
  prose promoted to a state.
- Its rule that a truth-affecting failure escalates after ONE attempt, not
  two, is a correction to our design and it is right: a wrong status or a
  PASS with a known counterexample is a defect in what this product sells,
  and a second attempt only means the wrong answer stands longer.
- Its help-request format is richer than ours in two fields that change what
  the human does, so both were added: who is being asked, and the risk if the
  system guesses. An unaddressed question waits longest, and the stated risk
  is what decides how fast somebody answers.

All four are in `tools/bm_escalate.py` with 32 passing tests, including the
discriminating pair that proves the truth-affecting flag is what moves the
verdict rather than the wording of the root cause, and six more that pin two
defects an adversarial reviewer executed against the first version: a passing
attempt used to clear an unresolved forcing condition, and punctuation used
to manufacture distinct approaches and so a false escalation. Both fixed,
both pinned, and the remaining ceiling pinned honestly beside them, which is
that two different words for one root cause are still two root causes.

### Adopted as the target shape, with a cheaper first increment

- Section 11, separating the risk tier ("how bad is failure") from the
  evidence trigger ("what surface changed"), is the best idea in the
  document and it is a better diagnosis of P8 than ours. The contract
  question is an evidence trigger that was wired as a risk input, which is
  exactly why the reference change came out T2. We adopt the framing and
  ship the four-line additive-versus-breaking split as its first increment,
  because that fixes the reported case this week and moves toward the same
  place. Full separation follows once the split is in use.
- Section 10, the evidence graph with staleness and precision, and section 9,
  requirements with supersession, are the same object as P10 and P13. Adopted
  as the shape. First increment stays the staleness clock, because it is the
  one that stops a stale design reading as green.
- Section 12, one durable event journal with materialised views, and its rule
  that chat is context and commit messages are sources rather than parallel
  memories, is the right answer to P4. Adopted as doctrine now, and the first
  increment is the decisions harvest.
- Section 22, progressive QC (QC starts early and does not finish early), and
  section 24's user-friendliness requirements are adopted as written. They
  cost nothing and they say plainly what the team asked for.

### Amended before adoption

- Sections 13 to 20 design Bitbucket support in three levels and recommend
  level 1 as the MVP. The sequencing is wrong for our estate and the document
  could not have known why: the test workspace is READ-ONLY today because it
  exceeds its user limit, and the free plan allows fifty build minutes a
  month. So level 1 gets built and its Bitbucket leg is labelled BLOCKED by
  name until the seats are fixed, rather than scheduled as if it could be
  certified now. Nothing here is a reason to buy a paid plan.
- Its escalation rule of "two failed automated approaches" for a named class
  is compatible with our counter and does not need a second mechanism: it is
  a declared budget of two, which the tool already accepts.

### Not adopted now, with the condition that would flip it

- Sections 2.1 and 5 propose one UX layer over both products, with unified
  `/brothers:start`, `next`, `status`, `review` and `deliver` commands. Not
  now. Three reasons: the product direction on file makes BrotherSBE a
  standalone skill and BrotherMode the general orchestrator, so this is a
  merge rather than a feature; none of the five reviewers reported the
  boundary as a problem, they reported sizing, behaviour, evidence and setup;
  and building it would consume exactly the capacity that fixes those. FLIP
  CONDITION: if the re-test on 3.2.0 puts boundary confusion in the
  reviewers' top three, build it.
- Section 2.2's canonical object model, if built as a new store, is not
  adopted. BrotherMode already has a record and receipt store, and standing a
  parallel journal beside it creates a third source of truth, which is the
  defect P4 is about. Adopted as the target SHAPE for what the existing store
  should express. FLIP CONDITION: a named failure the current store provably
  cannot express.
- The five release trains R0 to R5 as a program are not adopted as a plan.
  The work is right and the packaging assumes a team. Our own order below is
  what a single founder can actually run, and it deliberately front-loads the
  two items that cost nothing to try.

### What the document is missing, stated so it is not mistaken for complete

It does not know that the Bitbucket workspace is read-only, that the free
plan caps build minutes, that BrotherSBE 3.2.0 already closed the behaviour
gap and the exploratory-testing gap, or that the installed build the team
reviewed was 1.0.0-rc.2. Read it as a strong architecture with an out-of-date
picture of the estate, which is the same failure mode as the review itself,
and for the same reason.

## What the direction review changed in this plan

An architecture review was run against both products' stated north stars,
briefed to find drift rather than to agree. Four things came back that this
plan had wrong or missing, and all four are folded in above or below.

D1. THE ORDER HID A HALF-DEPLOYED STATE. The escalation capability was listed
as built. It was four registrations out of six, and the suite that should
notice cannot: the effects registry validates the entries it HAS, so an
undeclared module is silent rather than red. Confirmed here by hoisting the
dispatch table to make it discoverable, which turned the suite red
immediately, then reverting because the registry file sits under another
session's live fence. The honest state is in `docs/ESCALATION.md`.

D2. P3 AS WRITTEN COLLIDES WITH A RATIFIED ADOPTION RULE. Solution 1 makes
intake REFUSE without a clarify record. The assurance product's own direction
says: paved road, not forced road, no intake before work, the pipeline
reports and never blocks, and enforcement is something an estate turns on
later after watching the reporter catch something true. The drift is not the
control, it is the missing word: P3 solution 1 ships BEHIND AN ESTATE SWITCH,
defaulting to report. That amendment is adopted here and P3 above should be
read with it.

D3. THE FLIP CONDITION ON THE DECLINED UNIFIED SURFACE WAS DECORATION. It
said: flip if boundary confusion reaches the reviewers' top three. That
conditions on an unprompted list, from a re-test with no date and no owner,
about a category nobody will be asked about. Replaced with two observables
that need nobody's opinion: flip when a person runs a verb against the wrong
product twice in one change, or when the ported escalation ledger and its
parent disagree about the same objective.

D4. THREE NEW REFUSALS WERE PROPOSED AND NONE HAS AN EXCEPTION PATH. P3's
gate, P6's strict mode and P7's failure all block, and the assurance
product's own owned list includes exceptions with owners and expiry, while
the orchestrator's guardrails track a false-refusal rate the north star may
not be bought with. No false-refusal budget and no escape hatch was named for
any of the three. Adopted as a precondition: none of those three ships
without an exception carrying an owner and an expiry date.

The same review confirmed one thing worth keeping: nine of the fourteen
recommendations protect one of the five things the assurance product owns,
and the four that touch the north star metric all do it the same way, by
getting a non-founder to run the thing. That concentration is correct rather
than a defect.

## The order, and the one next action

Order by value per unit of work, which is not the same as by severity.
Revised after the direction review, which pointed out that the previous
version scheduled nothing for the two items that gate the north star metric
and never scheduled the measurement that decides whether any of it worked:

0. TAKE THE BASELINE FIRST, before anything else lands. G1's five queue
   numbers, counted once, however crudely. The tier split has ALREADY
   shipped, so part of the before-picture is gone; every further hour
   without a baseline loses more of it. This is minutes of work and it is
   the only thing here that cannot be done later.
1. Push the work and cut a new version, then send the note. The public tag
   does not contain the two answers, so there is nothing to re-read until
   this happens. Founder decision, outward facing.
2. P1, the Windows first run, which the previous order left out entirely
   even though the primary metric requires a non-founder to run the thing
   and the non-developer reviewer could not reach a command line.
3. The escalation capability, BUILT THIS SESSION (`tools/bm_escalate.py`,
   26 tests green, `docs/ESCALATION.md`). Its registration into the five
   shared registries is NOT applied, because another session held live work
   across seven files in this tree while it was written; the exact edits are
   listed at the end of `docs/ESCALATION.md`.
4. P14 solution 2, unexamined classes printed as NO-DATA (small, and it
   permanently fixes the honesty of a green verdict).
5. P3 solution 1, then P7 solution 1, then P11, then P6, then P10.

The one next action: send 3.2.0 to the analyst lead and the engineering lead with P9 and P14 named,
because everything else in this list is cheaper to decide once we know
whether those two are actually closed.
