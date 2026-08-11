# Learnings, mistakes, and what went best

Status: CURRENT, 2026-08-11 morning. Every line carries its evidence; none
is an impression. No em or en dashes.

## Learnings the night paid for

1. A fence claim needs the session id the HOOK reports, not the harness id.
   My first claim was refused; adopt then re-claim fixed it. The release
   plan's step 0.2 predicted exactly this.
2. A deliberate wording copy drifts the moment one side is edited. The
   `bm_visual` copy-equality test went RED on my canary rewording, the same
   trap the colleague hit hours earlier. Two bites in one night make this a
   rule fix, not a curiosity (see 03, item 4).
3. A gate verdict binds to ONE SHA, and `test_all` adds a clean-checkout
   FAILURE at its end, so a tracked-file edit mid-gate poisons the run.
   Every board refresh tonight waited for the sentinel.
4. `verify-install` EXTRA entries can be a live colleague's minutes-old
   files. Read them (both were ASCII prose) before treating an alarm as an
   attack.
5. The secret-scan pattern `sk-` matches the CSS token `at-risk-ink`. Read
   the matches before believing the count: 11 hits, all variables.
6. Stale fences from dead sessions bit a SEVENTH time in 24 hours (FENCE A2
   refused a writer after being closed once ABOVE the wrong line). The
   stall detector now exists because of this class.
7. A canary that cannot tell absent from broken reports the worst claim in
   the worst words: empty stdout of a hook that never ran read as a
   demonstrated defect. Classify on returncode; tests RED first.
8. `park` cannot free a foreign fence under any circumstance (the store's
   own not-owner guard); `adopt --adopt-from-live-session` is the only
   recovery verb. Discovered mid-build by the SD agent, corrected in SD5.
9. The write-sites manifest lives under a `reviewed` key; a top-level entry
   is invisible to the loader. Read the loader before writing the entry.
10. P17: any shipped string telling a reader to run `python3 tools/...`
    lies in a packaged install. `bm_store.invocation` is the resolver.
11. The Browser pane paints only the first viewport while hidden; full-page
    proof comes from the Playwright-cached `chrome-headless-shell` with a
    tall `--window-size`.
12. A backgrounded `test_all` dies at exit 144; `nohup` plus a sentinel
    file plus a background watcher completed cleanly FOUR times tonight.
    This is now the proven pattern.
13. A four-file Codex audit in one call times out with zero findings; one
    call per file with a 20 minute ceiling produced 12 findings. The failed
    attempt's own postmortem prescribed the fix, which is why honest
    NO-DATA records earn their keep.
14. The store's task lifecycle refuses stage-skipping (`ready` to
    `accepted` is illegal), and `task add` fields are write-once. Plan
    transitions, and get `depends_on` right the first time.
15. `next` filters on state `ready` only and does not evaluate
    dependencies; dependency ordering is the operator's job via explicit
    transitions.

## Mistakes I made, named

1. Claimed a fence under the harness session id (refused; cost one adopt
   cycle).
2. Called the evening's work fully verified in a summary while the dark
   theme render predated the last page edit. The drift gate caught the
   overclaim; the re-render then happened and the claim was restated with
   its true scope.
3. Wrote two lint tests one edit AFTER their fix instead of RED first.
   Recorded in R4-TRIAGE as a process slip.
4. Put a Co-Authored-By trailer on a commit in a repo whose recorded rule
   forbids it; another session pushed it, and undoing it took a
   founder-authorized force rewrite of public history.
5. Patched `foreign_commit_base_finding` by blanket string replace without
   reading its actual signature (`claimed_base_sha`, not `claim_base_sha`);
   cost two extra fix rounds. One variable per attempt, and read the
   signature first.
6. Added the write-sites entry at top level without reading the manifest
   loader; the gate stayed red until I read the test.

## What went best, kept as practice

1. RED FIRST worked every single time it was used: the hardened purity
   tests named exactly the six predicted offenders; the canary tests
   reproduced both refuter findings before the fix; the SD fixture failed
   naming all five real stale fences.
2. The refute pass with EXECUTED falsifications (not reasoning) found a
   HIGH the same-family reviews missed, and its verdict blocked the tag
   until fixed. Falsification-only review briefs are worth their cost.
3. Honest NO-DATA: recording the failed Codex audit as NO-DATA rather than
   silence is what made the successful split rerun possible and cheap.
4. Coordination with a concurrent colleague session all night with zero
   collisions: disjoint fences, sentinel-reading instead of racing, and
   one deliberate wait (the bedtime refresh) instead of one poisoned gate.
5. Decisions recorded at the moment of taking, with flip conditions: the
   CC deferral, the waiver boundaries, the CX tier map. Nothing waits to
   be discovered in a summary.
6. The board never showed a number without its command, and its two
   noisiest moments (RED gates) went ON the board instead of being smoothed
   over. That is the product's own promise, kept by its own maker.
