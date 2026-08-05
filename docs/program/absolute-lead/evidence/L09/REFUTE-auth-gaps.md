# REFUTE-auth-gaps: adversarial refutation of the three L09 authorisation narrowings

Date: 2026-08-06. Role: adversarial security refuter (refute-only, never confirm).
Target: tools/bm_store.py, tools/bm_controller.py, tools/bm_autonomy.py at the
state landed by FIX-L09-auth (docs/program/absolute-lead/evidence/L09/FIX-L09-auth-report.md).
Method: read the three files in full at the named line ranges, then DRIVE the
shipped CLIs (bm_store.py, bm_project.py, bm_autonomy.py, bm_controller.py) as
real subprocesses against five throwaway roots under `mktemp -d`, each with
BROTHERMODE_ROOT/BROTHERMODE_VAULT/HOME pointed inside the throwaway tree. The
live .brothermode store was never touched, no repo source file was edited, this
report is the only write.

Calibration rule honoured throughout: every ALLOW that would be a hole is shown
beside a known-bad that is REFUSED in the SAME rig under the SAME contract, so
"allowed" means hole, not broken rig.

## One-line verdicts

- CLAIM A (path floor): **REFUTED (1 exploitable hole, 1 defended store-layer gap).**
  The mechanism holds for the three NAMED surfaces under every spelling I threw
  at it, but the floor's stated purpose ("writing to the authorisation machinery
  itself ... un-authorisable by ANY contract wording") is defeated by an
  equivalent unlisted surface, `.claude/settings.local.json`, reproduced
  end-to-end through a dispatched write.
- CLAIM B (driver adoption): **REFUTED (3 holes, all reproduced).** Driver
  identity is a self-asserted, publicly-readable string, so the not-driver guard
  is an accountability speed-bump, not an access control; `plan` is unguarded and
  lets a foreign session inject the unit graph that the real driver then
  dispatches; a terminal run's late result is accepted from any session.
- CLAIM C (empty scope): **SURVIVED.** Every sign-layer refusal fires exactly as
  claimed. The only residual (unit-level empty write_scope) is disclosed by the
  implementer and grants nothing beyond the legitimately signed contract.

---

## CLAIM A: the path floor

### CONFIRMED A1 (exploitable, reproduced end-to-end): `.claude/settings.local.json` is not floored

`AUTONOMY_FLOOR_PATHS = (STORE_DIRNAME, ".git", ".claude/settings.json")`
(bm_store.py:3469). The set names `.claude/settings.json` but NOT
`.claude/settings.local.json`. In Claude Code the local settings file carries the
same schema (`permissions`, `hooks`) as the shared one and takes HIGHER
precedence, so a write there subverts the same authorisation system the floor
exists to protect. The floor lets it through at all three layers.

Sign layer and gate layer, same rig, `.` contract (`file-edit`, `allowed_path .`):

```
# gate-check under a '.' contract
.claude/settings.json            -> REFUSED-FLOOR governance-write     (calibration: floored)
.claude/settings.local.json      -> ALLOWED                            (HOLE)

# sign-time allowed_paths entry (--supersede)
.claude/settings.json        rc=1 -> refused: allowed_paths entry '.claude/settings.json' names a surface of 'governance-write'
.claude/settings.local.json  rc=0 -> allowed paths: 1                  (HOLE: signable)
```

Dispatch layer, the decisive test, calibrated against `.git/config` in the SAME
run under the SAME `.` contract:

```
# unit write_scope=['.git/config']  (known-bad)
step -> note: no selectable unit could be claimed this wave (... gate_check refused ...)
       gitscope   READY   fence=(none)      # never dispatched, never fenced

# unit write_scope=['.claude/settings.local.json']  (the hole)
step -> dispatched: settings
       controller_brief {... "write_scope": [".claude/settings.local.json"]}
       settings   DISPATCHED   fence=5096cc68f2c644e388e2063233019421
```

Under a single legitimately signed whole-project contract, a unit was gate-passed,
a fence was claimed over `.claude/settings.local.json`, and a brief authorising
the worker to write it was dispatched. The identically-shaped `.git/config` unit
was floored at gate_check and never left the wave. The difference is the floor's
incomplete path set, not the rig. This is a genuine authorisation-machinery write
the floor was meant to forbid.

Fix direction (not my job to land): add `.claude/settings.local.json` to
`AUTONOMY_FLOOR_PATHS`, or floor the whole `.claude` settings family. Consider any
enterprise/managed settings path too.

### CONFIRMED A2 (store-layer gap, defended in depth, NOT independently exploitable)

`Store.upsert_units` (bm_store.py:14223) validates a unit's `risk_class` against
the floor ids and canonicalises every `write_scope` entry, but it NEVER calls
`_governance_floor_hit` on those entries. So a unit row whose write_scope names a
floor surface is persisted verbatim:

```
plan unit write_scope=['.git/config']  -> count=1, row persisted:
   gitscope  risk=file-edit  write_scope=['.git/config']
```

