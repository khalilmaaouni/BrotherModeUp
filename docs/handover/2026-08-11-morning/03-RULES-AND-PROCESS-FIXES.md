# What should change as a rule, and what should be optimized as process

Status: CURRENT, 2026-08-11 morning. Each entry names the incident that
earned it, the fix, who enforces it (a file, or honestly UNENFORCED), and
the effort. Per the spend laws: a rule that cannot name its enforcing file
is written UNENFORCED, visibly. No em or en dashes.

## Rule fixes: things that demonstrably do not work well as they stand

### RF-1. Per-repo commit trailer policy must be checked BEFORE commit
Earned by: a Claude co-author trailer landed on a public-repo commit whose
recorded rule forbids it, got pushed by another session, and cost a
force rewrite of public history.
Fix: the push skill's dash-and-trailer scan moves from push time to commit
time in this repo via a commit-msg hook reading a per-repo policy line, and
repos.md gains a machine-readable `trailer: forbidden` field.
Enforce: a `.git/hooks/commit-msg` hook (new), plus the push skill.
Effort: 1 to 2 hours, HIGH confidence.

### RF-2. Fence claims should default to the hook-reported session id
Earned by: my own first claim refused as a foreign writer.
Fix: `bm_store.py claim` resolves the same id source the fence hook uses
when `--session` is omitted, instead of requiring the caller to know the
distinction.
Enforce: `tools/bm_store.py` plus a test.
Effort: 2 to 4 hours, MEDIUM-HIGH confidence.

### RF-3. Prose fences in STATE.md retire in favor of store fences
Earned by: FENCE A2 was closed once ABOVE the wrong line and kept refusing
writers; seven stale-fence bites in 24 hours, two of them from prose lines.
Fix: the store is the only fence surface; the STATE.md hand zone keeps
narrative only. The stall detector already sweeps store fences; prose
fences are invisible to it.
Enforce: the L13-style hook stops reading prose fence lines once migration
completes; until then UNENFORCED and this entry is the record.
Effort: half a day, MEDIUM confidence (migration of live lines needs care).

### RF-4. One message catalog for founder-facing reason strings (GAP-19)
Earned by: the deliberate controller-to-visual wording copy drifted twice
in one night, each time costing a red suite.
Fix: one catalog module owns the strings; every renderer imports it; the
copy-equality test becomes an import assertion.
Enforce: the existing copy-equality test flips to enforcing single-source.
Effort: 2 to 4 hours, HIGH confidence. Raise into Loop X1's first step.

### RF-5. The gate writes a machine-readable receipt (GAP-49)
Earned by: every page, ledger and handover tonight hand-quoted the gate
line beside a hand-copied SHA; the SHA-binding law currently lives on
discipline alone.
Fix: `test_all.py` writes `gate-receipt.json` (SHA, counts, wall, exit,
timestamp) next to its output; pages and packs read it instead of quoting.
Enforce: `tools/test_all.py` plus the CC generator consuming it.
Effort: 2 to 3 hours, HIGH confidence. Feeds Loop CC directly.

### RF-6. Watchdog and cadence crons must survive the session or declare they cannot
Earned by: the evening watchdog died with its session and tonight's crons
will die with this one; the re-arm is manual every time.
Fix: the stall detector already flags a dead watchdog; the durable answer
is the CC generated page plus a launchd or hook-driven refresh, product
work, not session memory.
Enforce: UNENFORCED until Loop CC lands; SD's sweep is the tripwire.
Effort: inside Loop CC.

## Process optimizations: things that work but cost more than they should

### PO-1. Gate runs standardize on nohup plus sentinel plus watcher
Proven four times tonight after the backgrounded form died at exit 144.
Write the three-line recipe into the project CLAUDE.md so no session
rediscovers it. Effort: minutes. UNENFORCED, documentation.

### PO-2. Cross-family audits run one file per call with a ceiling
The single four-file call produced NO-DATA; the split produced 12 findings.
Standing shape for Loop R3-class audits, already recorded in the evidence
file; copy into the audit brief template. Effort: minutes.

### PO-3. Worktree agents return deltas, orchestrator lands and verifies
Every landing tonight (L2H, SD, Phase 0, specs) followed copy, re-run
suites, commit; zero collisions all night. Keep as the standing dispatch
contract line. Effort: none, already practiced; UNENFORCED prose.

### PO-4. Board refreshes gate on `pgrep test_all` first
One near-poisoning avoided tonight only by checking. The hourly cron prompt
already carries the check; make it part of any future refresh instruction.
Effort: minutes.

### PO-5. Falsification-only review briefs as the default for safety seams
The R2 refuter's executed-attacks-only contract produced the night's most
valuable finding. Template its brief (attack list, executed-falsification
rule, COULD NOT BREAK fallback wording) into the reviewer agent docs.
Effort: an hour. UNENFORCED, brief template.

### PO-6. Read the loader before writing the entry
Two of my six mistakes (write-sites top-level key, signature name) share
one root: patching a file whose reader I had not opened. The existing
research law covers it; the optimization is the habit of quoting the
reader's loading line in the plan step before editing. Effort: none, habit.
