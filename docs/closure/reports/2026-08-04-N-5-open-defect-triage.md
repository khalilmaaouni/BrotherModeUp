# Open-defect triage of docs/NOT-FINALIZED.md, every entry in one of three buckets, N-5, 2026-08-04
Status: CURRENT as of 2026-08-04.

## The triage universe, counted rather than trusted

`grep -c "^## \|^### " docs/NOT-FINALIZED.md` returns 39 headings. One of them,
"What is genuinely finished" (line 1008), is the file's closing summary and
holds no defect; the other 38 are entries and every one is triaged below. Of
those 38, verified by reading every heading from the grep listing: 22 carry one
of the file's four status words in the heading (9 OPEN counting 17b, 5 PARTIAL,
3 UNPROVEN, 5 DEFERRED), which matches the earlier pass exactly; 9 carry a
closed-family verdict word instead (CLOSED, REFUTED, or PARTLY CLOSED: lines
49, 101, 176, 261, 316, 569, 590, 861, 902); and 7 carry no status word at all
(lines 501, 510, 644, 695, 735, 801, 954), including the unworded items 13, 14,
18, 19, 20 the brief named, plus item 24 and the correction-round subheading
under item 18. Item 17, the parent of 17b, sits in the closed-family group but
holds open residue bullets in its body, exactly as the brief warned.

Bucket meanings: 1 = blocks a user of the public release, fix now with a test
that fails without the fix. 2 = deliberately deferred, stated reason confirmed
still true today. 3 = an honest limit code cannot fix, belongs in
docs/KNOWN-LIMITS.md rather than in a backlog. FOUNDER DECISION = the bucket
turns on a value call only the founder can make; two options and a
recommendation are given below the table, never a silent choice. CLOSED = the
entry's own text records closure and no open work remains to sort (a closed
entry fits none of the three work buckets, and forcing one would manufacture
work; this deviation from the three-bucket rule is stated here plainly rather
than hidden).

## Headline

Bucket 1 is EMPTY. Nothing left in this file blocks or harms a real user of
the public release: all eleven machine-closable closure items are CLOSED per
docs/closure/CLOSURE_REGISTER.md, and every remaining open entry is a
deliberate deferral whose reason still holds, an honest limit needing
disclosure rather than code, or one of the three value calls listed after the
table. Because bucket 1 is empty, no fix-scope paragraphs are required; the
fix-scope column exists and is honestly blank.

## Triage table

