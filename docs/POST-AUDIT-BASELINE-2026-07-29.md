# Post-audit baseline, 2026-07-29 (Loop P0)

Every number below is tied to a command run on this machine on 2026-07-29, at the
commit named here, before any post-audit-plan code change. Historical documents
keep their own dated numbers; this file is the current truth at freeze time.

## Repository state

- Branch: v2, HEAD 8e015c7, working tree clean except the two files this loop
  adds (this baseline and the plan document).
  Command: git status -sb; git rev-parse --short HEAD
- Divergence: v2 is 70 commits ahead of origin/main, 0 behind. A fast-forward
  merge of v2 into main is possible.
  Command: git rev-list --left-right --count origin/main...HEAD -> "0 70"
- Default branch on GitHub: main. Consequence, confirmed: a visitor cloning the
  repository root today installs the OLD product, not V2. This is plan gap 1.
  Command: git ls-remote --symref https://github.com/khalilmaaouni/BrotherModeUp.git HEAD
  -> "ref: refs/heads/main"
- Tags, local and remote agree: v2.0.0-rc.1 = 7c2e0ec, v2.0.0-rc.2 = 2aef6a4.
  VERSION file: 2.0.0-rc.2. Neither tag points at current HEAD; rc.2 predates the
  correction-learning Phase D and E work.
  Commands: git tag -l; git ls-remote --tags; cat VERSION

## Test gate

- Full gate at 8e015c7:
  "test_all: 598 tests across 4 suites, 2 skipped, 539.7s wall. ALL GREEN", exit 0.
  Command: python3 tools/test_all.py
- Wall-time note: 539.7s against a usual ~60s because the gate ran concurrently
  with the CLI smoke and install verification below. Process lesson re-learned:
  give the gate the tree to itself, even for non-suite commands that import the
  repository's modules.

## CLI smoke path (throwaway store, scratchpad, git-init fixture)

All commands exit 0: bm_store.py init; bm_learn.py capture (release-note rule);
candidates; approve <id> --ref "baseline probe"; relevant --query "write the
release notes" returns the approved rule at rank 1 (mode=lexical, named);
learning-verify runs 9 checks, no findings, honest note that no FTS index exists.

## Install verification: FAILED, as the plan predicted

Command: HOME=<clean tmp home> bash scripts/verify-install.sh
Result: "100 file(s) match, 11 mismatched, 0 missing, 0 wrong type, 11 extra ...
verify-install: FAILED."
Cause, verified: CHECKSUMS.sha256 was generated at handover packaging time
(b2b352c); 12 commits have landed since, and docs/HANDOVER-2026-07-29.md plus the
Phase D and E changes are absent from or differ from the manifest. This is
manifest drift, not tampering, but the tool is correct to refuse trust. Fix owner:
Loop P1 regenerates the manifest at tag time; Loop P2 makes it part of every
release.

## Contradictions with current docs (auditor pass runs read-only after this freeze)

Known before the auditor runs:
- The repository root README (main branch) describes the pre-V2 product; plan
  gap 1, closed by Loop P1.
- CHECKSUMS.sha256 contradicts the working tree, above.
- docs/HANDOVER-2026-07-29.md carries dated counts (445 tests) that are
  historical, correctly dated, and must be marked historical per Loop P10 rather
  than updated.

## Founder decisions in force for this plan (2026-07-29, question windows)

1. Ship V2 as a release candidate now: Loop P1 executes; the STABLE claim still
   waits for dogfood (P13) and the independent audit (P14).
2. New loops ratified: P16 cross-runtime adapters, P17 packaging, P18 ecosystem
   launch kit, P19 external beta evidence. They run after P12.
3. Loop P3 approval model: Model A, one-time receipts minted by the founder's
   question-window answer.

## Out of scope for this freeze

No production code changed. NOT-FINALIZED.md is deliberately untouched in this
loop; status flips happen in the loops that earn them.
