Status: CURRENT. Measured 2026-08-22 (JST 2026-08-23 morning is the replan's date) by the merger-analysis session, from the three trees at BrotherModeUp `e0d604e`, BrotherSBE `bddbc63`, BrotherDS `8840c2d`, and from the private vault. Every figure below was produced by a command run this session; a figure with no command beside it is not in this page. Roles only: no client, company or person name appears here, by the private-content law.

# The one Brother repository: the inventory of overlaps and seams

This page is the measured input to `docs/plan/ADR-2026-08-23-one-brother-repository.md`. One section per overlap or seam, each with the file paths on every side and the check that re-measures it. The sanitized copy is this file; the private copy (which may name files whose names carry client terms) lives in the vault under `10-Projects/brothermode/design/`.

## The three trees at a glance

| Product | Repository | Visibility | Tracked files | Version | Plugin manifest | Registry | Battery |
|---|---|---|---|---|---|---|---|
| BrotherMode (execution provenance) | BrotherModeUp | PUBLIC | 1192 | 3.3.2 | `.claude-plugin/plugin.json` name `brothermode`, marketplace lists 1 plugin | `.brothermode/store.sqlite3` rendered into STATE.md | `python3 tools/test_all.py`, 42 suites, plus `scripts/local-gates.sh` |
| BrotherSBE (assurance, the eight concerns) | BrotherSBE | PUBLIC | 755 | 3.3.0 | `.claude-plugin/plugin.json` name `brothersbe`, marketplace lists 1 plugin | `.sbe/tasks.json` (gitignored) | `scripts/local-gates.sh` extracting 52 commands from `.github/workflows/brothersbe-gates.yml`; `python3 evals/run_evals.py` 547 evals |
| BrotherDS (the claim, verified reality) | BrotherDS | PRIVATE | 26 at `8084340` (23 at `8840c2d`) | none | none (a skill directory `skills/brotherds`, MIT LICENSE, no plugin.json, no VERSION, no CHECKSUMS, no CHANGELOG) | none | `/usr/bin/python3 bds.py selftest` (SELFTEST PASS) |

Checks: `git ls-files | wc -l` in each tree; `cat VERSION`; `python3 -c "import json;print([p['name'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins']])"`; `gh repo view khalilmaaouni/<repo> --json visibility -q .visibility`.

## R1. The change passport (the seam itself)

- BrotherMode, producer: `tools/bm_passport.py` writes `<root>/.sbe/passport.json` and reads nothing under `.sbe/`; schema `schema/change-passport.v1.json` (`$id` `https://brothermode.dev/schema/change-passport.v1.json`, sha256 `280c5711...`); fixtures `schema/fixtures/` (one canonical, three invalid); validator `tools/bm_passport_validator.py` (stdlib, no jsonschema dependency); suite `tools/test_bm_passport.py`.
- BrotherSBE, consumer: `tools/sbe_passport.py --root DIR` reads `.sbe/tasks.json`, `.sbe/evidence/*.json` and the `.sbe/passport.json` deposit, nothing else; contract `docs/specs/2026-08-15-change-passport-seam.md`; fixture `tools/fixtures/change-passport.v1.canonical.json`, byte-identical to BrotherMode's (both sha256 `e6d68b76...`); suite `tools/test_sbe_passport.py` (110 tests at the night's close).
- BrotherDS, second reader: `bds.py passport` reads `<root>/.sbe/passport.json` only, applies the producer's hollow-value rule (absent is NO-DATA, padded is FAIL), and is UNAUTHORISED until the siblings answer REQUEST 1 in `docs/TRIUMVIRATE-INTEGRATION.md`. It holds no copy of the canonical fixture.
- Gap for the timing gate: conformance is proven on the same bytes for two of three sides. BrotherDS has never been run against the canonical fixture.
- Check: `shasum -a 256 BrotherModeUp/schema/fixtures/change-passport.v1.canonical.json BrotherSBE/tools/fixtures/change-passport.v1.canonical.json` (equal today); `python3 tools/test_bm_passport.py`; `python3 tools/test_sbe_passport.py`; `/usr/bin/python3 bds.py passport --help`.

