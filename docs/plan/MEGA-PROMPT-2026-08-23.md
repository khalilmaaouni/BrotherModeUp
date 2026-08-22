Status: CURRENT. The coordinated session prompts for the three product lanes, written 2026-08-22 afternoon by the merger-analysis session (eab3d639) on the founder's instruction to restart the mega prompt as a replan that coordinates the three sessions toward one destination with the least rework. Three paste blocks below, one per lane; the contract above them binds all three. Roles only, no dashes. Supersedes the single-lane prompts where they conflict: this repository's pack 07, the sibling pack's NEXT-ROUND-PROMPT.md (now carrying a pointer here), BrotherDS's handover page (its next steps stand, its coordination section is this file).

# The coordinated mega prompts: three lanes, one destination

## THE DESTINATION, frozen (nobody re-opens these; every quote is the founder's, 2026-08-22, question UI, verbatim in docs/plan/ADR-2026-08-23-one-brother-repository.md)

"Merge them under Brother new repo". The umbrella EXISTS: `khalilmaaouni/Brother`, PUBLIC, Stage 0 at `1df838f`: a router marketplace (github sources pointing at the three home repositories; "Physical code stays in each product's own repository at Stage 0"), COORDINATION.md, a charter and a merge plan; its Stage 0 surface caps were withdrawn at `17ea4e0` on the ADR's own criteria (a nine-skill cut forces the renames the freeze forbids), and its test now requires COORDINATION.md to name docs/plan/ADR-2026-08-23-one-brother-repository.md as the architecture of record (verified at `90be2ea`). The shape: "B: one repository, three plugins under one marketplace, the Anthropic and ruflo shape", reached by stages: code moves INTO the umbrella by clean extraction when the gates hold, never by history merge. The harmony ("Find the right approach as Fable and handle a harmony between all functions to be seamless like Superpowers"): one entry point that routes, one vocabulary (the chain's stages, the verdict tuple, the assertion object with three subtypes), the seams as plumbing nobody touches; the passport survives the move as the internal module boundary, only the cross-repository ratification ceremony dies. Verified reality is occupied PER UNIT ("Split by unit, ledger owned by BrotherDS"): provenance answers whether the WORK was done as described, assurance whether a CHANGE worked in production, claims whether a NUMBER held; the human says whether it actually worked, and no computed rate replaces that answer. Movement gates (the umbrella's, plus the ADR's seven-condition table): one claim scored against a real outcome; the assurance product's open pull-request queue at zero; the amendment landed by the founder's hand.

## THE CONTRACT, binding every lane (the anti-rework rules, each bought once on 2026-08-22)

