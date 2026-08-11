# What changed as a rule, and what remains

Status: CURRENT, 2026-08-11 midday. Each entry names its enforcing file or
says UNENFORCED, per the spend laws. No em or en dashes.

## Closed this session, now ENFORCED

- RF-1 commit-message policy: scripts/bm_commit_msg_hook.py installed at
  .git/hooks/commit-msg refuses dashes and Co-Authored-By at commit time.
  It vetted its own landing commit.
- RF-2 claim session default: tools/bm_store.py resolves the fence-hook
  label when --session is omitted; explicit --session always wins; the
  two calibration tests pin the no-label path.
- RF-4 wording catalog: tools/bm_messages.py owns the shared refusal
  copy; the copy-equality test is now an identity assertion, so drift is
  impossible rather than detected.
- RF-5 gate receipt: tools/test_all.py writes
  .brothermode/gate-receipt.json, fail open, never in the tracked tree.
- M20 rule: while a gate runs, edit nothing tracked. Enforced by the
  gate's own clean-checkout check (tools/test_all.py, _worktree_dirt);
  the ledger and docs/mistakes/M20 carry the incident.
- PO recipes: repo CLAUDE.md now carries the sentinel gate pattern, the
  pgrep check, one-file-per-call audits, the deltas dispatch contract.

## Still open, honestly

- RF-3 prose fence retirement: store is the only fence surface; the
  STATE.md hand zone keeps narrative only. UNENFORCED until the hook
  stops reading prose lines; half a day, MEDIUM confidence.
- RF-6 durable watchdog: closes when SD2's kill-test passes; until then
  the gap is open and named on the board.
- test_bm_plugin_install flake: load-sensitive, one red in-gate, six
  greens standalone. Fix shape: the walltime-lint class (deterministic
  assertions). UNENFORCED watch item; do not chase mid-wave, fix when
  touching that suite.
- Slop-gate "fallback" false positive: recurring; consider a pattern
  refinement via the slop-gate pattern-curator agent. UNENFORCED note.

## Process optimizations proven this session

- Land builder work by copy, re-run suites yourself, commit; both
  dispatches followed it, zero collisions (now also in CLAUDE.md).
- Overlap founder question rounds with a running gate: the rounds touch
  nothing tracked, the gate finishes during them. Free wall time.
- BrotherSBE intake plus design gates on a BrotherMode loop worked first
  try: the dossier structured an already-ratified spec in about an hour,
  and the diagram tracer caught real untraced nodes. Keep using SBE for
  T2-plus builds in this repo.