## R2. The five-item handoff package (BrotherSBE to BrotherDS)

- Contracted 2026-08-11 in BrotherSBE `docs/specs/2026-08-11-analytics-partnership-design.md` lines 41 to 45: prepared dataset (grain, contract, snapshot id), evaluation harness (split), metric definitions (name, formula), labelled holdout (who, when), open questions.
- No code in BrotherSBE implements it: `grep -rln handoff src/brothersbe/*.py` prints nothing.
- BrotherDS `bds.py handoff` reads a proposed shape and caps its verdict at NO-DATA for any package lacking a `ratified` marker (REQUEST 2, unanswered).
- Check: the grep above; `/usr/bin/python3 bds.py handoff --help`.

## R3. The two one-writer registries and their hooks

- BrotherMode: `tools/bm_store.py` (sqlite store; verbs claim, park, checkpoint, complete, verify, handover-ack and more), `tools/bm_fence_hook.py` registered in `hooks/hooks.json` as PreToolUse on `Edit|Write|MultiEdit|NotebookEdit|Bash`, plus `tools/bm_bash_audit.py pre` and `tools/bm_session_cap.py` on Bash; STATE.md is the rendered view.
- BrotherSBE: `.sbe/tasks.json` through `sbe task open|close|list|fence|check`; `tools/sbe_fence_hook.py` and `tools/sbe_authority_hook.py` as PreToolUse on `Edit|Write|MultiEdit|NotebookEdit|CreateDirectory|Delete|apply_patch`; `tools/sbe_bash_write_guard.py` on Bash.
- BrotherDS: no registry, no hooks directory.
- With both plugins installed (this machine, today) every write runs both fence hooks against two registries that cannot recognise each other's owner. Queue here: M12 done (store claims render a fence line the installed sbe reconcile parses), M13 open (owner recognition, forecast 90 agent minutes), O23 open (the parity map's first decision: retire `sbe_fence_hook.py` behind `bm_fence_hook.py`, forecast 90). Parity map: `docs/plan/PARITY-READ-2026-08-15.md`.
- Check: `python3 tools/bm_store.py verify`; `python3 bin/sbe task list`; `python3 tools/sbe_fence_hook.py fences | grep -c "no readable"` (15 at the last measure, 2026-08-22).

## R4. The two ceremonies

- BrotherMode: `tools/bm_handover.py` (detect, owed, skeleton, zip, verify-close) generating the eight pack files 00 to 07 under `docs/handover/<date>-<name>/`, zipped beside the repository; verify-close refuses a hollow pack, a missing FINISHED or UNFINISHED line, a stale zip and unparked records.
- BrotherSBE: a hand convention, `.sbe/handover-<session>/` with START-HERE, CLOSE-REPORT and NEXT-ROUND-PROMPT, zipped to a handovers folder beside the repository and diffed at zero difference; five packs exist; the checks are applied by hand. Separately `sbe handover` (`src/brothersbe/handover.py`, `12-handover.json`) hands one change between two named people, a different object.
- BrotherDS: a page under `docs/` per session, no tool.
- Check: `python3 tools/bm_handover.py detect`; `ls -d .sbe/handover-*` in the sibling.

## R5. The two batteries and the third selftest

