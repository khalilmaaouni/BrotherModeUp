# 07. Verification plan

## The checks, each named before the work (kickoff step 4)

| # | What it proves | Command or gate | RED first |
|---|---|---|---|
| V1 | Each signal S2 to S5 detects its fixture case | python3 tools/test_bm_stall.py, new classes per signal | Yes: fixture from this week's real scars fails before the signal exists |
| V2 | Auto-clear clears only provably dead work, receipted | test seeding a dead-owner stall (cleared, receipt names finding) and the same with one live signal (NOT cleared) | Yes |
| V3 | Durability: the kill-test | owning session killed mid-run; launchd log quoted showing detection within one interval | Yes by construction: run before the plist installs must miss it |
| V4 | Hook overhead inside budget | python3 tools/test_bm_hookperf.py, existing floors | Existing suite extended |
| V5 | Registration and install truth | python3 tools/test_bm.py; bash scripts/verify-install.sh exit 0; four places plus checksums | Existing gates |
| V6 | Purity: the sweep changes zero bytes | python3 tools/test_bm_effects.py after registering new code paths pure_read | Existing gate |

## Kill criteria per step
Hook overhead over budget stops the hook path (V4 is the tripwire).
launchd unreliable across sleep flips to the ADR's recorded flip. Three
failed attempts on any step reverts to last green and reports, per the
standing debugging law.

## Evidence handling
Every verdict quoted after the last edit, bound to one commit, read from
the gate receipt where the full gate is the check (the M20 and
gate-verdict laws). Absent measurements say NOT MEASURED. The full gate
runs on a still tree with the sentinel pattern from CLAUDE.md.

## Independent verification
Loop close gets a fresh-context refute pass on the auto-clear seam
(falsification brief: attack the allow-list, try to make it clear live
work), per the ratified swarm rules for safety seams.
