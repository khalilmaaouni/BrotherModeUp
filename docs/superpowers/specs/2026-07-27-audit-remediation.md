# Audit remediation: the loops, and the root causes they close

External adversarial audit, 2026-07-27, against branch `v2` at `6dd4630`. Verdict
NO-GO: 8 release blockers, 9 high-risk. Founder instruction, verbatim: "fix all of
them in a coherent and consistent way at the source rather than at surface one by
one."

That instruction is the whole design. Seventeen findings are not seventeen bugs.
They are a small number of missing primitives, each absent from several places at
once. Patching seventeen sites would leave site eighteen open, which is the same
mistake this project already made with the database-handle leak: twelve call sites
fixed by hand, and the thirteenth would have leaked again until a mechanical stop
was added.

## The root causes, and which findings each one closes

| # | Root cause | Closes | The fix, stated once |
|---|---|---|---|
| R1 | No filesystem boundary primitive. The sqlite layer refuses symlink and hardlink escapes; nothing else does. | 2A, 2B, 2C, 3, 4 | ONE `safe_open`/`safe_write` primitive that lstats every existing component, refuses symlinks and hardlinks, proves the resolved parent stays inside the project, uses `O_NOFOLLOW` where available, and creates owner-only. Every writer routes through it, enforced by a structural test that FAILS on a raw `open()` for a project path. |
| R2 | Recovery truth is not event-scoped. A receipt answers "did this session ever snapshot", not "is the current work safe". | 1, 13 | One-shot compaction EVENT receipt: event uuid, ref, commit sha, tree fingerprint, timestamp, session, success state. Pending on attempt, successful only after the ref is written AND re-read. The hint consumes the specific event once and re-resolves the ref to the recorded sha. Refs move under a per-worktree lock with compare-and-swap. |
| R3 | Destructive response to non-destructive errors. Every non-busy `OperationalError` means corruption, and read-only shares the writable quarantine path. | 7 | Read-only NEVER mutates: no quarantine, no rename, no move. Quarantine only on sqlite result codes that specifically mean corruption or not-a-database. Copy evidence, never move the only source, during any health check. |
| R4 | Identity flows through the REDACTED boundary. Lookup reads the safe dump, so a redacted name is unfindable, and ambiguity is resolved by guessing. | 9, 10 | An internal raw exact-name query returning lifecycle uuid plus structural metadata only. Redaction stays at the external output boundary. More than one candidate ALWAYS refuses and demands a lifecycle prefix. |
| R5 | Root resolution prefers a distant marker over the nearest boundary. One tool has a private guard; the others do not. | 11 | Nearest project boundary wins, centrally. A nearer `.git` disagreeing with a more distant `.brothermode` REFUSES and asks for an explicit root. The autosave module's private guard is deleted in favour of the shared one. |
| R6 | State written outside the transaction. Handover appends race a whole-file replacement. | 12 | Handovers stored transactionally in sqlite and GENERATED into the view. Nothing appends to a generated file. |
| R7 | The raw store can live somewhere git will publish it. `.git/info/exclude` cannot untrack, and its failure is advisory. | 5 | Refuse to open or create when the store, its directory, or its sidecars are git-tracked, or when ignore status cannot be established. |
| R8 | The single-writer promise is a ledger, not a gate. | 8 | `--files` required for a writer thread, explicit `--read-only` for the rest, plus a PreToolUse hook that canonicalizes the write target and blocks it unless the session owns a matching active claim. |
| R9 | Release identity is ambiguous: an immutable tag and a moving branch both call themselves `2.0.0-rc.1`. | 6 | Withdraw `rc.1`, bump to `rc.2`, regenerate checksums LAST, tag only from a commit whose full matrix is green, and pin the install to that tag. |
| R10 | The suite making the strongest safety claim is not in CI, and fail-fast hides platform evidence. | 14, 15 | Autosave suite on every platform, `fail-fast: false`, and a Python hook dispatcher so the documented install path is identical on Windows. |
| R11 | Security documentation describes code that no longer exists. | 17, 16 | SECURITY.md regenerated against the real data flows, and the secret denylist replaced with a combination of git-ignore status, an expanded denylist, and a warning that lists newly captured untracked files. |

## The loops

Each loop has a done-check and kill criteria. No loop starts before the previous
one's check passes.

