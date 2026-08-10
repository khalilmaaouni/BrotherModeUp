# Alerts, open failures and unowned gaps

Status: CURRENT as of 2026-08-10 evening. No em or en dashes.
Every row names how it was found and what would close it.

---

# A. RED RIGHT NOW, and expected

| What | Evidence | Why it is red |
|---|---|---|
| `python3 tools/test_bm_effects.py` | `Ran 10 tests`, `FAILED (failures=3)` | RED ON PURPOSE. Each failure is a real defect, listed in section B. Do not weaken this test to make it pass |
| The full gate on the working tree | not run | `tools/test_bm_effects.py` exists but is not in `SUITES`, and `test_all.py` refuses a test file it does not know about |

The last FULL GREEN gate was at commit `c36bd00`:
`test_all: 2918 tests across 29 suites, 9 skipped, 559.8s wall. ALL GREEN`,
exit 0, clean tree, HEAD re-checked afterwards and unmoved.

---

# B. OPEN DEFECTS, each demonstrated

## B1. Documented read-only commands migrate an out-of-date database

SEVERITY: high. The product claims to be an assurance layer; an assurance layer
with ambiguous side effects of its own cannot be trusted to report on anything.

`Store.__init__` calls `_verify_schema_or_raise(migrate=True)`. Any command
constructing a writable Store against a database that is BEHIND rewrites it.

Demonstrated: a store forced to `schema_version 17`, handed to
`bm_project.py status --project-id nosuch`, exited 1 having found no such
project, and came back at `18` with a different md5.

Offenders as measured:
- `bm_docs.py tier`, whose docstring says "Writes nothing"
- `bm_project.py alert list`
- `bm_threads.py recommend`

CLOSES WHEN: each routes through `bm_store.ReadOnlyStore`
(`tools/bm_store.py:16345`) and `python3 tools/test_bm_effects.py` goes green
WITHOUT the test being weakened. An agent was doing this at handover; its result
is UNVERIFIED.

## B2. `bm_threads.py dashboard` ignores `--help` and rewrites STATE.md

SEVERITY: high, and it breaks the project's own pre-consent rule. `--help` is
the one command a nervous user runs to find out what something does BEFORE
letting it touch anything.

Two causes: `cmd_dashboard` (around line 871) accepts argv and never parses it,
so `--help` falls into the body; and it unconditionally calls
`_refresh_root_view` (around line 899), rewriting STATE.md.

CLOSES WHEN: argv is checked before any work, and the dashboard render is
genuinely read-only.

## B3. Stale fences from dead sessions block writers permanently

SEVERITY: high, and it is the clearest UNOWNED defect in the repository.

FIVE instances found on 2026-08-10 alone:
1. `README.md`, held by a dead session, blocking the most-read file
2. `SKILL.md`, held by a dead session
3. `SKILL.md` again, a SECOND fence from the same dead session. Closing the
   first was not enough; the hook simply reported the next one
4. the findings ledger
5. the README narrowing itself, where another session had claimed that exact
   work and died without doing it

Each was cleared by hand. Nothing in this repository sweeps for a fence whose
owning session is dead. The detection is trivial and nothing runs it.

CLOSES WHEN: a check lists active claims whose owning session is not alive, and
it runs somewhere anyone sees, for example at session start beside the
progress-page check.

## B4. The unattended preflight, MITIGATED tonight, NOT YET LANDED

The gate guarding unattended runs proved the write fence was on by reading an
environment variable. It never checked the hook fires. Under Codex the hook
never fires at all, so an unattended run passed all seven preconditions with
zero enforcement. Rated CRITICAL by an independent Codex audit.

STATUS: a live deny canary is built and its own suite passes
(`python3 tools/test_bm_controller.py`, `Ran 257 tests ... OK`). It is
UNCOMMITTED and has not passed a full gate, so the defect is NOT closed.

## B5. `v2.0.0-rc.3` was pushed unintentionally

`git push --tags` pushed every local tag, including an old release candidate
nobody meant to publish. Two older rc tags were rejected because local and
remote disagree on them, which means the tag history is inconsistent.

CLOSES WHEN: the founder decides whether to delete the stray tag and reconcile
the disagreeing ones. NEEDS A DECISION, not a fix.

---

# C. WATCHDOG ALERTS AND THEIR LIMITS

Armed tonight, and BOTH DIE WHEN THE SESSION THAT ARMED THEM ENDS. They live in
session memory, are written to no file, and nothing on disk enforces them.

- Cron `61f6f103`, twice hourly at minutes 13 and 43. Read-only by the founder's
  2026-08-09 decision, which overrides the watchdog skill's own clause telling
  an idle tick to resume unblocked work. Carries a stall rule and a hard stop at
  07:00.
- Monitor `brntx10kq`, foreign work on `origin/main`. This REPLACED monitor
  `b5pusgfev`, which fired twice on the session's own pushes because it tested
  whether origin MOVED rather than whether origin held commits this checkout
  lacks.

---

# D. KNOWN LIMITS THAT ARE PUBLISHED, NOT DEFECTS

These are stated in the shipped documentation rather than hidden, and are listed
here so a fresh session does not mistake them for new findings.

- The write fence does NOT gate shell commands. A write made by a shell command
  crosses a fence unrefused and is detected only afterwards by the audit.
- By default an UNCLAIMED path is allowed. Only claimed paths are refused.
  `BM_FENCE_MODE=enforced` and `BM_FENCE_STRICT=1` change that, and are not the
  shipped default by founder decision D3.
- The packaged-install suite SKIPS on a host that cannot build a virtualenv with
  pip. It reports three tests, three skipped, and says nothing below it was
  checked.
- Codex exec never fires PreToolUse, so the fence is advisory there. Measured,
  not inferred.

---

# E. THE HONEST GAP UNDER ALL OF IT

No BrotherMode capability has reached external verification. Nobody has counted
whether this product makes work better, faster or more reliable than working
without it. Ten outside builders and thirty externally attempted work items need
people and calendar, not code. Until that exists the defensible claim is the
narrow one: this is the agent layer that publishes the defects its own checks
find in itself.