This does not become a dispatched write: the dispatch route's
`_gate_check_write_scope` (bm_controller.py:2646) runs `store.gate_check` over
every write_scope path, and gate_check's check 5 floors `.git/config`
(REFUSED-FLOOR) BEFORE the allowance loop, so the unit never claims a fence (shown
above: fence=(none)). Worth a floor check in upsert_units for defense in depth,
but the gate is the standing wall and it holds.

### What HELD (spelling attacks on the three named surfaces, all REFUSED-FLOOR)

Every one of these was refused in the rig under a `.` contract, i.e. the broadest
allowance:

```
.git/config, .git, .git/hooks/pre-commit                 -> REFUSED-FLOOR
.brothermode, .brothermode/store.sqlite3                 -> REFUSED-FLOOR
sub/../.git/config, ./.git/config, .git/, .git/../.git/config -> REFUSED-FLOOR   (traversal collapses via _to_posix/realpath)
.git/*  (covering glob, sign time)                       -> refused path-is-floor
.GIT/config  (case-fold on darwin)                       -> REFUSED-FLOOR
blink/store.sqlite3  where blink -> .brothermode (symlink)-> REFUSED-FLOOR   (canonicalize_path realpath resolves the link)
```

Neighbours correctly stay ALLOWED: `.gitignore`, `.github/workflows/ci.yml`,
`.claude`, `.claude/other.json`, `src/app.py`. The hand-written-row vector is
covered because gate_check floors the CANDIDATE (check 5) regardless of what
allowed_paths a hand-written contract row claims; I confirmed `.git/config` is
REFUSED-FLOOR even under a `.` allowance and a covering glob.

The two hardest attacks that FAILED: (1) symlink-to-store (`blink -> .brothermode`),
because `_resolve_against_root` realpaths the link and the floor matches the
resolved `.brothermode/...`; (2) a hand-written `allowed_paths=['.git']` reaching a
write, because gate_check refuses the candidate before it ever reads allowed_paths.

### SUSPECTED, unreproduced (Windows-only)

`.git.` (trailing dot) and `.git ` (trailing space) as a candidate directory
lexically dodge `_governance_floor_hit` (they are neither equal to `.git` nor
`startswith(".git/")`), and I confirmed the ALLOWED verdict on darwin:

```
.git.config, .git./config  -> ALLOWED
```

On macOS/Linux `.git.` is a genuinely different name, so this is NOT a bypass
there (the write would land in a real directory named `.git.`, not `.git`). Only
Windows collapses trailing dots/spaces at the Win32 layer, and there
`canonicalize_path`'s `os.path.realpath` almost certainly collapses `.git.` to the
real `.git` before the floor runs, closing it. I could not reproduce Windows
semantics on this machine; flagged for a Windows run, expected to hold.

### DISCLOSED (not a new hole)

`.` and `*` candidates are ALLOWED at gate under a `.` contract (they reduce to
the empty/`.` coverage key and fall through). The report discloses this in
section 7 and the git-containment fence hook is the standing second wall; I did
not find a way to turn an ancestor candidate into a concrete write to a protected
file that the gate did not otherwise refuse.

---

## CLAIM B: driver adoption

### CONFIRMED B1 (reproduced): session identity is forgeable and public, so not-driver is not an access control

`_refuse_foreign_driver` (bm_controller.py:974) compares `run["session_id"]` to
`self.session_id`, and `self.session_id` comes straight from the caller-supplied
`--session-id` (`_actor`, bm_controller.py:4508:
`session_id = kv.get("session-id") or ("cli-" + uuid...)`). The driver's session
id is not a secret: `status --json --raw` prints it.

```
# begin as driver sess-A, then read it back as any reader:
status --json --raw -> run.session_id = 'sess-A'

# a genuinely different session is correctly refused (calibration):
step  --session-id sess-B  -> refused: ... driven by session 'sess-A' ... this engine is session 'sess-B' ... not-driver

# an attacker who copies the public id drives the run, no adopt, no refusal:
step  --session-id sess-A  (from a DIFFERENT process, controller-id ctrlX)
   -> controller_brief {... "unit_id": "u1" ...}
      run ...: state EXECUTING     # dispatched foreign work, zero audit trail
```

The guard tells an honest second process to run `adopt`; it does nothing against a
process that reads the public session id and asserts it. adopt at least records
`controller.run.adopted`; the impersonation path records nothing. Driver ownership
is accountability, not authorisation.

### CONFIRMED B2 (reproduced end-to-end): `plan` is unguarded, so a foreign session injects the graph the real driver dispatches

`ControllerEngine.plan` (bm_controller.py:1407) calls `_run_or_refuse` and
`_refuse_if_paused` but NOT `_refuse_foreign_driver`. Disclosed in the report
section 7; here it is reproduced through the CLI:

```
# driver sess-A begins a run, leaves it NEW
start --session-id sess-A -> run 27055... state NEW

# foreign sess-EVIL plans the whole graph on a run it never began:
plan --units-json '[{"unit_id":"evil","objective":"attacker-authored unit on a foreign run",...,"write_scope":["src/pwned.py"]}]' --session-id sess-EVIL
   -> count=1, rc=0            # accepted, no not-driver refusal
   driver.session_id='sess-A'  state=READY
   unit evil  obj=attacker-authored unit on a foreign run  scope=['src/pwned.py']

# the legitimate driver's next step DISPATCHES the attacker's unit under sess-A:
step --session-id sess-A -> controller_brief {... "unit_id": "evil", "objective": "attacker-authored unit on a foreign run" ...}
```

