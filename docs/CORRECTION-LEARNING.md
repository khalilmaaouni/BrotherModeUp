# Correction learning, explained plainly

Written 2026-07-29, Loop 13 of the correction-learning program. This is the
plain-language companion to the technical record in
`docs/superpowers/specs/2026-07-28-correction-learning-program.md` and
`docs/NOT-FINALIZED.md`. If a sentence here and a sentence in one of those two
disagrees, those two win: this file explains, it does not redefine.

Every command shown below was actually run against a real, throwaway store
while writing this file (built fresh under `/tmp`, then deleted), not copied
from a spec. Its exact output is quoted.

## What this is, in one sentence

A place on your own disk where a correction you give Claude, once you approve
it, is written down as a rule, and where Claude is required to check that list
before doing substantial work, so the same correction does not have to be
given twice.

Approved product wording for this system: "founder-approved correction
memory", "evidence-backed learned rules", "retrieval and outcome tracking",
"local correction-learning system". It is deliberately NOT described as
autonomous self-improvement, as statistical learning, as a guarantee against
repeated corrections, or as production ready. None of those claims is
supported yet, and section "What this does not claim" below says why.

## What is actually built right now

Everything below exists in this repository, is covered by the test suite, and
was exercised by hand for this document.

- **Capture.** You (or, soon, an automatic detector, see below) write down a
  correction: what situation it applies to, what to do instead, and why.
  Nothing changes yet, it is only a candidate.

  ```
  $ python3 tools/bm_learn.py capture --trigger "pushing commits or publishing a branch to GitHub" --action "use the GitHub Desktop app, never a bare git push" --because "the founder wants every push visible on screen" --scope global
  captured caf81782 (pending, nothing changes until you approve it)
  ```

- **Approval, and only your approval.** A candidate becomes a rule only when
  you say so. Nothing in this system, automatic capture included, can approve
  itself. That is not a policy choice that could be relaxed later, it is a
  hard rule this codebase enforces.

  ```
  $ python3 tools/bm_learn.py approve caf81782 --gate --ref "why you approved"
  approved as rule f9464c03
    f9464c03  [global, approved, gate] v1
       When: pushing commits or publishing a branch to GitHub
       Do  : use the GitHub Desktop app, never a bare git push
  ```

- **Retrieval, with the reason shown.** Claude (or you) can ask what rules
  apply to a piece of work and see why each one matched, not just a bare list.

  ```
  $ python3 tools/bm_learn.py relevant --query "I want to push this branch to github"
    f9464c03  rank=1
    Scope: global     State: approved     GATE
    When : pushing commits or publishing a branch to GitHub
    Do   : use the GitHub Desktop app, never a bare git push
    Why  : the founder wants every push visible on screen
    Match: terms ['branch', 'github', 'push'], relevance 0.6
  ```

  Retrieval is honestly labelled `mode=lexical`: it matches on shared words,
  the same technique a good search box uses. It is not full-text search
  (FTS5) and it is not an AI judging relevance. Both are stated in the output
  itself, not only in this document.

- **Skill-driven retrieval (Loop 11A).** `SKILL.md` requires a Claude session
  to run retrieval before substantial work and to name which rule IDs it
  applied. This is "Stage A": the skill pulls rules, nothing pushes them at
  you automatically yet (see Loop 11B below).

- **Conflict detection and supersession (Loop 6).** Approving a rule that
  plainly reverses a live rule ("always push through the desktop app" against
  "never push through the desktop app") is refused unless you override it, and
  the override is recorded, not silent. `bm_learn.py verify` reports integrity
  problems (contradictions, a dead successor, and similar) with an exit code a
  script can act on: 0 clean, 1 findings, 2 could not run.

  ```
  $ python3 tools/bm_learn.py verify
  learning-verify: 1 rule(s), 0 edge(s), 9 check(s) run
    note: fts-drift: no FTS index exists in this schema, retrieval mode is lexical, so there is nothing to drift from
    no findings
  ```

  This detector is lexical, on purpose stated as a limit rather than a
  surprise: it catches a reversal of the same instruction, it does not catch
  "indent with tabs" against "indent with four spaces". You can always declare
  a conflict by hand with `bm_learn.py link a contradicts b`, and a declared
  conflict counts the same as a detected one everywhere downstream.

- **Retrieval and application outcomes (Loop 7).** Every rule shown to a
  session can be marked followed, ignored, not relevant, or unknown, so the
  store can answer "was the rule actually followed" rather than only "was it
  shown".

