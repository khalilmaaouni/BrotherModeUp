# BrotherModeUp: repo working rules

Proven recipes from docs/handover/2026-08-11-morning/03-RULES-AND-PROCESS-
FIXES.md, PO-1 to PO-6, plus standing repo policy. Read PROJECT.md first for
identity and links; this file is process, not identity.

## PO-1: the gate, foreground detach plus sentinel (nohup dies, this does not)

`python3 tools/test_all.py` runs 8 to 13 minutes (516.3s measured 2026-08-11);
backgrounding it as a harness task dies at exit 144 with no verdict
(reproduced twice 2026-08-08). Detach and poll instead:

```
nohup bash -c 'python3 tools/test_all.py > "$TMPDIR/gate.log" 2>&1; echo $? > "$TMPDIR/gate.exit"' > /dev/null 2>&1 &
for i in $(seq 1 56); do [ -f "$TMPDIR/gate.exit" ] && break; sleep 10; done
cat "$TMPDIR/gate.log"; cat "$TMPDIR/gate.exit"
```

Never stop a running gate with `pkill -f` (can match another session's
prompt). Kill by PID after printing the target.

## PO-2, PO-3, PO-4, PO-6: proven process shapes

- PO-4: run `pgrep -f tools/test_all.py` before every board refresh. A
  refresh that read mid-gate output once poisoned the board.
- PO-2: cross-family audits run one file per call, with a ceiling. A single
  multi-file call returned NO-DATA; one-file-per-call found 12 real issues.
- PO-3: worktree agents return deltas, never a direct commit. The
  orchestrator copies the delta, re-runs the gate, commits. Collision-free.
- PO-5: review briefs for safety seams are falsification-only: the reviewer
  runs attacks and reports what broke or states COULD NOT BREAK; reasoning
  without an executed attack is NO-DATA.
- PO-6: before adding an entry to any registry (SUITES in tools/test_all.py,
  tools/write_sites.json, a workflow step), open the file that READS that
  registry first and confirm the shape it expects.

## Standing rules

- No em dashes, no en dashes, anywhere: code, comments, docs, commit
  messages, output.
- No `Co-Authored-By:` trailer, ever, in any commit
  (~/.claude/skills/github-desktop-push/repos.md, founder decision
  2026-08-10, after a force-rewrite removed one). Enforced at commit time by
  `scripts/bm_commit_msg_hook.py`.
- Touching tracked files: `git add` new ones first, regenerate the manifest
  LAST: `sh scripts/checksums.sh CHECKSUMS.sha256`. Skipping this leaves
  `scripts/doctor.py` check 9 FAILing, and no test catches it.
- Push policy: direct to main. Every gate (secret scan, dash scan, green
  tests, command verification) stays mandatory.

## Key commands (from PROJECT.md)

- Full gate: `BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py`
- Manifest, after `git add`: `sh scripts/checksums.sh CHECKSUMS.sha256`
- Install check: `bash scripts/verify-install.sh`