1. ONE WRITER PER TREE. Each lane writes ONLY in its own repository. A need in another tree is a MESSAGE to that lane (ListAgents, SendMessage), never an edit. Registry lanes before any write (`bin/sbe task open` in the assurance tree, `tools/bm_store.py claim` here; BrotherDS has no registry and runs one session at a time).
2. ONE BATTERY AT A TIME on this machine. Before launching any battery or full gate, check `pgrep -f "test_all.py|local-gates"` and message the other lanes; a battery launched into another's run measures the machine, not the tree.
3. ONE ASKER. Founder windows run from the BrotherModeUp lane only (the question UI, one window per decision, recommended option first); the other lanes send their questions there. He is never asked the same thing twice.
4. THE UMBRELLA COORDINATES, THE ADR DECIDES: read Brother's COORDINATION.md before adding any command, agent, hook, skill or state vocabulary anywhere, and the architecture of record is this repository's docs/plan/ADR-2026-08-23-one-brother-repository.md (the umbrella's own test enforces that COORDINATION.md names it). The front door ROUTES, it does not delete; phase 5 shrinks the combined surface by at least a third, measured before and after.
5. MEASURE, NEVER RELAY: a fact from another session is re-measured in the owning tree before it reaches a document (ls-remote in every verify block; the stale-tracking-ref and the relayed-decision classes both bit on 2026-08-22).
6. SCANS AND THE PUSH IN SEPARATE CALLS, five scans per range (secret patterns, assignment shapes, attribution, dashes, private terms over newly reachable blobs, plus the product's own history test where one exists); `cd` on its own line, never inside a backgrounded list; the manifest regenerated LAST in any commit that touches a tracked file; a battery's directory proven with `lsof -p <pid>` after launch.
7. NO-DATA is never a pass and never a block; a worker's green is a claim until the orchestrator re-runs the check in the main tree; every regenerated document is read for the tool's own failure vocabulary before a re-quote.
8. FOUNDER GATES everywhere: no tag, no Release object, no deletion, no repository created or made public, no plan or billing change, no Bitbucket seat, no credential typed (keys are placed by his hand: keychain service `openrouter` for the cross-family reads), no PRODUCT-DIRECTION edit, no workflow file with an automatic trigger.
9. BUDGET per session from ~/.claude/spend-guard.json; a raise only in his words with an `until`; never raise your own ceiling; stop at 70 percent context with the handover addressed to Khalil by name.
10. TIERS: Fable orchestrates, judges, designs and asks; writers sonnet effort high in pinned worktrees returning deltas; scouts haiku; opus only at gates the plan of record names, and only through a definition or a readjustment he gives in that session.

## BLOCK M: the BrotherModeUp orchestrator lane (paste into a fresh session at /Users/khalil.maaouni/Documents/BrotherModeUp)

---
Phase 1 and 2 of the replan in BrotherModeUp, coordinated per docs/plan/MEGA-PROMPT-2026-08-23.md (read its contract first). /brothermode /brothersbe

You are Fable and you ORCHESTRATE AND DESIGN ONLY. Writers sonnet effort high in pinned worktrees; scouts haiku; opus only where a definition pins it or the founder readjusts in his own words.

BUDGET: <Khalil writes the figure and expiry, for example "6,000,000 output tokens until 23:00 JST">; write it into ~/.claude/spend-guard.json as a RAISE with that until, measuring the rolling residue first; an unfilled line means the baseline and a stop at the brake.

READ FIRST: docs/handover/2026-08-22-merger-replan/07-NEXT-SESSION-PROMPT.md and 06-CLOSE-REPORT.md; docs/plan/ROADMAP-2026-08-23-REPLAN.md; docs/plan/ADR-2026-08-23-one-brother-repository.md; the umbrella's COORDINATION.md (gh api or a clone, read only); docs/plan/QUEUE.json.

VERIFY BEFORE ANY WORK (stop and reconcile on any mismatch): `python3 tools/bm_handover.py detect`; `git rev-parse --short HEAD && git ls-remote origin refs/heads/main | cut -c1-7` (equal); `python3 tools/bm_idle.py check`; in the sibling and BrotherDS, ls-remote against the local head, READ ONLY; `df -h / | tail -1` (above 15 GiB or clean before builds; under 8 refuse); check the live lanes with ListAgents and say who else is working.

THE ORDER, FINISH FIRST, one task per lane, two lanes at most:
1. M22 then M18 then M26 (scripts/migrate_install.py, tools/test_bm.py; the queue's own done_checks, red first, quoted), then M20, M31, M30 (M30's removal half is his gate). Full gate green at each landing sha (`BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py`, PO-1 recipe), manifest last, push through the five scans.
2. Second lane when free: MERGE-P3 here (docs/PASSPORT.md gains the read-only consumer sentence), MERGE-P5 here (the digest test), MERGE-P2/M13 (the registry recognition; name `python3 evals/test_no_data_class.py` in any brief touching the sibling's installed copy read-only), then the P18 design (the front door's routing table and the before-measurement of the surface; routing, not deletion; design only, nothing ships before the founder lands the freeze amendment).
3. Founder windows owed (one asker, this lane): the amendment text (in the vault's pending-amendments note, REVISED block); O23 the one fence owner (recommendation: BrotherMode owns it, per the parity map and the delivering session's design); the OpenRouter key placement; Codex credits; BrotherDS's claim path and boundary question (the boundary study's split recommendation); the weekly review (overdue).
4. CLOSE per the ceremony: skeleton, fill by hand, zip, verify-close with --session, commit the pack, manifest last, full gate, the five scans, push; the vault log and its push; the boards as files.
---

## BLOCK S: the BrotherSBE lane (paste into a fresh session at /Users/khalil.maaouni/Documents/BrotherSBE; the live session of 2026-08-22 afternoon adopts this by message)

---
Phase 1 of the replan in BrotherSBE, coordinated per BrotherModeUp docs/plan/MEGA-PROMPT-2026-08-23.md (read its contract first). /brothersbe /brothermode

You are Fable and you ORCHESTRATE ONLY; writers sonnet effort high in pinned worktrees under /Users/khalil.maaouni/Documents/BrotherSBE-worktrees/; every brief touching tools/*.py names `python3 evals/test_no_data_class.py` (must stay `0 failure(s)`).

BUDGET: <Khalil writes the figure and expiry>; the same raise rule as block M.

READ FIRST: .sbe/handover-eab3d639-merger/START-HERE.md and NEXT-ROUND-PROMPT.md; docs/plans/2026-08-23-roadmap-pointer.md and the roadmap it points at; the umbrella's COORDINATION.md; `python3 bin/sbe task list` (the merger session's five lanes are records of committed paths; adopt nothing without a disposition).

VERIFY: `git rev-parse --short HEAD && git ls-remote origin refs/heads/main | cut -c1-7` (equal; 0075655 at this file's writing); `git tag --list 'v3.3*'` (empty until the founder tags; PR 48 waits for the tag); `git status --porcelain --untracked-files=no` empty; `gh pr list --state open` (48 expected, plus whatever the day added: read each new one before touching anything); disk and ListAgents as in the contract.

THE ORDER:
1. If the founder has tagged v3.3.0: PR 48, his word "Merge it": one lane resolves its 26 commits against main, the battery green at the merge commit, the five scans, push. If no tag: skip and say so.
2. The review's rows S2 to S8 in the WBS order (BrotherModeUp docs/plan/OVERNIGHT-2026-08-22-TEAM-COMPLAINTS-WBS.md section 4a; S7 note: docs/BITBUCKET.md does not exist here, create it or point at docs/ADOPTION.md), each: lane open, red then green quoted by the writer, re-run by the orchestrator in the main tree, cherry-pick by sha.
3. MERGE-P4: contracts/handoff-package.v1.json (the five items: prepared dataset with grain, contract and snapshot id; evaluation harness with split; metric definitions by name and formula; labelled holdout with who and when; open questions) with one fixture and one test; then MERGE-P3's sibling half: the read-only consumer sentence in docs/specs/2026-08-15-change-passport-seam.md. Message the BrotherDS lane when both land so it drops its UNAUTHORISED cap.
4. MERGE-P16: scripts/local-gates.sh's TRUSTED_REF and workflow path become inputs read from the tree so a fresh extraction runs; the poll ceiling sized to three batteries; one receipt per plugin. This blocks every rehearsal; it is the merge's critical path in this repository.
5. Then S9 to S14, Q5 (one recommended next action per response), Q6 (`security find-generic-password -s bitbucket-api-token`; exit 44 is NO-DATA), the Band Z seal.
6. CLOSE in this repository's own convention: the pack under .sbe/handover-<session>/, first line FINISHED or UNFINISHED, one zip in /Users/khalil.maaouni/Documents/BrotherSBE-handovers/ diffed at zero difference, board refresh merged on top of 17, the vault log; pushes through the five scans with the posting battery (the ruleset requires the local-gates status on the exact head).
---

## BLOCK D: the BrotherDS lane (paste into a fresh session at /Users/khalil.maaouni/Documents/BrotherDS; the umbrella-holding session of 2026-08-22 adopts what it has not already done)

---
The replan in BrotherDS, coordinated per BrotherModeUp docs/plan/MEGA-PROMPT-2026-08-23.md (read its contract first). /brothersbe /brothermode

One session, one writer; the tree is small (26 tracked files). The interpreter for the engine is /usr/bin/python3 (duckdb lives there).

BUDGET: <Khalil writes the figure and expiry>; the same raise rule.

READ FIRST: docs/HANDOVER-2026-08-23-merger-replan.md; docs/ROADMAP-POINTER-2026-08-23.md; docs/ONE-PRODUCT-2026-08-22.md and docs/COORDINATED-PLAN-2026-08-22.md; the umbrella's COORDINATION.md and its GANTT; docs/plan/QUEUE.json here.

VERIFY: `git rev-parse --short HEAD && git ls-remote origin refs/heads/feature/north-star-chain-and-native-seam | cut -c1-7` (equal; 4cd4f3f at this file's writing); `gh pr view 1 --json state` (OPEN; its merge is the founder's); `/usr/bin/python3 bds.py selftest` (SELFTEST PASS); the private-terms grep over the tracked tree prints exactly the two known files or fewer.

THE ORDER:
1. FIRST-SCORED-CLAIM is the product's own gate and the umbrella's gate 1: register claims for the current pilot month NOW so an outcome can arrive within weeks (`bds.py register`; real data stays gitignored); everything else serves this.
2. MERGE-P7: VERSION, CHANGELOG.md, CHECKSUMS.sha256 and .claude-plugin/plugin.json (the queue item plugin-surface), with a verify-install equivalent, so the product carries the same release invariants as its siblings.
3. MERGE-P5's half here: a copy of the canonical passport fixture under examples/ with its sha256 (e6d68b76...) pinned in the selftest; run `bds.py passport` against it and quote the verdicts.
4. MERGE-P11's remainder: the research file whose NAME carries two terms is renamed and its 26 matches rewritten to roles; the scope directive's 4 matches are the founder's own words: prepare the role-worded diff and put it to him through the BrotherModeUp lane (one asker), never land it unshown.
5. When the sibling messages that P3 and P4 landed: drop the UNAUTHORISED cap on the passport reader and read the ratified handoff fixture; quote both greps and the verdicts.
6. CLOSE: a handover page under docs/ in this repository's convention, the board refreshed in the absolute structure, the vault session log, push the branch through the scans (PRIVATE repository: the secret scans and dashes still run; the terms grep must not grow).
---