- **Grading with rework and escaped defects (Loop 8).** If a piece of work had
  to be redone, or a defect escaped a record you had already called done, that
  outcome can be recorded and linked to whichever rule applied to that work.

  ```
  $ python3 tools/bm_learn.py outcome ef85f24f --kind rework --note "had to redo the push because it went through git push directly" --artifact x.py
  captured 52878111 from rework (pending, nothing changes until you approve it)

  $ python3 tools/bm_learn.py loop-failures --since 30d
  loop failures since 2026-06-29T06:04:33Z
    applications in window: 0
    retrieval_miss       0
    compliance_failure   0
    bad_rule             0
    scope_error          0
    not_decidable        0
    repeated settled corrections: 0
    unresolved contradictions: 0
    rules never retrieved: 1
    rules always marked not relevant: 0
    rework and escaped defects linked to a rule: 0
    unattributed outcomes (listed separately, never averaged in): 1
      52878111 rework: no rule application was recorded for that work, so this outcome is attributed to no rule
    NOT MEASURED: no rule application falls in this window, so every class below is not measured rather than zero
  ```

  Notice what that output does NOT do: it does not turn zero applications into
  a false "everything is fine" reading. Every line it cannot support says so
  (`NOT MEASURED`) instead of printing a zero that would read as a clean bill
  of health. A rework or an escaped defect is never counted as "you repeated
  yourself": you did not say anything twice, the work went wrong, and those
  are graded and reported on their own line so the two are never confused.

- **Multi-language capture (Loop 4).** Correction detection now recognises
  English, French and Japanese phrasing, and a long correction is excerpted
  with the omitted character count recorded rather than silently dropped, as
  the old English-only, 400-character filter used to do.

  ```
  $ python3 tools/bm_learn.py capture --trigger "quand on ecrit du code" --action "toujours ecrire des tests" --because "le fondateur veut de la fiabilite" --scope global
  captured ddd6e256 (pending, nothing changes until you approve it)
  ```

- **A stronger secret scrubber, and full withholding of raw founder text
  (Loop 12).** Every vendor-shaped secret pattern (an OpenAI-style key, an AWS
  key, a GitHub token, a French national ID number, and others) is now
  anchored so a secret glued to a word character on either side is still
  caught, which an earlier version of the scrubber missed. `dump` and every
  JSON-emitting command now withhold the raw founder text and evidence
  excerpts entirely, through one shared rule, rather than printing them
  because a particular command forgot to ask.

- **A result limit can no longer hide a gate rule (Loop P4).** `--limit` now
  caps SOFT rules only. Every applicable live gate rule is returned whatever
  the limit says, including `--limit 0` and negative limits, which both mean
  "gates only". Before this, a gate was exempt from the relevance floor but
  still subject to the slice, so a wordier soft rule could outrank it and a
  small limit cut it off entirely. The output now states the two facts
  separately, because they are two different things: gate delivery is a
  guarantee, soft omission is a tuning knob.

  ```
  $ python3 tools/bm_learn.py relevant --query "deploying the website to production" --limit 0
  RELEVANT FOUNDER RULES (mode=lexical)

    47ff18cb  rank=1
    Scope: global     State: approved     GATE
    When : when about to force push
    Do   : never force push
    Match: terms (none, shown because it is a gate), relevance 0.0

  Constitution overrides learned rules.
  Gates: 1 of 1 applicable returned. A result limit cannot hide one.
  Soft rules: 0 shown, 1 omitted by --limit 0. Raise the limit to see them.
  ```

  The JSON form carries the same numbers as `gates_returned`, `gates_total`,
  `soft_returned` and `soft_omitted`. Retiring a gate still works: a
  deprecated or forgotten gate is not live, so it is not delivered.

- **An empty screen says WHY it is empty (fix round P4-fix).** Zero results has
  two causes that used to print the same sentence: nothing matched, or rules
  matched and the limit cut every one of them. The first shipped wording said
  "none matched" either way and, on the path that returns early, never printed
  the omission count at all, so `--limit 0` in a store with a matching rule read
  as a clean complete answer while the JSON from the same call reported the
  omission. The two causes are now distinguishable, and the gate sentence and
  the soft sentence are printed on every path out of the command.

  ```
  $ python3 tools/bm_learn.py relevant --query "deploying the website to production" --limit 0
  no founder rules SHOWN here (1 in scope; mode=lexical). Rules matched. The result limit cut every one of them.
  Gates: 0 of 0 applicable returned. A result limit cannot hide one.
  Soft rules: 0 shown, 1 omitted by --limit 0. Raise the limit to see them.

  $ python3 tools/bm_learn.py relevant --query "zebra xylophone quarantine"
  no founder rules apply here (0 in scope, none matched; mode=lexical)
  Gates: 0 of 0 applicable returned. A result limit cannot hide one.
  Soft rules: 0 shown, none omitted.
  ```

## What this does not claim, and why

- **Not autonomous self-improvement.** Every rule that changes anything went
  through your approval. Automatic detection (below) finds candidates, it
  never promotes them.
- **Not statistical learning from a small number of sessions.** A person has
  perhaps twenty to forty rules. There is no dataset here large enough to
  train or validate anything, and the program deliberately does not pretend
  otherwise (see "Loops deliberately not built" below).
- **Not a guarantee against repeated corrections.** The system can now tell
  you when a correction repeats one you already settled, and why (never
  retrieved, retrieved and skipped, retrieved into the wrong work, or followed
  and wrong anyway), but it cannot promise a correction is never needed twice.