- **Loop A, VERIFY (read-only, parallel).** Every finding confirmed or refuted
  against the real code with file:line evidence and, where possible, an executed
  reproduction. Done-check: every one of the 17 carries a verdict and evidence.
  Kill criterion: a cluster that cannot reach the code at all.
  *An audit written without a working clone will contain wrong findings. Fixing a
  finding that is not real costs correctness twice: once in the wasted change, once
  in the test that then locks the wrong behaviour in.*
- **Loop B, DESIGN.** One written design per CONFIRMED root cause, in this file,
  before any code. Done-check: each design names the primitive, its call sites, and
  the structural test that will stop call site N+1.
- **Loop C, IMPLEMENT (serial, one writer per fence).** Primitives first, then call
  sites, then deletions of the now-redundant private guards. Done-check: three
  suites green after every landing.
- **Loop D, ADVERSARIAL TESTS.** The auditor's 20 mandatory regression tests, each
  calibrated by reinjecting the defect and proving the test fails.
  *An uncalibrated test is decoration; this project has already shipped two checks
  that could not fail.*
- **Loop E, GATE.** Three suites plus autosave on Linux, macOS and Windows with
  fail-fast disabled.
- **Loop F, RELEASE.** Withdraw rc.1, bump version, regenerate checksums last, tag
  from the green commit only.
- **Loop G, RE-AUDIT.** Independent adversarial pass against all 17 original
  findings plus whatever the fixes introduced.

## Loop A result, 2026-07-27: every finding CONFIRMED, several worse than reported

Six read-only agents, one per cluster, each required to quote file:line and to RUN
the attack rather than argue it. Zero refuted. What the executions actually showed:

- **2A** a handover block was written into a file OUTSIDE the project root.
- **2B** an external file's contents were copied INTO the repo as `STATE.md.bak-*`.
  Correction to the audit: the final write uses `os.replace`, so it replaces the
  symlink rather than writing through it. The escape is read-and-copy-inward, not
  overwrite-outward. It is still a disclosure, and in a user project
  `STATE.md.bak-*` is untracked, so a routine `git add -A` commits it.
- **2C** thread files landed outside the root, and a symlinked `outbox.md` gave a
  general-purpose append primitive (`checkpoint --next "PWNED-APPEND"` exited 0).
- **3** the MCP server, asked ONLY about project B, returned project A's records
  and fences with `isError=False`.
- **4** the install verifier passed with a planted unmanifested `tools/json.py`
  symlink, run against a real throwaway install.
- **8B, NOT in the original audit and worse than what was reported:** session
  identity is a caller-supplied string AND the owning value is printed in
  plaintext into the file every session reads. The ownership guard compares a
  public value against itself.

Two nuances that change the fix, and would have caused a regression if missed:

1. **Finding 11 is a trap.** The "distant marker beats a closer `.git`" precedence
   is DELIBERATE and fixes an earlier bug class (F2 / F42 / F2b): it stops a
   vendored submodule shadowing the real project root. Inverting it would reopen
   that. The fix is to move the containment check into `resolve_root` as an
   opt-in, not to flip precedence.
2. **The primitives already exist and are correct.** `_refuse_if_symlink_escape`
   and `_refuse_if_hardlinked` are sound; they are simply never called for
   `STATE.md`, backups, `threads/`, or the MCP copy. So R1 is enforcement and
   routing, not new security code. Writing a second symlink checker beside a
   working one would itself be the defect this project keeps hitting.

## Fence registry, wave 1 (disjoint files, three writers)

| Fence | Files | Scope |
|---|---|---|
| W1-scripts | `scripts/verify-install.sh`, `scripts/checksums.sh`, add-only in `tools/test_bm.py` | findings 4, 4B |
| W1-mcp | `mcp/bm_mcp_server.py`, `mcp/README.md`, add-only in `tools/test_bm.py` | findings 3, 3b, 3c |
| W1-store | `tools/bm_store.py`, `tools/test_bm_store.py` | findings 2B (funnel), 7 |

Wave 2, after W1-store lands and exports the funnel: `bm_threads.py` (2A, 2C, 9,
10, 12, 8), `bm_autosave.py` (1, 13, 16), then root containment (11), git-tracked
refusal (5), release identity (6), Windows hook dispatcher (15), docs (17).

## Standing constraints

- No em dashes or en dashes anywhere.
- Every fix reproduced by execution BEFORE it is written.
- Every test calibrated in both directions before it is trusted.
- A finding that turns out to be wrong is recorded as REFUTED with the line that
  refutes it, never quietly dropped.