- BrotherMode: `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py` (42 suites, 8 to 13 minutes; last full green 3480 tests over 42 suites on 2026-08-21) and `scripts/local-gates.sh`, which runs that battery and posts a commit status through the host-aware `tools/bm_bbstatus.py`.
- BrotherSBE: `scripts/local-gates.sh --no-post` extracting the 52 commands of the dormant workflow file, signing a receipt under `evidence/gates/<sha>.txt`; `python3 evals/run_evals.py` (547 evals); `python3 evals/test_no_data_class.py` (the honesty meta-test, 0 failures required); `python3 tools/test_sbe.py` (130 tests including the private-name tracked-tree and history tests).
- BrotherDS: `/usr/bin/python3 bds.py selftest` (56 assertions; the interpreter matters because duckdb is installed under the system python only).
- Both batteries read their command list from a workflow file that GitHub Actions never runs (disabled estate-wide since 2026-08-16). Both already refuse a dirty tree and both bind a verdict to one sha.
- Check: the commands above, each quoted with its sha.

## R6. Manifests and release invariants

- BrotherMode: `CHECKSUMS.sha256` (1191 lines, regenerated LAST by `sh scripts/checksums.sh CHECKSUMS.sha256`, checked by `scripts/verify-install.sh` and doctor check 9), `VERSION` 3.3.2, `CHANGELOG.md` rule 1 (the annotated tag sits on the one commit that carries the VERSION move), `scripts/release-smoke-install.sh`, `scripts/doctor.py` (15 check functions).
- BrotherSBE: `CHECKSUMS.sha256` (754 lines, same regenerate-last rule), `VERSION` 3.3.0, `python3 tools/sbe_release_invariant.py --strict` (VERSION must move in any range that changes a distributable file), `python3 bin/sbe book --check --strict` (booklet drift, 7 sections), `DIGEST.md` header carries the version, `bin/sbe doctor` (14 checks including hooks-wiring).
- BrotherDS: none of the above. Its queue item `plugin-surface` is where a manifest would enter.
- Lesson already paid in both trees, recorded in the vault: a manifest regenerated last is only last until the next commit. This session found the sibling's manifest stale by exactly the two documents committed after its last regeneration, and regenerated it as `bddbc63`.
- Check: `sh scripts/verify-install.sh CHECKSUMS.sha256 .` in each plugin tree; `python3 tools/sbe_release_invariant.py --strict` in the sibling.

## R7. Vault protocols and telemetry

