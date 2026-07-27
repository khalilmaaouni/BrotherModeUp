# MANIFEST-extraction.md

Mechanical extraction of SKILL.md sections 1 to 15 into references/*.md, verbatim.
Section 0 (Invocation sequence) stays in SKILL.md; it was not part of this task.

## Reference files

| Target path | Source sections | Lines (body) | Approx tokens (chars / 4) | LOAD WHEN |
|---|---|---|---|---|
| references/profiles.md | 1, 2 | 48 | 905 | LOAD WHEN: work is being classified at the start of a task, to pick its work-nature profile and assign hats. |
| references/delegation.md | 3, 4 | 79 | 1511 | LOAD WHEN: deciding whether to delegate to an agent or fleet, picking a model tier, or setting a token budget for a phase or agent. |
| references/fences.md | 5 | 38 | 736 | LOAD WHEN: a writing agent is about to be dispatched, or files could be touched by more than one writer at once. |
| references/research.md | 6 | 14 | 237 | LOAD WHEN: a decision-carrying question needs research, or a fact must be verified before it can be trusted. |
| references/solutioning.md | 7 | 19 | 359 | LOAD WHEN: work has been classified COMPLEX, or more than one plausible approach exists. |
| references/improvement.md | 8 | 100 | 1984 | LOAD WHEN: a loop is closing and needs scoring, or a correction, taste signal, or calibration result has just arrived. |
| references/context.md | 9 | 17 | 304 | LOAD WHEN: the orchestrator's context is filling up, or a compaction or resume has just happened. |
| references/honesty.md | 10 | 20 | 341 | LOAD WHEN: bad news needs reporting, a claim needs a calibrated confidence label, or the founder's ask conflicts with the evidence, the personas, or a prior decision. |
| references/machine.md | 11 | 40 | 709 | LOAD WHEN: the machine (Xcode, simulators, browsers, GUI apps) is about to be driven directly, or a founder-gated action (credentials, releases, destructive operations) is in view. |
| references/memory.md | 12 | 17 | 322 | LOAD WHEN: the vault needs reading before work starts, or writing at a milestone or session close. |
| references/mistakes.md | 13 | 28 | 511 | LOAD WHEN: before repeating a pattern that has failed before, such as dispatching writers, resuming after a kill, or running a build. |
| references/founder-model.md | 14 | 35 | 682 | LOAD WHEN: a recommendation is being formed, a prediction needs sealing, or the founder's voice is being drafted in or learned from. |
| references/scoring.md | 15 | 22 | 420 | LOAD WHEN: a session is closing, or a scorecard is being written. |

"Lines (body)" counts only the verbatim SKILL.md text (the `## N.` heading through the
last line before the next heading, or end of file for section 15). It excludes the
added `# Title`, `LOAD WHEN`, and pointer-back line in each file. "Approx tokens" is
the verbatim body's character count divided by 4, matching the design doc's stated
method. Every file's body starts with the original `## N. <heading text>` line
unchanged, so the section numbering from SKILL.md is preserved inside each file.

## Cross-references noted (not rewritten)

- references/fences.md (section 5), the sentence "return contracts per the section 4
  hard cap so noise dies at the boundary": section 4 (token budgets) now lives in
  references/delegation.md. Left as-is per the task rule; the router author needs to
  resolve this pointer (either link to delegation.md or ensure delegation.md is
  loaded alongside fences.md).
- No other numeric cross-references ("section N" / "sections N to M") were found
  inside sections 1 to 15. All other such references (sections 0's mentions of
  section 1, 2, 6, 7, 12, 14, and "sections 3 to 14") live in SKILL.md's own
  Invocation sequence (section 0), which was not extracted and is out of this
  task's fence.

## Verification (rule 3: nothing lost)

Method: concatenate the verbatim bodies of all 13 reference files (excluding the
added title/LOAD WHEN/pointer lines) in section order, and compare character-for-
character against the concatenation of the corresponding SKILL.md line ranges
(sections 1 through 15, lines 58 to 534).

- Concatenated reference-file bodies: 36102 characters
- Concatenated SKILL.md sections 1 to 15 (lines 58 to 534): 36102 characters
- Difference: 0 characters
- Result: MATCH (exact, verified by direct string comparison, not by eyeballing)

Per-file source line ranges used for the comparison (1-indexed, inclusive, from
`grep -n "^## " SKILL.md`):

- profiles.md: SKILL.md lines 58 to 105 (section 1 starts 58, section 2 starts 98, section 3 starts 106)
- delegation.md: SKILL.md lines 106 to 184 (section 3 starts 106, section 4 starts 161, section 5 starts 185)
- fences.md: SKILL.md lines 185 to 222 (section 6 starts 223)
- research.md: SKILL.md lines 223 to 236 (section 7 starts 237)
- solutioning.md: SKILL.md lines 237 to 255 (section 8 starts 256)
- improvement.md: SKILL.md lines 256 to 355 (section 9 starts 356)
- context.md: SKILL.md lines 356 to 372 (section 10 starts 373)
- honesty.md: SKILL.md lines 373 to 392 (section 11 starts 393)
- machine.md: SKILL.md lines 393 to 432 (section 12 starts 433)
- memory.md: SKILL.md lines 433 to 449 (section 13 starts 450)
- mistakes.md: SKILL.md lines 450 to 477 (section 14 starts 478)
- founder-model.md: SKILL.md lines 478 to 512 (section 15 starts 513)
- scoring.md: SKILL.md lines 513 to 534 (end of file)

Extraction and comparison were done mechanically (a small Python script reading
exact line ranges from SKILL.md and comparing string equality), not by hand-copying
or eyeballing text, per the task's precision requirement.