| # | Entry heading (line in docs/NOT-FINALIZED.md) | Bucket | Date | Reason (2 sentences max) | Bucket 1 files + test |
|---|---|---|---|---|---|
| 1 | rc.4 MERGE: the gate carry cap was REJECTED (14) | 2 | 2026-08-04 | Never withholding a safety gate is the ratified design, and the volume cost this entry names has since been bounded without dropping any gate: the Loop 3 gate manifest with `GATE_EXPANSION_CAP = 5` (tools/bm_learning.py:1124, described in docs/KNOWN-LIMITS.md's rc.4 section, measured 5722 to 1849 characters on a 20-gate store). The reason still holds; the entry's "nothing prevents it" framing predates the manifest and understates what shipped. | n/a |
| 2 | rc.4 MERGE: approval needs two things, only one mechanical (36) | 3 | 2026-08-04 | Neither a receipt nor a typed reference can authenticate WHICH human answered on one machine, one user, no network; no code closes that. Already stated in docs/KNOWN-LIMITS.md ("Approval proves an answer, not an identity"), so this stops being backlog. | n/a |
| 3 | P7: the loop-close gate flakes 1 run in 16 (49) | CLOSED | 2026-07-31 | Closed by Loop 2 with a collision-proof forged token, proven over 100 consecutive runs. CHK-2A row 3 found no counter-evidence. | n/a |
| 4 | P7: the FTS5 fast path ships DISABLED by default (68) | 2 | 2026-08-04 | Opt-in confirmed still true (`FTS5_ENV` in tools/bm_store.py, CHK-2A row 4), and the stated reason outlives the rule: BM25 is a number the founder cannot re-derive in a tool sold on explainable retrieval. Reason still holds. | n/a |
| 5 | P7: retrieval gain measured on ONE labelled fixture (78) | 3 | 2026-08-04 | Proving the gain at scale needs a labelled corpus of real founder rules with graded relevance, which is data, not code: the same shape as register item X-03. Honest limit until real-use data exists. | n/a |
| 6 | P7: index maintenance covers approval and edit only (87) | 2 | 2026-08-04 | Since 2026-07-29 the index is reconciled against the rules at the moment retrieval consumes it, so a future write site that forgets `_fts_write_rule` costs one index rewrite, never a wrong answer. Deliberate mitigation accepted; mechanical enforcement remains `verify`'s job by design. | n/a |
| 7 | P6: the run stored the founder's prompt by default (101) | CLOSED | 2026-08-04 | The entry's OPEN remainder (`learning_applications.task_excerpt` keeps the query by default) is STALE: verified in code this session, the default excerpt is now the bounded term set (`L.query_terms(redact_text(query))`, tools/bm_store.py near line 8134, comment "LOOP 5 (the headline defect)"), and verbatim prose is stored only under the explicit `--store-excerpt` opt-in in tools/bm_learn.py, covered by a test in tools/test_bm_store.py. The entry needs a dated correction; CHK-2A row 7 checked the closed half and did not catch this. | n/a |
| 8 | P6: a task's vocabulary is still stored (116) | 2 | 2026-08-04 | The entry itself records that the trade was taken deliberately: refusing to store terms would make every empty retrieval permanently not decidable, killing the measurement the loop exists for. Reason still true, and it is the exact trade row 7's fix relies on. | n/a |
| 9 | P6: `retrieval_uuid` is nullable forever (125) | 2 | 2026-08-04 | Schema confirmed unchanged (CHK-2A row 9: no NOT NULL, no later migration). The stated reason, that requiring it is a second migration a loop already owning one should not take, still holds; legacy rows are permanently legacy either way. | n/a |
| 10 | P5-fix: `apply` discloses the two-units ambiguity (133) | CLOSED | 2026-08-04 | Closed by commit 259c30b and recorded in the entry's own 2026-08-04 correction: `apply` now refuses without exactly one work identity, a hard refusal stronger than the disclosure the entry originally asked for. Verified in code this session (`no-work-identity` refusal, tools/bm_store.py near line 8107). | n/a |
| 11 | P5-fix: fixes verified through `apply`, not the alias (157) | 2 | 2026-08-04 | The alias calls the same `Store.record_learning_applications`, so it inherits the fixes by construction, and spending new verification on a deprecated path scheduled for removal is deliberately declined (this reason is proposed by this triage; the entry states no deferral reason of its own). If the alias survives into 2.0.0 the cheap honest close is one test through `relevant --record-applications`. | n/a |
| 12 | Loop P5: `relevant` is deprecated but not removed (166) | 2 | 2026-08-04 | Kept so existing scripts do not break silently, with a deprecation line on every run (confirmed by CHK-2A row 12); removal belongs to the next major version. The PARTIAL sub-note (narrative docs still teach the deprecated verb) is documentation debt already carried in docs/KNOWN-LIMITS.md. | n/a |
| 13 | 1. Used daily, never measured (176) | 3 | 2026-08-04 | Real use exists and graded outcomes do not; only counting closes this, and no code produces the count (register item X-04 states the identical limit). Already mirrored in docs/KNOWN-LIMITS.md ("Used for real, but never MEASURED"); the users-track-main note is a communication task for the founder at tag time, not code. | n/a |
| 14 | 2. Bash writes are not gated by the fence hook (198) | 3 | 2026-08-04 | Not closable by design: gating Bash means parsing arbitrary shell, and full OS containment is explicitly out of scope; the C-02 narrowing (refusal plus alerting under enforced mode) is what code can do and has shipped, with its three limits checked against the code by CHK-2A row 14. Already stated at length in docs/KNOWN-LIMITS.md and SECURITY.md. | n/a |
| 15 | 3. Session identity is harder to forge, not unforgeable (249) | 3 | 2026-08-04 | Perfect unforgeability is unreachable on one machine, one user, no network: any process running as the user can read the token file. Documented in docs/HOOKS.md rather than overclaimed; nothing further for code. | n/a |
| 16 | 4. Handovers are lock-serialized, not transactional (261) | 2 | 2026-08-04 | The defect itself is closed (twice, with crash-injection and calibration tests); what remains are two DELIBERATE residues the entry names: manual `handover-ack` (because a render must not mutate the database) and same-heading dedupe to one row (the retry dedupe doing its job). Both reasons still hold. | n/a |
| 17 | 5. The adopt defect (316) | CLOSED | 2026-07-28 | Refuted by reproduction and closed; the GATE 3 ordering and its calibrated test confirmed present by CHK-2A row 17. Kept in the file as a lesson, not as work. | n/a |
| 18 | 6. Recovered work is owner-only on POSIX only (352) | FOUNDER DECISION | 2026-08-04 | Whether shared-Windows-machine readability of recovered work blocks a public 2.0.0 is a value call: fixing it requires breaking the project's own stdlib-only, no-subprocess law (icacls or pywin32), while shipping it disclosed keeps the law and the tool already prints the real mode it achieved. Options and recommendation below. | n/a |
| 19 | 7. The lazy core missed its own target (361) | 2 | 2026-08-04 | 1,490 tokens against a 400 target, and the entry's own verdict stands: what remains is the triage, the safety floor and the routing rows, and cutting either is not worth 1,090 tokens. Deliberate, measured, honestly unmet. | n/a |
| 20 | 8. The lazy core is UNPROVEN in the way that matters (371) | 2 | 2026-08-04 | Proving that sessions load the right reference requires observing real sessions, which is the item 1 measurement problem; the planned Stop-hook guard belongs with the dogfood window, the same gating docs/KNOWN-LIMITS.md already applies to the Loop 11B hook. This deferral reason is proposed by this triage; the entry states none of its own. | n/a |
| 21 | 9. Three (now four) scoring checks are red (380) | 2 | 2026-08-04 | These are live telemetry hygiene counters that drift by the hour with ordinary use, as the entry's own 2026-08-04 addendum says, not code defects a release fixes. The CI NO-DATA structure is the nature of a local-vault-dependent gate and is disclosed in the entry itself. | n/a |
| 22 | 10. The suites cannot be run concurrently (406) | 2 | 2026-08-04 | The serial `test_all.py` gate is the documented safe path, now also in CI (per the entry's own 2026-08-04 correction), and removing the module-rename technique is a test-architecture change deliberately not taken. A public user following the documented gate never hits the hazard. | n/a |
| 23 | 11. Phase 3, the public install, is DEFERRED (463) | FOUNDER DECISION | 2026-08-04 | The installer and plugin shipped, so what remains is scope: whether 2.0.0 requires a Windows-native hook dispatcher or ships with the installer's honest Windows refusal (WSL works) disclosed. That is a supported-platform value call; options below. The never-installed-by-an-outsider half is the X-02 family, not code. | n/a |
| 24 | 12. The independent re-audit was never run (491) | 3 | 2026-08-04 | Code cannot supply an independent adversary from a second model family; the register's X-01 (credits) and X-02 (outside participants) are the same wall. Belongs in docs/KNOWN-LIMITS.md (which already carries "No independent second-model review") with the reopening condition: it becomes work again the day the founder funds it. | n/a |
| 25 | 13. Orchestration practice did not improve (501) | 3 | 2026-08-04 | A process observation about fence-before-dispatch discipline and a lucky non-collision, deliberately scored flat; there is no code fix, only practice. It belongs in the record as a lesson, not in a backlog. | n/a |
| 26 | 14. Findings 16 to 63 triaged by class (510) | 3 | 2026-08-04 | Individual re-proof of 48 findings is exactly the independent re-audit of row 24 and inherits its wall. Already stated in docs/KNOWN-LIMITS.md ("What was checked by class rather than individually"). | n/a |
| 27 | 15. `dump` redaction is a secret scrubber, not a redactor (515) | FOUNDER DECISION | 2026-08-04 | The four prose columns (records.evidence, records.objective, digests.body, transitions.note) still pass ordinary sentences through with only secret-shape scrubbing (CHK-2A row 27 confirmed unchanged), and whether the fix is withholding them or disclosing them plainly turns on the founder's own 2026-07-31 because_text precedent. Options and recommendation below; either option is small, testable work once he picks. | n/a |
| 28 | 16. `claim --help` claims a record named `--help` (569) | CLOSED | 2026-07-30 | Closed wider than filed: `_require_positional` covers seven commands, calibrated by reversion. Confirmed still present by CHK-2A row 28. | n/a |
| 29 | 17. The English-only, 400-character correction filter (590) | CLOSED | 2026-07-29 | The filter is closed (three language packs, excerpting instead of dropping, proven through the real CLI). Its residue bullets are the recall-gap honest limit already stated inside the entry and the measurement gap that is row 13's bucket 3; nothing separate to sort here. | n/a |
| 30 | 17b. What Loop 4 owed the plan and did not build (616) | 2 | 2026-08-04 | Both open bullets are deliberate with reasons that still hold: no automatic rework detector because a wrong automatic verdict is review cost the founder did not ask for (re-confirmed by CHK-2A row 30, no scheduler invokes `capture_outcome_candidate`), and the correction row omits a work record because telemetry cannot resolve one, so it travels with channel 3 candidates instead. | n/a |
| 31 | 18. What Loop 6 built, and what its detector cannot see (644) | 2 | 2026-08-04 | All five OPEN sub-items carry stated reasons that still hold: lexical detection with the blind spot pinned by a test and a manual `link` escape hatch, no scope-containment guessing on no evidence, no edit CLI because founder surface is a design decision (grant-edit still absent, CHK-2A row 31), the source-candidate receipt quirk is a correct refusal, and O(n squared) is fine at tens of rows. Deliberate throughout. | n/a |
| 32 | Correction round, 2026-07-29: four ways the done gate leaked (695) | CLOSED | 2026-07-29 | Historical fix record, all four defects fixed with calibrated regression tests; the stricter-refusal trade it opened is part of row 31's deliberate design. Nothing open of its own. | n/a |
| 33 | 19. What Loop 7 built, and what it still cannot see (735) | 2 | 2026-08-04 | The remaining bullets are deliberate limits whose reasons hold: context reconstruction undercounts misses in the safe direction, limit-miss semantics are stated, the classifier reports what it is told by design, and the real-day caveat is row 13. The SKILL.md bullet closed per the entry's own 2026-08-04 correction; DIGEST.md staying at 13 lines is what a digest is. | n/a |
| 34 | 20. What Loop 8 built, and what its correction round fixed (801) | 2 | 2026-08-04 | Same standing as row 30: no automatic detector, deliberately, for the same review-cost reason; the weaker session-only grading path is honestly named in the entry (its missing per-count flag in loop-failures output is a nice-to-have disclosure, not user harm); real-day grading is row 13. | n/a |
| 35 | 21. Approval receipts landed; three documents described the old flow (861) | CLOSED | 2026-07-31 | All six doc sites corrected and SECURITY.md carries the receipts-are-secrets section; mechanism confirmed still enforced by CHK-2A row 35. | n/a |
| 36 | 22. `complete <short-prefix>` blames a missing record (902) | CLOSED | 2026-07-31 | Resolved at the CLI layer with `_resolve_record_uuid`, three tests including a calibration; confirmed still wired by CHK-2A row 36. | n/a |
| 37 | 23. The two oldest published tags are lightweight (924) | 3 | 2026-08-04 | Fixing it means force-updating two published refs, which this project refuses permanently on principle, so it will never be done and belongs in docs/KNOWN-LIMITS.md rather than in a backlog. Re-checked fresh by this session with a read-only `git ls-remote --tags origin`: v2.0.0-rc.1 and v2.0.0-rc.2 still show no peeled `^{}` line (lightweight) while v2.0.0-rc.13 does (annotated), and nothing current depends on either old tag. | n/a |
| 38 | 24. The two handover flakes were not reproduced (954) | 3 | 2026-08-04 | The two flakes are UNDECIDABLE (one never reproduced under deliberate load, the other's test no longer exists), and code cannot fix what cannot be reproduced; the CI annotation wrapper already captures any recurrence. The entry's one open remainder, the sibling stopwatch test deriving its ceiling from `small`, was closed 2026-08-04 by C-11: `_time()` in tools/test_bm.py now returns the minimum of five samples and both timing tests share it (checked by reading the fenced file this session: `def _time(self, text, samples=5)` is present; no line number is quoted because that file is changing under another agent's fence). | n/a |
| 39 | What is genuinely finished (1008) | none | 2026-08-04 | Not an entry: the file's closing summary of finished ground, holding no defect and nothing to sort. Included here only so every heading appears exactly once. | n/a |

## FOUNDER DECISIONS, stated for the question window, never decided silently

These three go to the founder. Each bucket depends on a value call about what
counts as blocking a public 2.0.0.

### 1. Item 6 (row 18): recovered work is owner-only on POSIX only

- Option A: ship 2.0.0 with the Windows gap disclosed exactly as today, since
  docs/KNOWN-LIMITS.md already states it in full and the tool prints the real
  file mode it achieved rather than lying.
- Option B: relax the stdlib-only, no-subprocess project law enough to make a
  real Windows ACL call (icacls or pywin32) and close it before 2.0.0.
- Recommendation: Option A. The exposure is narrow (other local accounts on a
  shared Windows machine), it is honestly disclosed to the person affected at
  the moment it happens, and breaking a foundational project law for it costs
  more than it buys.

### 2. Item 11 (row 23): the Windows-native hook dispatcher

- Option A: declare native Windows install out of scope for 2.0.0, keeping the
  installer's existing plain refusal (WSL works and is the documented path)
  and saying so in the release notes.
- Option B: build a Windows-native hook dispatcher before 2.0.0 so the install
  path stops being shell-dependent on a supported platform.
- Recommendation: Option A. The refusal is honest and already shipped, the
  store and recovery suites do cover Windows for users who reach it via WSL,
  and a dispatcher built without a single observed external Windows install is
  effort ahead of evidence.

### 3. Item 15 (row 27): ordinary prose in `dump` output

- Option A: keep the four prose columns in non-raw dump but disclose plainly,
  one sentence in dump's own output naming the columns whose ordinary prose is
  not redacted, plus the SECURITY.md export-posture sentence the entry itself
  asks for.
- Option B: withhold records.evidence, records.objective, digests.body and
  transitions.note from non-raw dump by default, the way learning raw_text is
  withheld through `_withhold_source` in tools/bm_learn.py.
- Recommendation: Option A. It follows the founder's own 2026-07-31 ruling
  that prose he wrote and can review is a feature, it preserves dump's
  diagnostic value, and the harm only arises when output is shared unread,
  which disclosure addresses at the moment it matters. Whichever he picks is a
  small, testable change (dump path in tools/bm_store.py plus SECURITY.md, a
  test asserting the disclosure line or the withholding).

## Cross-check against the N-6 telemetry findings

No entry of docs/NOT-FINALIZED.md is made obsolete by the eleven N-6 findings,
and none of the eleven duplicates an entry here: N-6's own report searched both
docs/NOT-FINALIZED.md and docs/KNOWN-LIMITS.md for every finding before
writing it down and found zero hits (its "What was checked and produced
nothing" section). All eleven are FIX dispositions inside tools/bm_telemetry.py
owned by the fenced agent, and none is re-triaged here.

## What was verified independently and what was leaned on, stated plainly

- Verified by this session directly: the heading counts and status-word counts
  (grep, listed above); item 7's stale OPEN remainder (read of tools/bm_store.py
  near lines 8100 to 8135 and the `--store-excerpt` opt-in in tools/bm_learn.py);
  the `no-work-identity` refusal behind row 10; `GATE_EXPANSION_CAP` behind
  row 1; the min-of-five `_time` helper behind row 38 (read only, file fenced);
  the live tag state behind row 37 (`git ls-remote --tags origin`, read-only,
  run in this session).
- Leaned on CHK-2A's 2026-08-04 per-row verification (cited by row number
  throughout) for entries not independently re-probed here, and on
  CLOSURE_REGISTER for C-02 and C-11. The historical CLOSED entries were not
  re-run, matching CHK-2A's own disclosure.
- Not run: `python3 tools/test_all.py` (orchestrator-owned) and any git command
  that writes.

## Done-check and counts

Headings in docs/NOT-FINALIZED.md: 39 (grep count above). Rows in the table:
39. They reconcile: every heading appears exactly once. Entries triaged: 38
(row 39 is the file's closing summary, not an entry, and is marked "none").

- Untriaged entries: 0
- Bucket 1 (blocks a user, fix now): 0
- Bucket 2 (deliberately deferred, reason still true): 16 (rows 1, 4, 6, 8, 9, 11, 12, 16, 19, 20, 21, 22, 30, 31, 33, 34)
- Bucket 3 (honest limit, move to docs/KNOWN-LIMITS.md): 10 (rows 2, 5, 13, 14, 15, 24, 25, 26, 37, 38)
- FOUNDER DECISION: 3 (rows 18, 23, 27)
- CLOSED, nothing open to sort: 9 (rows 3, 7, 10, 17, 28, 29, 32, 35, 36)
- Not an entry: 1 (row 39)

9 + 16 + 10 + 3 + 0 + 1 = 39. Of the ten bucket 3 rows, seven are already
present in docs/KNOWN-LIMITS.md in substance (rows 2, 13, 14, 15, 24, 26, and
row 5 partially via the benchmark caveat); the move that remains is for rows
25, 37, 38 and the completion of 5, which is a documentation change for
whoever holds that file's fence, not this agent.
