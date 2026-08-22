Status: DECIDED by the founder on 2026-08-22 in the question UI (round four: a NEW repository named Brother, the harmony layer delegated to the strongest tier and designed below; round one: BrotherDS separates and goes public first, the amendment lands by his hand; round three: Option B, the reality owner split by unit with the ledger at BrotherDS, one vault space proposed at the merge, one manual Bitbucket pipeline); his words are recorded verbatim in the two founder sections below. Written 2026-08-22 (dated for the 2026-08-23 replan) by the merger-analysis session from docs/plan/MERGER-INVENTORY-2026-08-23.md. Roles only, no dashes, nothing in PRODUCT-DIRECTION.md is edited by this page: its amendment is a PROPOSED block at the end.

# ADR: the one Brother repository

Serves the CHANGE PASSPORT stage of the chain (the seam is what a merger either protects or breaks) and the founder's north star of 2026-08-22: one Brother repository holding the three products, merged at the right time, not now; first the backlog finished properly, meanwhile each repository prepared so the merge is a move, not a rewrite.

## Context

Three products, three repositories, three plugins, measured in the inventory: BrotherMode (BrotherModeUp, PUBLIC, 1192 tracked files, plugin `brothermode` 3.3.2), BrotherSBE (BrotherSBE, PUBLIC, 755 files, plugin `brothersbe` 3.3.0), BrotherDS (BrotherDS, PRIVATE, 23 files, a skill with no plugin manifest, MIT). They meet at exactly two documents travelling one way: the change passport (BrotherMode produces, BrotherSBE consumes, BrotherDS asks to read) and the five-item handoff package (BrotherSBE to BrotherDS, content contracted, wire format unratified). They duplicate five things: a one-writer registry with its hooks, a handover ceremony, a gate battery, a manifest with release invariants, a board with its generator. Five skill names collide (`help`, `next`, `review`, `start`, `status`); no tool file name collides. Both public histories carry accepted private objects; the private tree carried 104 client-term matches in 9 files at `8840c2d` and carries 30 in 2 files at `8084340`, its remote head, after last night's de-naming commit (found when the checkout was fast-forwarded; the earlier figure came from a stale tracking ref, a verification miss of this session). GitHub Actions is off estate-wide; every gate runs locally; Bitbucket parity is manual under a 50 minute monthly budget.

The laws no option may weaken: PRODUCT-DIRECTION.md is founder-owned, so the merge enters it as a PROPOSED amendment he lands; a merged public repository is a CLEAN EXTRACTION of each tree at a chosen commit, never a history merge and never a scrub; no plugin is a dependency of another, and with nothing else installed each product fills its stage properly; the passport is the seam, not a schema; the tool surface is frozen until the four user journeys pass; every development works on GitHub (main) and Bitbucket (parity); nothing self-fires in CI.

Verified against the host's own documentation this session (code.claude.com, plugin-marketplaces, plugins and plugins-reference pages): one `marketplace.json` may list several plugins whose sources are relative paths inside the same repository ("Local directory within the marketplace repo. Must start with `./`"); a user installs one of them by name (`claude plugin install <plugin>@<marketplace>`) without the others; each plugin keeps its own `.claude-plugin/plugin.json`, `hooks/`, `skills/` and `agents/` at its own root; skills are always namespaced by plugin name ("to prevent conflicts when multiple plugins have skills with the same name"); marketplace plugins are copied into the plugin cache, so `CLAUDE_PLUGIN_ROOT` is the cached copy of that plugin's directory alone, never the repository root.

## Criteria

Each criterion is scored 0, 1 or 2 from the inventory's measurements, and the evidence is named.

| # | Criterion, measurable | What 2 means |
|---|---|---|
| C1 | The team's install path | one marketplace add, one install per product a person actually wants, one doctor |
| C2 | History and privacy under the clean-extraction law | no leaked history carried into the result; the private tree can join a public one after its own rewrite |
| C3 | The no-dependency law | each product installable alone, whole, with nothing else installed; no product's hooks run because another was wanted |
| C4 | The frozen tool surface | no skill or command renamed, no new public command |
| C5 | One battery, one ceremony, one registry | the shape makes convergence the default rather than an aspiration |
| C6 | Bitbucket parity cost under the free plan | one manual pipeline, one deliberate run proving all products |
| C7 | Release cadence | products can move at their own pace without a bump that is noise for the others |
| C8 | The reviewers' reading (the buyer is the reviewer) | one story to read, one place to look |
| C9 | Gate cost and coupling | the merged battery fits the poll ceiling the recipe already has, and one product's red run does not block another's release |

Method note, stated on the page rather than implied: no decision table for repository consolidation exists in the assurance product's tables (only the architecture shape table), so this table is hand-built with equal weights under human review, which is what the assurance product's L12 calls it.

## Options considered

### Option A (rejected): one repository, one plugin manifest exposing the three skills

One repository named Brother, created by clean extraction of the three trees at named commits, laid out as one package per product (mode, sbe, ds) plus shared `contracts/` and `schema/`, with ONE `.claude-plugin/plugin.json` whose skills are the three products; the three old repositories archived read-only with README pointers, never deleted.

