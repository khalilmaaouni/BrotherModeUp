# Fold-ins inherited from session eab3d639 (brothermodeup-37), 2026-08-22 evening
Apply at the NEXT commit that touches the plan documents; do not make them their own commit.

## 1. MERGE-P16 rescope (author-confirmed intent)
The "poll ceiling sized to three batteries" and "one receipt per plugin" words belong to
MERGE-M2 (merged repository root runner plus its session-side polling recipe), NOT to P16.
scripts/local-gates.sh has no polling loop and its MAXLOAD guard is not raised; one battery
at a time stands.
- docs/plan/ADR-2026-08-23-one-brother-repository.md, P16 row: drop the poll-ceiling and
  one-receipt-per-plugin words, move them into the M2 step description.
- docs/plan/ROADMAP-2026-08-23-REPLAN.md, P16 row: same.
- P16 keeps only the two ladders: workflow path resolved plugin-local then root with a
  refusal naming both; trust anchor a fixed ladder never caller-supplied, fresh-extraction
  case running UNANCHORED at POST=0.
- docs/plan/QUEUE.json MERGE-P16 done_check: drop "the root runner's poll loop outlasts the
  sum of the three measured runtimes, quoted"; gain "the receipt records which workflow
  candidate resolved and battery_from UNANCHORED when no remote-tracking ref exists".

## 2. Actions switch reading before any workflow file moves
Founder ruled the workflow divergence for the ADR's reading: allow the directory, forbid
anything that can fire. The umbrella (khalilmaaouni/Brother) had Actions ENABLED at creation
(allowed_actions all, zero workflow files so nothing fired); founder disabled it within the
hour; all three repositories now read enabled=false.
- Add one line to the ADR's migration steps (M2 or M4) and to the roadmap's phase 4: before
  moving any workflow file into the destination repository, read its Actions switch
  (`gh api repos/<owner>/<repo>/actions/permissions`, expect enabled false) and record the
  reading. The files were safe; the switch was the gap.

## 3. Tree handoff facts
- eab3d639 closed and pushed at 96383a1 (gate ALL GREEN over 3486 tests, five scans clean,
  verify-close PASS on docs/handover/2026-08-22-merger-replan). Read-only from here.
- QUEUE.json, GANTT.html, CHECKSUMS.sha256 and the plan documents are UNOWNED and claimable.
- Its declaration lane merger-replan-docs-eab3d639 was force-closed with a disposition.
  Watch for ~13 other dead lanes in the local sbe registry from 2026-08-21 and earlier; the
  recovery that works is a forced close with an adoption disposition.
- Owed to the founder: the felt-outcome ask (1 to 5) and the weekly review (overdue).
- This lane now holds the one-asker role for this repository.

## 4. Contract rule 11 for docs/plan/MEGA-PROMPT-2026-08-23.md (fold-in 4, eab3d639)
Add as rule 11 in THE CONTRACT section, wording trimmable:

"11. THE CROSS-FAMILY MODEL (stealth/ox-alpha via OpenRouter, the founder's standing
instruction to leverage it): free, 1M context, tools supported, 19 tokens per second, and
PROMPTS AND COMPLETIONS ARE RETAINED by an anonymous third-party provider. Therefore:
content from the two public repositories and the umbrella ONLY; NEVER BrotherDS (private,
carries client terms), the vault, client estates, personal data, credentials, or the
private-terms list file itself; the key is placed by the founder's own hand (keychain
service openrouter) and read by name, never typed by a session and never printed; its slot
is the cross-family refutation read Codex left NO-DATA (secondary and verification reads,
re-verified in the main tree before anything acts on them, per the standing cheap-lane law);
at 19 tokens per second it runs detached with a sentinel, never awaited inline."

Boundary refinements inside that rule:
- Unpushed work in the PUBLIC repositories may be sent only when it is on its way through
  the gates to public anyway.
- Handover material naming machine internals stays out.
- The retention caveat goes in front of the founder ONCE (next question window or close-out):
  "leverage as much as possible" was said before the retention term was measured, and his
  standing laws make that trade his to confirm.

Measured facts behind the rule (openrouter.ai/stealth/ox-alpha, read 2026-08-22 19:2x JST):
free 0 in / 0 out, ctx 1,048,576, max completion 131,072, text+image+video in,
supported params include tools, reasoning_effort, response_format; 19 tok/s, 7.45s latency
P50; anonymous third-party provider, prompts and completions retained, not used for training.
Bridge: ~/.claude/bin/or_ask.py (reads keychain service `openrouter`, exit 44 on no key).

### Rule 11 strictenings (from brotherds-b1, adopted verbatim)
- "Not used for training" is NOT "not retained". Two different promises; the weaker one is the
  one that was made. An anonymous operator cannot be assessed, audited, or asked to delete
  anything, so retention is the whole risk regardless of what it is not used for.
- Eligibility follows what a repository IS, not what it is planned to become. Private content
  becomes eligible only once actually public, never on the strength of a plan to separate its
  context. The window between "we intend to publish" and "we published" is when the leak happens.