- **Not correctness judged by an LLM.** Retrieval relevance is lexical word
  matching, stated as such in its own output. Grading rework and escaped
  defects is something you or an external process records, not a judgment the
  model makes about its own work.
- **Not production ready before dogfooding.** See the next section.

## What automatic capture does, and does not do

An automatic detector watches for correction-shaped messages at the end of a
session and files them as pending candidates. It runs in English, French and
Japanese, and a long message is excerpted rather than dropped. It has never,
under any configuration, been given the ability to approve what it finds.
Approval is founder-only, forever: that is a hard rule in the code, not a
setting.

The detector is a set of phrase patterns, not language understanding. A
correction phrased in a way none of the packs recognise is still missed, and
the honest name for that is a recall gap, not a bug that will be quietly
fixed by more patterns. `bm_learn.py capture` covers any language, by hand,
regardless of what the detector recognises.

## The biggest honest gap: this has never run on a real day of work

Every number, every command output, and every test in this document and in
this codebase comes from a test suite, an adversarial probe against a
throwaway store, or a scripted demonstration. **Not one hour of the founder's
actual work has gone through this system.** That is `docs/NOT-FINALIZED.md`
item 1, marked UNPROVEN and ranked as the highest-harm open item in the whole
project, and it stays UNPROVEN here too. Only using the system for real,
across real working days (Loop 14a in the program), closes it. No amount of
further testing can.

## What was deliberately not built, and why

- **Loop 9, evaluation partitions and deterministic replay.** Not built,
  reopen when the rule corpus is large enough for a train/validation/test
  split to decide anything. At twenty to forty rules for one person, a
  validation partition would hold about eight cases, and a statistically
  significant result over eight cases does not exist. Building the machinery
  anyway would make an unsupportable number look rigorous, which is the exact
  failure this program's own principle (delete or relabel a metric that
  cannot move mechanically or cannot support a decision at current volume)
  forbids.
- **Loop 10, generated LESSONS and TOOLBOX views.** Not built, reopen when
  hand-curating `docs/knowledge/LESSONS.md` and `docs/knowledge/TOOLBOX.md`
  actually becomes the bottleneck. Both files already hold good, hand-written
  content that no code reads; generating over them today would destroy real
  work rather than replace a real problem.
- **Loop 11B, the optional automatic-retrieval hook.** Not built. Stage A
  (the skill pulling rules on its own initiative, already shipped) has to be
  dogfooded first. A hook that pushes the wrong rule into every single prompt
  is worse than the current, opt-in retrieval, and this is explicitly gated
  on the real dogfood window (Loop 14a), not a technical blocker.

None of the three is abandoned. Each has a stated, checkable reopening
condition rather than a vague "later".

## Independent review: still open

`docs/NOT-FINALIZED.md` item 12 records that an independent second-model
adversarial re-audit of this project has never run. The privacy and security
work in Loop 12 (the scrubber fix and the withholding fix described above)
does **not** close that item: it was written and verified by the same model
family that built the feature it is reviewing, which is exactly the blind
spot an independent re-audit exists to catch. Item 12 stays open until a
different model family runs an adversarial pass against this system.

## Windows

Every claim about this system's behaviour on Windows comes from continuous
integration, never from a machine on this desk. There is no Windows machine
available to the people building this. Where CI is green on Windows, that is
what "supported" rests on; where a limit says "POSIX only" (recovered work
being owner-only, for example), it is because Windows uses access control
lists rather than POSIX file modes and this project does not yet set one.

## Replacing the old scorecard's theatre metrics

The pre-existing weekly scorecard (`RUBRIC.md` metric 1, "SELF-LEARNING") is a
founder-frozen template: `RUBRIC.md` says its own numbers change only by
founder decision, never by drift, so this document does not silently rewrite
it. What changed is the evidence available to score it against. Where the old
metric had no mechanical number behind it, `bm_learn.py loop-failures` and
`bm_learn.py rule-outcomes` now produce one, built from rows that exist in the
store rather than from a self-report:

- candidates captured, and founder approval/rejection counts (`candidates`,
  `bm_learn.py metrics`);
- repeated settled corrections, reported separately from rework and escaped
  defects, never folded together (`loop-failures`);
- retrieval misses, compliance failures, bad-rule candidates, and scope
  errors (`loop-failures`, four separate named counts, not one blended
  score);
- unresolved contradictions, rules never retrieved, and rules retrieved but
  always marked not relevant (`loop-failures`, `verify`);
- rework and escaped defects linked to a rule, with unattributed outcomes
  listed on their own line, never averaged into a rule's record
  (`loop-failures`);
- `NOT MEASURED` printed in place of any number the rows on hand cannot
  support, rather than a zero that would read as a clean result.

Any count this system cannot yet produce (a felt-outcome average with real
provenance, for instance) is not invented here. If you want `RUBRIC.md`
itself amended to point metric 1 at these commands, that is a founder
decision the rubric's own rule reserves to you; this document only makes the
evidence available.