- BrotherMode: `references/memory.md` (the Kay Vault protocol the session hooks inject); `tools/bm_telemetry.py` writes `outcomes.jsonl`; weekly review `tools/WEEKLY-REVIEW.md` against the rubric (overdue 9 days at this session's start).
- BrotherSBE: `memory-template/` (10-Projects, 50-Reference, LEARNED.md, TEAM-VAULT.md) shipped for adopters; a runtime vault of its own through `BROTHERSBE_VAULT`; `tools/sbe_telemetry.py`; and one test in `tools/test_sbe.py` that opens the INSTALLED BrotherMode telemetry tool to assert both products write the same key, skipping as NO-DATA when the sibling is not installed.
- BrotherDS: no protocol file; five documents mention the vault.
- The private vault holds three spaces (brothermode, brothersbe, brotherds). BrotherDS's own decision 6 asks whether its space should exist and where.
- Check: `ls references/memory.md`; `ls memory-template/`; `grep -rl -i vault --include=*.md .` in BrotherDS.

## R8. Boards and their generators

- BrotherMode: `docs/plan/GANTT.html`, judged by `tools/bm_progress_check.py` and rendered through `tools/bm_visual.py`; the pack carries a copy and `bm_handover.py` checks the copy matches.
- BrotherSBE: `GANTT.html` at the root, refresh 16, hand-built by each session, no generator (`grep -l GANTT tools/*.py bin/*` prints nothing).
- BrotherDS: `GANTT.html` at the root, stamped 2026-08-16 night two, hand-built.
- All three stable links are account-bound; every close delivers the file.
- Check: `grep -i refresh GANTT.html | head -1` in each tree.

## R9. Documents and books

- BrotherMode: `docs/book/` (5 files, the solo builder booklet in two languages), `PRODUCT-DIRECTION.md` (founder-owned authority), `docs/NORTH-STAR-CHAIN.md`, the plan pages under `docs/plan/`.
- BrotherSBE: `docs/book/` (23 files, 15 chapters regenerated by `python3 bin/sbe book`), `docs/guides/`, `NORTH-STAR.md`, `docs/INTEROPERABILITY.md` (whose section count a test derives), `SKILL.md` under 18,000 bytes by test.
- BrotherDS: `docs/` (6 files) and `research/` (6 files), `SPEC.md`, `OPTIONS.md`.
- Check: `ls docs/book | wc -l` in each tree.

## R10. Name collisions, measured

- `tools/*.py`: zero collisions. BrotherMode tools carry the `bm_` prefix (45 of 94 entries; 43 `test_`; 6 other), BrotherSBE the `sbe_` prefix (33 of 117; 78 `test_`; 6 other). Shared basenames: `tools/WEEKLY-REVIEW.md` in both, and `__pycache__`.
- Skills: five names collide between the two plugins: `help`, `next`, `review`, `start`, `status` (BrotherMode ships 19 skill directories, BrotherSBE 16). Under one plugin manifest these five would need renaming or nesting, which is a new public surface under the tool-surface freeze; under separate plugin manifests they stay namespaced (`/brothermode:start`, `/brothersbe:start`).
- Agents: no collisions (5 against 8). Hooks: both manifests register SessionStart, PreToolUse, Stop, SessionEnd and PreCompact; BrotherMode also PostToolUse. One manifest would have to merge them; two manifests already coexist on this machine.
- BrotherDS: `bds.py` at the root with verbs new, check, receipt, register, score, ledger, chain, stage, passport, handoff; one skill `brotherds`; no collision with either sibling.
- Check: `comm -12 <(ls A/tools | sort) <(ls B/tools | sort)`; `comm -12 <(ls A/skills | sort) <(ls B/skills | sort)`.

## R11. Bitbucket parity per product

- BrotherMode: `bitbucket-pipelines.yml` at the root (88 lines), `docs/BITBUCKET.md` (CURRENT: the engine speaks plain git, `ls-remote` proven against a public Bitbucket repository on 2026-08-15, the pipeline itself UNVERIFIED), `tools/bm_bbstatus.py` for status posting.
- BrotherSBE: `bitbucket-pipelines.yml` at the root (24 lines) and `ci/bitbucket-pipelines.yml` (171 lines, never executed on a real workspace); `src/brothersbe/bbprverify.py`, `bbstatus.py`, `prverify.py`; the approval gate proven PASS on a fresh clone from Bitbucket (`docs/plans/2026-08-18-bitbucket-parity-remaining.md`). `docs/BITBUCKET.md` does NOT exist in the sibling, although the overnight WBS row S7 names it; S7 must create it or point at `docs/ADOPTION.md`.
- BrotherDS: nothing.
- Both legs wait on the same two founder-held facts: the keychain item `bitbucket-api-token` (absent at every check since 2026-08-18) and the test workspace's seat limit. Status posting exists twice (`bm_bbstatus.py` and `bbstatus.py`), one per product.
- Check: `security find-generic-password -s bitbucket-api-token` (exit 44 means absent); `ls bitbucket-pipelines.yml ci/bitbucket-pipelines.yml`.

## R12. Private-content status, and what each tree needs before a clean extraction

- BrotherMode, PUBLIC: the tracked tree passes the delivery scans; the full LOCAL history still carries 278 lines matching the private-terms list (`git log -p --all | grep -icF -f <list>`), and the remote still serves 44 pull-request refs that anchor a file and identifiers removed on 2026-08-18 (founder decision that day: accepted as a known gap; flip condition: the repository is named for extraction). Before extraction: nothing in the tree, because extraction takes the tree at a commit and leaves the history behind.
- BrotherSBE, PUBLIC: the tracked tree passes; the publishable history carries seven hits on five already-public blobs, WAIVED by id through the tracked `.sbe-private-history-acceptance.json` (founder decision 2026-08-22, accept and record; flip condition: a third exposure). Before extraction: nothing in the tree.
- BrotherDS, PRIVATE: at `8840c2d` (the local head when this page was first measured) 104 matches across 9 of its 23 tracked files (`git grep -c -i -F -f <list>`); at `8084340`, the remote head fast-forwarded to later the same session (last night's commit "The design documents stop naming the two estates"), 30 matches in 2 files: the research file whose NAME carries two terms (26) and the founder's scope directive (4). Plus gitignored claims and receipts holding real pilot data. Before any public tree: those two files rewritten or renamed, the real claims kept out, and then a clean extraction of the rewritten tree, because its history holds the names whatever the tree says. Lesson paid here: the session verified BrotherDS against a stale tracking ref instead of `git ls-remote`; the remote was five commits ahead.
- The law this page obeys: a merged public repository is a CLEAN EXTRACTION of each tree at a chosen commit, never a history merge and never a scrub; a repository that ever held the content still holds it in its objects (vault precedent: a clone that still holds the objects you deleted).
- Check: the two greps above, each over the target tree, with the list read from outside every repository.

## R13. Who owns the chain's verified-reality stage

- The chain (`docs/NORTH-STAR-CHAIN.md`) gives the stage three columns: BrotherMode "should record the outcome (does not yet)", BrotherSBE "should compare outcome against tier (does not yet)", and the human "says whether it actually worked" (the column that may never be automated away); its status table records the stage as DOES NOT EXIST. The claim product's own page reads that as "owned by nobody", which drops the human column.
- Measured today, three partial implementations exist: BrotherMode `tools/bm_reality.py` (accept a release, enter reopened, rolled-back or incident, linked to a queue item; landed 2026-08-20), BrotherSBE `src/brothersbe/lifecycle.py` `reduce_verified_reality` (zero callers outside its test; H5 partial), BrotherDS `bds.py score` and `ledger` (the Verified Claim Rate, the only metric in the family that reports whether reality agreed, NO-DATA until a claim resolves).
- A standing founder decision binds the answer: N2 (2026-08-15, BrotherSBE) says the whole end of the chain, release readiness, production observation and verified reality, gets built on the assurance side. BrotherDS's proposal (its decision 3) is therefore a question of UNIT, not of replacing N2: a change's verified reality is the assurance product's; a claim's verified reality is BrotherDS's; the execution record stays with BrotherMode.
- Check: `python3 tools/bm_reality.py --help`; `grep -n "def reduce_verified_reality" src/brothersbe/lifecycle.py`; `/usr/bin/python3 bds.py ledger --help`.

## R14. Install paths and doctors, as the team meets them

- BrotherMode: `claude plugin marketplace add khalilmaaouni/BrotherModeUp`, `claude plugin install brothermode@brothermode-marketplace` (the marketplace is named `brothermode-marketplace` in `.claude-plugin/marketplace.json`; corrected after the gate of 2026-08-22), `python3 scripts/doctor.py`.
- BrotherSBE: `claude plugin marketplace add khalilmaaouni/BrotherSBE`, `claude plugin install brothersbe@brothersbe`, `bin/sbe doctor`.
- BrotherDS: not installable as a plugin today; the skill directory is copied by hand.
- Two marketplace adds and two installs today, three with BrotherDS. The team installs BrotherSBE alone; nothing forces BrotherMode beside it, and the no-dependency law says nothing may.

## R15. Dormant CI files that still serve as command sources

- BrotherMode `.github/workflows/tests.yml`; BrotherSBE `.github/workflows/brothersbe-gates.yml`, `consumer-check.yml`, `scorecard.yml`. Actions is disabled; both `local-gates.sh` scripts parse these files for the command list. A merged repository keeps one such file per product or one file that extracts all three; either way nothing self-fires (cloud-cost floor, enforced by `~/.claude/hooks/github_cost_wall.py`).