Rejected because one manifest makes the three products one install unit: a person who wants assurance alone gets execution provenance and claim scoring too, and every session runs all three products' hooks (today two fence hooks already fire on every write on this machine, the exact overlap O23 exists to retire). That is the no-dependency law broken in practice even though no plugin "depends" on another on paper. It also forces the five colliding skill names to be renamed or nested, which is a new public surface under the freeze. Its extraction and layout are right, and Option B keeps them.

### Option B (chosen): one repository, three plugins under one marketplace

The same repository, the same clean extraction, the same one package per product and shared `contracts/`, but three plugin manifests (`plugins/brothermode`, `plugins/brothersbe`, `plugins/brotherds`, each whole with its own hooks, skills, tools, VERSION, CHECKSUMS and CHANGELOG) listed by ONE `.claude-plugin/marketplace.json` at the root with relative-path sources. One marketplace add; one install per product a person wants; skill namespaces unchanged (`/brothermode:start`, `/brothersbe:start`); one root battery that runs the three batteries and the contracts equality test; one manual Bitbucket pipeline; one board with three ledgers; the old repositories archived read-only with pointers.

What it does NOT give for free, stated so nobody reads it as done: shared contracts are not reachable from an installed plugin (the cache holds each plugin's directory alone), so every plugin carries its own copy of the passport schema and fixtures, exactly as the two products do today with byte-identical files, and a root test holds the copies equal to the master in `contracts/`. One registry is a decision (O23), not a consequence of the layout.

### Option C (rejected): three repositories plus a fourth, contracts-only repository

Keep the three repositories where they are and add a fourth holding the passport schema, the handoff package and the shared delivery gates, consumed by the three as a development-time dependency.

Rejected because it keeps both leaked public histories and their pull-request refs exactly where they are, adds a fourth Bitbucket leg to a 50 minute monthly budget that already cannot afford the first three, and centralizes contracts that are already byte-identical copies a test can hold equal without a repository to pin. It costs a fourth manifest, a fourth release cadence and a compatibility matrix, and the reviewers' one story becomes four.

### Option D (considered, not chosen): stay as three repositories and converge by tests only

The preparation list of this page applied in place, with no merge. Not chosen because the founder's north star names one repository; it stays the rollback position of the migration plan and costs nothing to keep.

## The decision table

| Criterion | A: one plugin | B: three plugins, one marketplace | C: three repos plus contracts | Evidence |
|---|---|---|---|---|
| C1 install path | 1 | 2 | 0 | R14: two adds and two installs today; the team installs assurance alone; the docs confirm one add, per-plugin install |
| C2 history and privacy | 2 | 2 | 0 | R12: 278 history hits here, 7 accepted objects there, 44 pull-request refs; extraction leaves history behind, C keeps it |
| C3 no-dependency law | 0 | 2 | 2 | R3 and R10: two fence hooks per write today; one manifest would make that permanent |
| C4 frozen surface | 0 | 2 | 2 | R10: five colliding skill names; namespaces survive only with separate manifests |
| C5 one battery, ceremony, registry | 2 | 1 | 0 | R4, R5: B makes a root runner natural; A forces it; C leaves three of each |
| C6 Bitbucket minutes | 0 (NO-DATA) | 0 (NO-DATA) | 0 (NO-DATA) | R11 counts pipelines, not minutes, and no battery has ever been timed on a runner (the only runtime figure, 8 to 13 minutes for 42 suites, is local); scored 0 for all three until one run is timed (found by the gate of 2026-08-22) |
| C7 release cadence | 1 | 2 | 1 | R6: three VERSIONs move independently under B; A bumps all three on any change |
| C8 reviewers' reading | 2 | 2 | 1 | R9: one README, one board; C splits the story four ways |
| C9 gate cost and coupling (added after the gate of 2026-08-22) | 0 | 1 | 2 | a root runner of three batteries in sequence exceeds this repository's PO-1 poll ceiling of 800 seconds (its own battery alone measured 516 seconds) and one red battery would block three releases; B mitigates with one receipt per plugin and a product releasing on its own receipt (P16), A cannot, C is independent by construction |
| Total | 8 | 14 | 8 | C6 scored 0 for all, C9 added; the choice does not flip |

## Decision

Option B: "one repository, three plugins under one marketplace", with Option A's clean extraction and per-product layout, and the explicit preparation list below so that the move is a move. The recommendation is the session's; the decision is the founder's and is recorded below verbatim.

## The proposed top-level layout (recorded here, built in phase 4, never before the timing gate)

```
Brother/
  README.md                      one story: the chain, three products, when to use each
  LICENSE                        MIT
  .claude-plugin/marketplace.json  name brother; plugins: ./plugins/brothermode, ./plugins/brothersbe, ./plugins/brotherds
  plugins/brothermode/           today's BrotherModeUp tree at its named commit (plugin.json, hooks/, skills/, tools/, scripts/, docs/, VERSION, CHECKSUMS.sha256, CHANGELOG.md)
  plugins/brothersbe/            today's BrotherSBE tree at its named commit
  plugins/brotherds/             today's BrotherDS tree, rewritten to roles, with plugin.json, VERSION, CHECKSUMS.sha256 and CHANGELOG.md added (its queue item plugin-surface)
  contracts/                     change-passport.v1.json (master) and fixtures/; handoff-package.v1.json once ratified; DIGESTS.txt naming every copy that must match
  gates/                         the MASTER copies of the five delivery scans (secret, assignment, attribution, dash, private terms) and the release invariant; each plugin carries its own copy under scripts/, like contracts, equality-tested by the root runner, because an installed plugin cannot read outside its own directory
  scripts/local-gates.sh         one runner: the three batteries in sequence with ONE RECEIPT PER PLUGIN plus one for the merged shape, then the contracts and gates equality tests; its poll ceiling sized to three batteries (P16); a product releases on its own receipt
  bitbucket-pipelines.yml        custom (manual) pipeline only, one step running scripts/local-gates.sh --no-post
  .github/workflows/             dormant command sources only; no automatic trigger, no macOS or Windows runner
  docs/plan/GANTT.html           the family board, produced by running plugins/brothermode's board tools FROM THE ROOT (they resolve paths from the working directory); plugins/brothermode keeps its own board for its suite, a duplication named here and decided in P17
  docs/handover/                 the family ceremony, bm_handover.py run from the root; plugins/brothermode keeps its own docs/handover for its suite (P17)
```

## Consequences

- The backlog is finished IN PLACE first; nothing moves until the timing gate reads green. Every preparation item below is valuable on its own and none is wasted if the merge is postponed.
- Three VERSION files, three CHANGELOGs and three tag prefixes (`brothermode-v`, `brothersbe-v`, `brotherds-v`) replace today's unprefixed tags; the root CHANGELOG is an index.
- Two fence hooks stay two until O23 is decided; the layout does not decide it, the founder does, in phase 2.
- BrotherDS joins a public tree only after its decision 5 (separate internal context, go public MIT) is answered yes and executed; if answered no, the repository holds two public plugins and BrotherDS stays a separate private repository (an Option C shaped exception for one product, recorded as such).
- The three old repositories are archived read-only with a pointer README after cutover; the team's reinstall path is one marketplace add; nothing is deleted, and the archive flip is the founder's hand.

## What would flip this

- To Option A: the team asks, in its own words, for one install of all three, AND O23 has landed (one registry, one fence hook), AND the founder decides the skill namespace for the unified plugin. All three, because each alone is the failure A was rejected for.
- To Option C or D: BrotherDS's decision 5 is answered no and the founder also declines a public two-plugin repository, or Bitbucket's free plan changes so that four legs cost nothing.
- Any of the six timing conditions proving unreachable within the calibrated range of phase 3 sends the question back to the founder rather than lowering the gate.

## The preparation list, "do now, merge later" (phase 2 of the roadmap)

Each item names the repository, the files, the writer tier (sonnet at effort high unless stated; design items are the strongest tier's own; founder windows are his) and a runnable done-check. Forecasts are AGENT minutes as briefed; the actual range applies the calibration quoted in the roadmap (`python3 tools/bm_forecast.py calibrate`: judged median 2.24 over n=14, any median 1.39 over n=17).

| Id | Item | Repository, files | Tier | Est | Done-check |
|---|---|---|---|---|---|
| P1 | O23 decided: one fence owner (retire `tools/sbe_fence_hook.py` behind `tools/bm_fence_hook.py` through the assurance product's coordination module; the parity map's first move and the delivering session's design both recommend BrotherMode owns the fence; the founder decides) | both: `docs/plan/PARITY-READ-2026-08-15.md`, both `hooks/hooks.json` | design, founder window | 90 | a ratified ownership decision recorded in both repositories naming the single fence owner (the queue's own check for O23) |
| P2 | M13: the two registries recognise each other's owner until P1 lands | BrotherModeUp `tools/bm_store.py`, `tools/test_bm_store.py` | sonnet | 90 | the queue's own check: a fence line written by `bm_store.py claim` carries an identity the INSTALLED `sbe_fence_hook.same_session` matches, proven by a regression test red on the current render |
| P3 | The passport's second read-only consumer authorised | BrotherSBE `docs/specs/2026-08-15-change-passport-seam.md`; BrotherModeUp `docs/PASSPORT.md`; BrotherDS `docs/TRIUMVIRATE-INTEGRATION.md` and `bds.py` | founder window, then haiku | 30 | `grep -n "read-only consumer" ` hits in both contracts; `/usr/bin/python3 bds.py passport <fixture>` no longer prints the UNAUTHORISED cap |
| P4 | The handoff package wire format ratified | BrotherSBE `contracts/handoff-package.v1.json` (new) with one fixture and one test; BrotherDS reads the `ratified` marker | founder window, then sonnet | 120 | `bds.py handoff <fixture>` not capped at NO-DATA; the assurance product's test asserts the schema; `python3 evals/test_no_data_class.py` still 0 failures |
| P5 | Passport conformance on the same fixture bytes on all three sides | BrotherModeUp `schema/fixtures/`, BrotherSBE `tools/fixtures/`, BrotherDS (a fixture copy under `examples/`), one digest file per repository | sonnet | 60 | the three suites each print the canonical fixture's sha256 and all three equal `e6d68b76...`; a byte changed in any copy reddens that repository's suite |
| P6 | The same five delivery scans as a script in every tree | the `gates/` master mirrored into `scripts/delivery-scans.sh` in each repository, reading `~/.brothersbe-private-names` | sonnet | 60 | each script exits 0 on a clean range, exits 1 naming the hit on a planted fixture, and exits 2 when the list file is unreadable; the assurance product's own history test stays authoritative there |
| P7 | Release invariant, VERSION and CHANGELOG shape in all three | BrotherModeUp adopts the "VERSION must move with distributable files" check beside its rule 1; BrotherDS gains VERSION, CHANGELOG.md, CHECKSUMS.sha256 and `.claude-plugin/plugin.json` (its queue item plugin-surface) | sonnet | 120 | each repository's invariant command prints PASS on its head; `sh scripts/verify-install.sh` MISSING 0 MISMATCH 0 in all three |
| P8 | One ceremony shape: the assurance and the claim products adopt the generated pack with a by-hand verify-close checklist, no new verb | BrotherSBE `.sbe/handover-<session>/` convention documented in `docs/HANDOVER-BY-HAND.md` equivalent; BrotherDS `docs/` | haiku | 30 | the next pack in each repository has a first-line FINISHED or UNFINISHED verdict, every file non-empty, a zip diffed at zero difference |
| P9 | One board structure: the absolute structure checked by the same checker in all three | BrotherModeUp `tools/bm_progress_check.py` run against the sibling's and BrotherDS's GANTT.html | haiku | 30 | `python3 tools/bm_progress_check.py --page <path>` passes on all three files |
| P10 | Namespaced tool names recorded, zero collisions verified | inventory R10 | done this session | 0 | `comm -12` over `tools/` prints only `WEEKLY-REVIEW.md` and `__pycache__`; under Option B no skill rename is needed |
| P11 | BrotherDS internal context separated (its decision 5) | BrotherDS: at `8084340` two files remain (the research file whose name carries two terms, and the scope directive), the rest de-named last night; claims and receipts kept gitignored | sonnet | 45 | `git grep -c -i -F -f ~/.brothersbe-private-names` prints nothing over the tree; `/usr/bin/python3 bds.py selftest` SELFTEST PASS |
| P12 | Vault consolidation plan (BrotherDS decision 6): one space `10-Projects/brother` proposed under AGENTS.md, created only on approval | the vault | founder window | 15 | the proposal note exists; no folder created before his yes |
| P13 | Bitbucket parity proven once per product, the deliberate free-tier way | keychain item `bitbucket-api-token` (his hand), the seat limit (his hand), then one `custom:` run per product | founder, then haiku | 30 each | each run's id and verdict quoted; `ci/bitbucket-pipelines.yml` marked EXECUTED in the sibling's parity page |
| P14 | BrotherDS PROJECT.md status current (it still says nothing pushed and no remote) | BrotherDS `PROJECT.md` | haiku | 15 | its status line names the remote, the branch, the sha and PR 1 |
| P15 | The proposed layout above recorded and the marketplace mechanics quoted | this page | done this session | 0 | this section exists with the documentation quotes |
| P16 | The batteries made relocatable, before any rehearsal: the assurance product's runner hardcodes `TRUSTED_REF="origin/main"` and resolves its workflow path from the repository root (`scripts/local-gates.sh` lines 146 and 161, found by the gate of 2026-08-22), so a throwaway extraction refuses with exit 2 before running one command; the ref and the path become inputs read from the plugin's own root, and the root runner gets a poll ceiling sized to three batteries and one receipt per plugin | BrotherSBE `scripts/local-gates.sh`, BrotherModeUp `scripts/local-gates.sh`, `CLAUDE.md` PO-1 | sonnet | 90 | each runner, invoked from a fresh extraction with no `origin/main`, runs its battery and signs its receipt; the root runner's poll loop outlasts the sum of the three measured runtimes |
| P17 | The root ceremony and board paths decided and tested: `tools/bm_handover.py` and the board tools resolve `docs/plan/GANTT.html` and `docs/handover/` from the working directory, so the family board and packs at the merged root and the product's own copies inside `plugins/brothermode/` both exist; decide which suite checks which, and test it | BrotherModeUp `tools/bm_handover.py`, `tools/bm_progress_check.py`, `tools/test_bm_handover.py` | design, then sonnet | 60 | `python3 tools/test_bm_handover.py` green from inside `plugins/brothermode/` in the rehearsal, and `python3 tools/bm_handover.py detect` run from the merged root names the root pack |

## The timing gate, "merge when": six conditions, each with its check and today's reading

| # | Condition | Check | Reading on 2026-08-22 |
|---|---|---|---|
| 1 | Phase 1 rows closed and 3.3.0 installed by the team: the note to the two lead reviewers sent, their retest recorded | the roadmap's phase 1 ledger ticked; a dated line in the private vault naming the note and the retest (a record to be written, not a command; a stranger cannot run it and the condition says so) | NOT MET: 3.3.0 not yet on main (battery 51 of 52 at `bddbc63`, the delivering session's run at its head pending); no tag; no note |
| 2 | Passport conformance green on all three sides on the same fixture bytes | P5's three commands printing one digest (the third exists only once P5 lands; until then this check is not runnable) | PARTIAL: two sides byte-identical (`e6d68b76...`), BrotherDS never run against the fixture |
| 3 | BrotherDS's internal context separated and PR 1 resolved | P11's grep empty; `gh pr view 1 --json state` not OPEN | NOT MET: 30 matches in 2 files at `8084340` (104 in 9 at `8840c2d`); PR 1 OPEN into `v1-claim-receipt` |
| 4 | The PRODUCT-DIRECTION amendment naming the merge landed by the founder | `grep -n "one Brother repository" PRODUCT-DIRECTION.md` hits AND the landing commit is the founder's own; founder ownership of that file is UNENFORCED (no hook in `hooks/` guards it), so the second half is read by a person | NOT MET: drafted below as PROPOSED, and decided by him to land |
| 5 | A clean-extraction rehearsal into a throwaway PRIVATE repository passes each product's battery and the FIVE delivery scans (the private-terms scan included, the one a public-bound tree exists to run) | the rehearsal's receipt per product and the five scans' exits, quoted | NOT MET: not started; needs P16 first |
| 6 | Bitbucket parity proven once for the merged shape | one `custom:` run of the root runner, id and verdict quoted | NOT MET: keychain item absent, workspace seat limit |

## The migration plan, phase 4, expand and contract, reversible (sized, not started)

| Step | What | Est agent min | Actual range (1.39 to 2.24) | Rollback |
|---|---|---|---|---|
| M1 rehearsal | after P16: extract the three trees at named commits into a throwaway PRIVATE repository laid out as above; run the three batteries and the five scans; delete nothing | 180 | 250 to 403 | discard the throwaway |
| M2 extraction | the real Brother repository, PRIVATE first, from the same commits; the contracts equality test green; root runner green | 120 | 167 to 269 | the old repositories are untouched |
| M3 parity | one deliberate Bitbucket run of the root runner | 30 plus his hand | 42 to 67 | none needed |
| M4 cutover | marketplace manifests and READMEs point at the new repository; the team's reinstall path documented and walked once on this machine; the repository made public by the founder | 120 | 167 to 269 | the old marketplaces stay installable until he archives them |
| M5 archive | the three old repositories archived read-only with pointer READMEs, his hand | 15 | his clock | unarchive |

Total agent work 465 briefed minutes, 646 to 1042 actual, across phase 3 and 4; not one session's work, and none of it before the gate.

## PROPOSED amendment to PRODUCT-DIRECTION.md (drafted here and in the vault's pending-amendments note; landed only by the founder, in his words)

> AMENDMENT, founder direction (date of landing): the three products converge into ONE repository, Brother, created by clean extraction of the three trees at named commits and never by merging histories. BrotherMode (execution provenance), BrotherSBE (assurance) and BrotherDS (the claim, and verified reality for a claim) live there as three plugins under one marketplace manifest, each whole and installable alone, sharing one contracts directory for the change passport, the handoff package and the delivery gates, one battery, one ceremony, and one registry once its owner is decided. The merge happens when the six-condition timing gate in docs/plan/ADR-2026-08-23-one-brother-repository.md reads green, not before; until then the backlog is finished in place and each repository is prepared so the merge is a move. The three existing repositories are archived read-only with pointers, never deleted. The merged product is ONE product to the person using it: one entry point that routes, one vocabulary, the seams as plumbing nobody touches, and a surface redesigned ONCE at the merge around the criterion that it shrinks by at least a third in skills, commands and agents, measured before and after; the tool surface stays frozen before and after that one redesign. BrotherDS's capability is routed as experimental until its first claim is scored against a real outcome. Nothing else above this amendment changes: the passport stays the only seam between execution and assurance, every development works on both hosts, and nothing self-fires in CI.

## The founder's decision (verbatim, from the question UI)

Round one, 2026-08-22 about 12:0x JST (10:0x local), question UI, his words verbatim:

- The shape: "Same as superpowers model optimized through Fable planning and risk management". Not a pick among A, B and C: an instruction to compare the shape with the superpowers model first. Recorded as open; the comparison round below answers it in this session.
- BrotherDS: "Yes: separate the internal context, then public MIT, before it joins (Recommended)". Decision taken: P11 is a precondition of the merge (timing gate condition 3).
- The verified-reality owner: "Compare to Superpower and the other leading plugins then come with the better idea with fable max". Not a pick: the same comparison informs it; the strongest tier works it at the effort he named.
- The amendment: "Land it now, as drafted in the ADR (Recommended)". Decision taken: he lands it by his own hand; the session holds the block's shape sentence until the comparison round closes, then hands him the final text. PRODUCT-DIRECTION.md is not edited by any session.

## Round two, 2026-08-22 about 12:1x JST, question UI, his chosen options verbatim

- The push of 3.3.0: "Push now with the receipt at 51 of 52 and the v3.2.0 defect named (Recommended)". Given before the delivering session's gate fix was known; with that fix a 52 of 52 receipt is the better reading of the same answer.
- Pull request 48 (26 commits absent from main by subject): "Merge it". His pick against the recommendation; applied only after the tag is pushed (release-cut rule), by one lane resolving conflicts, with the battery green at the merge commit.
- BrotherDS's request 1, the passport's second read-only consumer: "Yes: authorise the read-only second consumer (Recommended)".
- BrotherDS's request 2, the handoff package wire format: "BrotherSBE writes contracts/handoff-package.v1.json with a fixture and a test; BrotherDS reads the ratified marker (Recommended)".

## The comparison round (his instruction of round one), to be filled this session

What is compared: how superpowers and the other leading plugins organise their repositories and marketplaces, how versions and releases move, and what they do about risk, read from their own pages by three researchers (sonnet, effort high per their definition) on 2026-08-22, every fact with the URL it came from in the session log; then the better idea, worked by the strongest tier at the effort the founder named.

### What the leading projects actually do (measured by the researchers, not remembered)

| Project | Repository shape | Plugins and sources | Versioning and release | Risk controls | Post-release reality |
|---|---|---|---|---|---|
| superpowers (obra) | ONE repository holding ONE plugin of 14 skills, no agents, one session-start hook; per-harness manifest directories in the same tree (.codex-plugin, .cursor-plugin, .devin-plugin and others; 14 harnesses claimed) | its marketplace (obra/superpowers-marketplace, version 1.0.13) lists TEN plugins, each a SEPARATE repository by git URL, never a relative path | plugin.json 6.3.0; 34 tags; 4 releases in the last 60 days (about one per two to three weeks); RELEASE-NOTES.md in the tree | 77 test entries (shell runners per harness, a Node suite); no cloud CI in the tree; a verification-before-completion skill (a discipline, human-read); no documented rollback or uninstall path found | none |
| Anthropic, claude-code | ONE repository holding TWELVE plugins under plugins/<name> | one .claude-plugin/marketplace.json, every source a relative path "./plugins/<name>"; one plugin installed at a time by name | each plugin carries its own independent version (frontend-design 1.1.0, hookify 0.1.0); a root CHANGELOG.md; ten tagged releases of the host in the last 60 days | the one hook-bundling plugin (security-guidance) documents what it sends and disclaims; no tests visible in that plugin | none |
| ruflo (ruvnet) | ONE repository, plugins/ holding 37 plugins | one marketplace.json, relative sources "./plugins/ruflo-core" and so on, "so users install only the capability they need" | package.json version; about ten releases in 60 days; CHANGELOG.md | a verify command checking installed bytes against a signed witness; a pre-ship audit harness; a security-audit plugin; GitHub Actions | none |
| compound-engineering (EveryInc) | ONE repository, ONE plugin, 33 skills, per-host manifest directories | marketplace.json with one entry, source "./" | release automation owns versions; CHANGELOG.md; GitHub Releases | CI, a test suite, SECURITY.md and PRIVACY.md | none |
| BMAD-METHOD | one monorepo, npm package, modules inside it | a .claude-plugin structure describing modules, not separate plugins | package.json and tags (dates conflicted across two sources, counted UNCERTAIN) | lint, pre-commit hooks, automated review, SECURITY.md | none |
| get-shit-done (gsd-core) | one repository; runtime-specific marketplace plugins beside an npm package | changesets-driven releases | several releases per month (dates UNCERTAIN) | mutation testing, named guards for plan drift and fact drift (a verification discipline inside the tool) | none |
| spec-kit (GitHub) | one Python package with its own extension system, no marketplace file | PyPI, pinned git install | v1.0.0 then v1.0.1; about nine tagged releases in 60 days | pre-commit, tests, SECURITY.md, self check and self upgrade | none |

### What transfers from the superpowers model, and what does not

The founder's words were "same as superpowers model optimized through Fable planning and risk management". Read literally, the superpowers model is one repository holding one plugin of many skills, which is Option A. Read by what makes it work, it is four things, three of which transfer and one of which does not.

1. Skills first, runtime adapters in the same tree (transfers, later): superpowers ships per-harness manifests beside one skills tree. PRODUCT-DIRECTION's own runtime-adapter section already says Claude Code is the verified runtime and the others carry exact support labels; the per-plugin adapter manifests are a phase after the merge, not a reason to change the repository shape.
2. Tests in the tree and no cloud CI (transfers, already ours): superpowers runs shell test runners in the repository and has no workflow directory; this estate runs every gate locally by founder law and posts a status afterwards. The root runner of the Brother repository is the same idea.
3. Release notes in the tree and a release every two to three weeks (transfers): three VERSION files and a root CHANGELOG index, per-plugin versions the way Anthropic's twelve plugins carry theirs.
4. One plugin (does NOT transfer): superpowers can be one plugin at zero cost because it ships no write-refusing hooks and no registry; its hooks directory holds one session-start hook. Our three products carry two PreToolUse fence hooks, a Bash write guard, a session cap, two registries and telemetry. Bundling them into one plugin makes every session run all of it, which is the no-dependency law broken in practice, and renames five public skills under the freeze. What superpowers does ACROSS repositories with its federated marketplace of ten separate plugins, Anthropic and ruflo do INSIDE one repository with relative sources. That inside-one-repository form is Option B.

### The better idea

Option B, now grounded on the two projects that own the platform and the largest plugin catalogue respectively, with three additions taken from the comparison and sized into the roadmap rather than assumed:

- From ruflo: a bytes witness at install. This estate already has it (CHECKSUMS.sha256 and verify-install in two products); P7 extends it to the third and the root runner signs one receipt per sha.
- From superpowers and compound-engineering: per-harness adapter manifests per plugin, AFTER the merge and after the four user journeys, under the runtime-adapter rules PRODUCT-DIRECTION already states; recorded as a parked item with that flip condition, not scheduled.
- From the last column: none of the seven measures whether reality agreed after release. GSD and superpowers stop at a verification discipline inside the session; ruflo stops at a bytes witness. The verified-reality stage is this family's edge, which settles the owner question below by what each product can measure rather than by who asked.

The decision table is not re-scored: the comparison adds evidence to C1, C3 and C8 and moves no score. B stays at 15.

### The verified-reality owner, the better idea

The chain's ownership table gives BrotherMode and BrotherSBE "should" roles at this stage and gives the HUMAN the answer ("says whether it actually worked", the column the chain says may never be automated away), while its status table records the stage as DOES NOT EXIST; the standing decision N2 builds the end of the chain on the assurance side; BrotherDS asks to own the stage because its Verified Claim Rate is the only metric in the family that reports whether reality agreed; and the comparison shows no leading plugin owns a post-release outcome loop at all. The honest shape is ownership by what each product can measure, one writer per record kind:

- BrotherMode RECORDS the outcome of a change (tools/bm_reality.py: accept, reopened, rolled-back, incident), linked to the queue item; it judges nothing.
- BrotherSBE JUDGES a change's verified reality (N2 intact: readiness, observation, the reducer reduce_verified_reality gains its callers), reading BrotherMode's record through the passport's return edge once H4 lands.
- BrotherDS OWNS THE STAGE'S LEDGER: it counts the outcomes a PERSON observed and recorded against the uncertainty that was stated (the Verified Claim Rate for claims) and the change-level reopen rate from BrotherMode's records and BrotherSBE's verdicts, so the family has one place that answers "how often did reality agree" for both units. A computed rate never replaces the human's answer; it counts it. BrotherDS judges no change and writes no change record. (The gate of 2026-08-22 caught the earlier wording, which dropped the human column; the founder chose the split with that column restored here and is told so in the close-out.)

Put to the founder in round three as "split by unit, ledger owned by BrotherDS"; the flip condition either way is the first resolved claim and the first reopened change landing in the same month, which will show whether two ledgers drift.

## The founder's decisions of round three (verbatim, question UI, 2026-08-22 about 12:5x JST)

- The shape, final: "B: one repository, three plugins under one marketplace, the Anthropic and ruflo shape (Recommended)". DECIDED. The amendment's shape sentence stays as drafted.
- The verified-reality owner: "Split by unit, ledger owned by BrotherDS (Recommended)". DECIDED. BrotherDS's request 3 is answered by unit; N2 stands for a change; the chain document gains this sentence through a PROPOSED amendment of its own, landed by the founder.
- The vault spaces: "Propose one space 10-Projects/brother at the merge, keep three until then (Recommended)". DECIDED. P12 writes the proposal note; nothing is created before his yes at the merge.
- The Bitbucket shape: "One custom (manual) pipeline running the root battery, run once per release candidate and on your request (Recommended)". DECIDED. The layout's bitbucket-pipelines.yml is that one step.

## Round four, 2026-08-22 about 13:3x JST, question UI, his words verbatim, and the approach taken

Surfaced to him: BrotherDS's own docs/ONE-PRODUCT-2026-08-22.md (written last night after his words "merge them all under one like superpower", unread by this page until the checkout was fast-forwarded) recommends ONE PRODUCT under the BrotherMode name, the claim as the general unit for all three ("one object with three subtypes"), the seams dissolved, a third of the combined surface removed as an exit criterion, one entry point that routes, and its own counter-argument (score one claim against reality before merging). Its companion docs/COORDINATED-PLAN-2026-08-22.md already lands where round three did on the reality owner: occupied per unit, neither product implementing the other's mechanism.

- On which governs: "Merge them under Brother new repo". Read as: the target is a NEW repository named Brother, created by clean extraction, which is what Option B builds; the three existing repositories are archived with pointers afterwards.
- On the seventh gate condition: "Find the right approach as Fable and handle a harmony between all functions to be seamless like Superpowers". Read as a delegation: the strongest tier designs how the three products become one seamless product without breaking the laws, and decides the gate.

The approach taken, the strongest tier's own design under that delegation:

1. PACKAGING stays Option B: three whole plugins inside the Brother repository, each installable alone, one marketplace. This is what the no-dependency law and the team's install path require, and it is what Anthropic's and ruflo's repositories do.
2. HARMONY, the superpowers pattern applied: superpowers is one thing because one entry skill routes and its skills call each other, not because its skills share a folder. So Brother gains ONE ENTRY POINT that routes a person to the right capability by what they are doing (a change, a claim, a session), the way `using-superpowers` routes; ONE VOCABULARY (the chain's stages, the verdict tuple PASS, FAIL, NO-DATA, and the assertion object with three subtypes: BrotherMode asserts the work was done as described, BrotherSBE asserts the change is safe to ship, BrotherDS asserts the number is true); and the SEAMS TURNED INTO PLUMBING: the passport is written by execution and read by assurance and by the claim ledger with no manual step, the handoff package the same, tested by the root runner and invisible to the person using the product. The contracts survive as the mechanism of the seamlessness; what disappears is the person ever seeing them.
3. THE EXIT CRITERION from the BrotherDS document is adopted for PHASE 5, after the merge: the combined surface (19 plus 16 plus 1 skills, 15 commands, 13 agents today) shrinks by at least a third, measured before and after in skills, commands and agents, by collapsing the four state vocabularies first, then the duplicated documents, then the commands that exist only because a product needed its own entry. A merge that does not delete has failed; that sentence is the phase's first line.
4. THE COUNTER-ARGUMENT is adopted as a PROMOTION gate, not a join gate: BrotherDS joins the repository with the others (the entry point must route to it for the product to be one), and its capability is routed as EXPERIMENTAL until its first claim is scored against a real outcome (`/usr/bin/python3 bds.py ledger` reporting one resolved claim; its queue item first-scored-claim). This keeps the merge a move while answering whether the third product earns its place before anyone is told it has.
5. THE FREEZE: the entry point is a new public command and phase 5 deletes commands, both of which the tool-surface freeze forbids until the four user journeys pass. That is the founder's law to amend, so the PROPOSED amendment below now carries the sentence: the merged product's surface is redesigned ONCE, at the merge, around one entry point and the shrink-by-a-third criterion, and is frozen before and after that redesign.

What this changes on the page: the decision table is unchanged (the harmony layer sits above the packaging, not instead of it); P18 (the entry point and vocabulary design, with the before-measurement of the surface) joins the preparation list; phase 5 joins the roadmap; condition 7 joins the timing gate as a promotion gate with its check; the amendment text gains its surface sentence. The flip condition of the whole approach: if the founder, reading this, wants the BrotherDS document's shape instead (one plugin, the seams dissolved in code), Option A returns with the five skill renames and the hook bundling named in its rejection, and that is his decision to take in his own words.

| Id | Item | Repository, files | Tier | Est | Done-check |
|---|---|---|---|---|---|
| P18 | The harmony layer designed: one entry point that routes, one vocabulary (stages, verdict tuple, the assertion object with three subtypes), the seams as plumbing; the combined surface measured BEFORE (skills, commands, agents per product, quoted) so phase 5's third is checkable | Brother (the ADR), `skills/brother/SKILL.md` at the merged root later | design by the strongest tier, then sonnet | 120 | the design page names the entry point's routing table (what a person is doing, which capability answers) and the before-measurement, and the founder has amended the freeze |

| # | Condition | Check | Reading on 2026-08-22 |
|---|---|---|---|
| 7 | BrotherDS's first claim scored against a real outcome, before its capability is promoted from experimental in the entry point (a promotion gate inside the merged repository, not a join gate) | `/usr/bin/python3 bds.py ledger` reports at least one resolved claim | NOT MET: the ledger reports NO-DATA until a claim resolves |

## The delivering session's companion design (2026-08-22), and where the two agree

The assurance product's own session, with the founder's direct steer ("like Superpowers, think from the user's perspective and different personas"), wrote a repository-structure and soundness design at `~/Documents/BrotherArchive/2026-08-22-brother-merge-and-backlog/design/repo-architecture-soundness.md` (private archive, 87 lines; timing deferred to this roadmap by its own statement). Read here after round four. Where the two designs meet, stated so nobody reconciles them twice:

- The target shape is the same: one public repository, one marketplace, three plugins, and a persona front door (its "using-brother meta-skill modelled on using-superpowers" is this ADR's entry point that routes, P18).
- The four collisions it names match inventory rows R3, R7 and R10: the hook events both manifests register (one hook-chain runner), the two fence mechanisms (it proposes BrotherMode owns the fence, which is also the parity map's first move; P1's recommendation is aligned to that and stays the founder's decision), the shared telemetry file with a known lock-discipline defect between the two writers (one reconciled writer), and the passport as the one internal contract.
- It adds a criterion this ADR had not measured: the CONTEXT BUDGET. Three digests injected at every session start would bloat the always-loaded surface; its rule is that the front door injects ONE small digest and the products' digests load on demand. Adopted as P19 below, because the estate's own measurement says always-loaded context is its cost bottleneck.
- Its soundness invariants to hold NOW (no second fence, no second telemetry writer, no new hook event handler without a parity fixture) are the same discipline P1, P2 and P6 carry; its candidate control (a parity fixture that fails when either product adds a hook handler, a fence or a telemetry writer) is recorded as a candidate, not built.
- Its open decisions marked "confirm directly" (the shape, the second passport consumer) are the founder's rounds one to four recorded verbatim above; the delivering session received them by relay and asks him to confirm in its own channel, which is correct.

| Id | Item | Repository, files | Tier | Est | Done-check |
|---|---|---|---|---|---|
| P19 | The context budget of the merged product: one small digest injected by the front door at session start, the products' digests on demand; the bytes of each digest measured and quoted before and after | the three `DIGEST.md` and session-start hooks; the front door skill | design, then sonnet | 60 | the session-start injection of the merged shape measured in bytes and below the sum of today's three, the figures quoted |

## The adversarial gates of 2026-08-22 (opus, the brothersbe reviewers, the founder's one-time readjustment)

ADR gate (principal-architect, briefed to refute): REVISE, 1 BLOCKER, 4 MAJOR, 3 MINOR. Addressed in this one revision: the blocker (the chain's human column restored in the owner section, and the founder told in the close-out); M1 and condition 5 depend on relocatable batteries (P16 added, M1 sequenced after it); C6 re-scored NO-DATA for all three and C9 (gate cost and coupling) added, totals now A 8, B 14, C 8, the choice unchanged; the `gates/` contradiction resolved (masters at the root, copies per plugin, equality-tested); the ceremony and board duplication named and sized (P17). Minors: R14's install command corrected in the inventory (`brothermode@brothermode-marketplace`); condition 4 now says its second half is UNENFORCED and human-read; conditions 1 and 2 say which check still has to be built. Residue, named: C6 stays NO-DATA until one run is timed; P17 is a decision, not yet a design; the equal weights are a method choice under human review.

Roadmap gate (qa-reviewer, briefed to refute): REVISE, 3 BLOCKER, 6 MAJOR, 5 MINOR, addressed in the roadmap's own revision section. Codex: NO-DATA (out of credits), recorded.