`plan` is the single most powerful mutation (it defines what work runs and rewrites
the unit graph, cascading DONE units) and it is the one door left without the
ownership check. The driver identity is unchanged, so the injected work runs under
the honest driver's session. `check_timeouts` (the other disclosed unguarded
method) is not exposed as a CLI command (`known: adopt, complete, plan,
record-result, resume, start, status, step, stop`), so it has no shipped door,
but `plan` does.

### CONFIRMED B3 (reproduced): a terminal run's late result is accepted from any session

`receive_result` only calls `_refuse_foreign_driver` for a non-terminal run
(bm_controller.py:1969). Disclosed in the report; reproduced:

```
# non-terminal run, foreign sess-B (calibration): REFUSED
record-result --dispatch-id <open> --session-id sess-B -> refused: ... not-driver

# driver stops the run (STOPPED, terminal), then foreign sess-B records anyway:
record-result --dispatch-id <same> --session-id sess-B
   -> dispatch <id> rejected; the unit re-queues ...    # accepted and processed, no not-driver refusal
```

Bounded: it records a dispatch outcome / re-queue on a finished run, it does not
resurrect the run into new dispatch. Lower severity than B1/B2 but it is a foreign
write under the guard the claim says covers `receive_result`.

### adopt itself

adopt is open to ANY session: `adopt --project p1 --actor-name X --session-id
sess-EVIL2` displaced driver `sess-A` (`adopted: true, previous_session_id:
sess-A`), after which `sess-A` was refused on its own run. This is the intended
"one deliberate takeover path" and it records the handover, so it is not a defect,
but it confirms the point: taking a run over is available to anyone, audited via
adopt or unaudited via B1.

### What HELD

step, receive_result and stop all correctly refused `not-driver` for a genuinely
different session (`sess-B`) that did not copy the driver id. The guard's stated
logic is exactly as claimed; its weakness is that the identity it compares is
self-asserted and public.

---

## CLAIM C: empty allowed_paths

### SURVIVED at the sign layer (every case as claimed)

Signing with an empty `allowed_paths`:

```
writing classes, each alone -> REFUSED no-write-scope:
  file-edit, file-create, file-move, build, test-run, local-commit, local-branch, app-drive

read-only classes -> SIGNED:
  read-only-inspect ; browser-read ; read-only-inspect+browser-read

mixed browser-read + file-edit -> REFUSED no-write-scope (the writing class triggers it)
no risk classes at all         -> SIGNED (degenerate: authorises nothing, bounds nothing)
```

I looked for a WRITING class the fix treats as read-only, and for a read-only
class that can cause a write. I found neither: `app-drive`, `build`, `test-run`,
`local-commit`, `local-branch` are all refused with an empty scope (treated as
writing), and the only read-only classes are the two named. No misclassification.

### CONFIRMED C-residual (disclosed, non-escalating)

`upsert_units` does not require a write_scope, so a unit with a WRITING risk_class
and an EMPTY write_scope is accepted and dispatchable:

```
plan unit risk=file-edit write_scope=[] -> planned count=1
   noscope  risk=file-edit  write_scope=[]
```

The report admits this ("the UNIT-level empty write_scope is still open"). It does
NOT escalate past the signed contract: a unit's writes are gate-checked against the
CONTRACT's allowed_paths, and the contract that reaches this state was legitimately
signed with a real scope (an empty-scope writing contract is refused at sign, per
above). An empty unit write_scope removes the per-unit fence, not the contract
boundary, so it grants nothing the founder did not already authorise for the
project. Two hardest attacks that failed here: the mixed browser-read+file-edit
contract still refused, and app-drive (the most "read-ish" of the writing classes)
still refused.

---

## Coverage: what I did NOT fully close

- The Windows trailing-dot/space floor vector (A, SUSPECTED) is reasoned, not
  reproduced; needs a Windows run.
- I did not exercise the actual worker writing the dispatched
  `.claude/settings.local.json` file to disk (no live worker in the rig); I proved
  authorisation up to and including the dispatched brief and the claimed fence,
  which is the point the floor is supposed to stop.
- I did not audit the fence hook (tools/bm_fence_hook.py) beyond observing it is
  the disclosed second wall; it is outside the three named files. The A1 hole does
  not depend on it (the write is affirmatively authorised, not merely un-blocked).
- check_timeouts is unguarded but unreachable via the shipped CLI; a future wiring
  of it would inherit the B gap.

## Rig provenance

Five throwaway roots under `mktemp -d`, BROTHERMODE_ROOT set to each; init via
`bm_store.py init`, project via `bm_project.py start`, contracts via
`bm_autonomy.py sign`, runs via `bm_controller.py start/plan/step/record-result/stop/adopt`.
Live store untouched, no repo source edited.