- Framing that makes it enforceable: sending content to a retaining anonymous third party IS a
  form of publishing it, so it falls under the existing NO PRIVATE CONTENT IN PUBLIC law rather
  than needing a new one. Nothing goes through the lane that could not be published today.

### CREDENTIAL PATH COLLISION, open, founder decision (found 2026-08-22 19:3x JST)
- ~/.claude/CLAUDE.md section "OpenRouter, the second lane" (written 17:21 by session
  brotherds-b1) names `~/.openrouter.key`, mode 600, read as `$(cat ~/.openrouter.key)`.
- docs/plan/MEGA-PROMPT-2026-08-23.md contract rule 8 names keychain service `openrouter`.
  ~/.claude/bin/or_ask.py reads the keychain.
- Neither was written by the founder. Two paths on one machine; his call. Recommendation:
  keychain (a 600 file is still plaintext any session can cat and any grep can find).
- MEASURED: ~/.openrouter.key exists, mode 600, 19 characters, does NOT begin `sk-or-v1`,
  dated 2026-08-22 11:43. That path returns NO-DATA today, correctly refused by its own guard.
  Keychain item absent, bridge returns exit 44. THE LANE IS NOT LIVE FOR ANY SESSION.

### KEY EXPOSURE, measured, rotation recommended to the founder
- One distinct key, 73 characters (its fingerprint is deliberately NOT recorded here: this
  repository is public, and a credential fingerprint is credential metadata). 72 occurrences across 10
  transcript and session files in five project directories: BrotherModeUp (2), BrotherSBE (2),
  BrotherDS (1), Tonari (3), slop-gate session state (2).
- Persistence property of how the harness records sessions, not a session's mistake.
  NOT scrubbable by any session; no session edits transcripts. Rotation is the fix and it is
  the founder's hand.

## 5. Passport consumer ordinal: SECOND, not third (brothersbe-ca, 2026-08-22 evening)
The merger pack says the claim product is the SECOND read-only consumer of the passport; the
sibling's companion handover says THIRD. SECOND is right: the seam spec's own opening names one
producer and one consumer (the assurance repository), so the claim product is the second.
Correct any "third" wording in the ADR or the roadmap when next in those files.

## 6. Release-blocking subset finding (BrotherSBE lane, CORRECTED and measured)
SUPERSEDES the earlier draft numbers. Source of record: the sibling repository's
docs/plans/2026-08-23-release-blocking-subset.md at commit 9a8f848. Cite that path,
never a scratchpad path.

- 83 test files, not 82 (79 under tools/test_*.py plus 4 under evals/), all anchoring on
  `__file__`. The first count was misread and recounted explicitly.
- 12 of 13 shell scripts are self locating. The suite therefore travels with the plugin at
  no cost, so almost nothing in rows S2 to S14 is cheaper before the move than after.
- TWO CANDIDATE FINDINGS WERE CHECKED AND DISCARDED AS FALSE, and they travel with the
  claim because without them it reads sloppier than it is: eight modules under src read the
  working directory, which looks like move fragility and is the deliberate shared --cwd
  mechanism for operating on a caller's repository; and the one shell script that is not
  self locating reads no repository file at all, it calls a REST API.
- THE LIMIT TRAVELS WITH THE CLAIM, and a version without this sentence is an overclaim:
  it measures PATH RESOLUTION only. It does not prove the plugin installs from a
  subdirectory of a multi-plugin repository, and it does not prove three plugins share one
  contracts directory without collision. Both stay rehearsal questions.
- MERGE-P16 IS DONE at the sibling's main 2acd700, so "the gate runner gets more expensive
  after the move" is PAST TENSE. Calibrated in a throwaway checkout with no git remote: the
  fixed runner announces UNANCHORED, forces posting off, runs all 52 commands from the
  working tree and signs its receipt, while the pre-P16 runner in that same tree prints
  "REFUSED: cannot read .github/workflows/brothersbe-gates.yml from origin/main" and exits 2.
- CONSEQUENCE for the ADR: only pull request 48 remains genuinely more expensive after the
  move, so "finished" should not be defined as an empty backlog and the timing gate can read
  green far earlier than the roadmap implies.

### The lesson worth more than the incident
Running that extraction rehearsal exposed FOUR regressions in the sibling's own tree that
every narrower check had passed: one added file under tools/ moved counts that shipped
documents quote verbatim. `python3 evals/run_evals.py` prints
`547 evals: 543 passed, 4 regressions` (three are count drift in two docs and SKILL.md,
under repair; the fourth is the manifest, red by design until regenerated LAST).
A rehearsal held before a merge paid for itself on a defect that had nothing to do with the
merge.

### Mutation-proof technique worth reusing here
An in-place mutation of a tracked file cannot reach the code under test in these repositories,
because the dirty-tree guard fires first. The sibling's mutation proofs therefore COMMIT the
mutation, run, then reset, inside a disposable worktree rather than the shared tree. That is
the shape any M26 mutation proof in this repository has to take.
