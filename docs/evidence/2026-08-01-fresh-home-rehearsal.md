# Fresh-home install rehearsal, 2026-08-01 (Loop 3 design D-6, WP-F)

Status: CURRENT (evidence record; superseded only by a later rehearsal file)

Covers decision D-6 in
docs/superpowers/specs/2026-08-01-loop3-consent-install-design.md: "a
scripted fresh-HOME rehearsal ... driving: clone-path install per docs
alone, setup consent flow, doctor all-PASS, one project started via the
Loop 2 CLI, uninstall clean. Recorded as evidence with the exact commands."
The harness is scripts/rehearse_fresh_install.py (new, Python 3.9 stdlib
only). Every command below ran on this machine, inside temporary
directories with HOME and BROTHERME_CONFIG overridden; the real HOME and
the real ~/.claude were never touched (the harness strips
BROTHERMODE_VAULT, BROTHERMODE_ROOT, BROTHERMODE_REGISTRIES and
BROTHERME_CONFIG from the inherited environment before setting HOME and
BROTHERME_CONFIG to paths under a fresh mkdtemp directory).

## Two runs, both pasted in full, neither edited after the fact

Two invocations of the same script are recorded here, not one. The first
is the plain command, unmodified, run first. Its step 2 (`python3
tools/test_all.py`) reports two of eleven suites red at the current
commit, for reasons traced in the section below and unrelated to the
install/consent/CLI mechanics this rehearsal exists to check. The second
invocation adds `--skip-gate`, which the work order names as an
acceptable form for this file's own required command: "python3
scripts/rehearse_fresh_install.py (or with --skip-gate, disclosed) exits
0." Both are shown so the gate finding is visible, not hidden behind the
second invocation.

## Run 1: default mode, the gate included

Command:

    python3 scripts/rehearse_fresh_install.py

Result: 6 of 7 steps report PASS, 1 reports FAIL, exit code 1. Wall time
for the gate step alone: 128.6s (not a time problem; the two suite
failures are content, not a timeout).

Full numbered output:

```
rehearse_fresh_install.py: fresh-HOME clone-path rehearsal
  temp root: /var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/bm-rehearsal-9dktcd8g
  fake HOME: /var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/bm-rehearsal-9dktcd8g/fakehome
  gate: RUN

[1/7] copy (clone stand-in) into fakehome/.claude/skills/brothermode: PASS
    237 files copied from /Users/.../BrotherModeUp to /var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/bm-rehearsal-9dktcd8g/fakehome/.claude/skills/brothermode
    disclosed deviation: this is a plain recursive copy, not git clone. It excludes .brothermode, .git, node_modules, the same list scripts/checksums.sh and scripts/verify-install.sh use.
    present at target: SKILL.md, VERSION
[2/7] python3 tools/test_all.py from the copy: FAIL
    exit code 1, ALL GREEN not found in the output
    command: python3 /var/folders/.../fakehome/.claude/skills/brothermode/tools/test_all.py (cwd=.../fakehome/.claude/skills/brothermode)
    elapsed: 128.6s, exit code: 1
    test_all: 11 suites, serially, one process each, 900s timeout each
      running test_bm_docs.py          FAIL  135 tests   14.2s
      running test_bm_store.py         OK    692 tests   21.8s
      running test_bm_project.py       OK     20 tests    5.1s
      running test_bm_fence_hook.py    OK     50 tests    1.5s
      running test_install.py          FAIL   67 tests   23.4s
      running test_bm_consent.py       OK     28 tests    5.1s
      running test_bm_runtimes.py      OK     35 tests    2.0s
      running test_bm_autosave.py      OK     34 tests   16.7s
      running test_bm_ledger.py        OK     15 tests    1.5s
      running test_bm_schema.py        OK     20 tests    0.5s
      running test_bm.py               OK    239 tests   36.6s
    FAILURES (2 of 11 suites):
      test_bm_docs.py: ---------------------------------------------------------------------- | Ran 135 tests in 13.972s | FAILED (failures=1, skipped=5)
      test_install.py: ---------------------------------------------------------------------- | Ran 67 tests in 22.968s | FAILED (failures=5)
    test_all: 1335 tests across 11 suites, 6 skipped, 128.5s wall. 2 SUITE(S) FAILED
[3/7] scripts/install.py against the fake settings.json: PASS
    exit code 0, five hooks wired into .../fakehome/.claude/settings.json, smoke line present
    dry-run exit code: 0
    real-run exit code: 0
    hooks: 0 BrotherMode entry(ies) replaced, 5 installed: SessionStart, SessionEnd, Stop, PreCompact, PreToolUse
    smoke: the fence hook ran end to end and exited 0; every file a hook command names exists.
[4/7] scripts/setup.py flag mode consent, plus the vault-template copy: PASS
    config at .../fakehome/.brotherme/config.json: setup_complete True, installation_mode clone, vault_path .../fakehome/BrotherModeVault
    vault-template copied to .../fakehome/BrotherModeVault (10 files), mirroring docs/SETUP.md Step 3
    exit code: 0
    [1/10] fence hook wired and live: PASS
    [2/10] VERSION matches the plugin manifest: PASS
    [3/10] python3 3.9+ and git are available: PASS
[5/7] scripts/doctor.py --json checks: PASS
    status PASS for: fence, consent, vault, duplicate_install, settings_json
    exit code: 1
    fence              PASS
    version            PASS
    runtime            PASS PASS: python3 3.9.6, git on PATH.
    consent            PASS
    vault              PASS
    duplicate_install  PASS
    store              SKIP SKIP: no project store under the current directory (none created yet)
    mode_wiring        PASS
    checksums          FAIL FAIL: 31 of 191 listed file(s) do not match CHECKSUMS.sha256: .github/workflows/tests.yml does not match its checksum; .gitignore does not match; and more
    settings_json      PASS
    checksums status recorded as-is: FAIL (a live development tree, not a clean checked-out release, so CHECKSUMS.sha256 disagreeing is expected here; this key is not in the asserted set)
[6/7] one project through tools/bm_project.py: PASS
    nine CLI calls all returned exit code 0; CANVAS.md, DELIVERY-PACKET.md and the store are present at the documented paths
    init -> bm_store: initialized .../fakehome/projects/fresh-home-demo/.brothermode/store.sqlite3
    start -> {"forecast_id": null, "project_id": "fresh-home-demo", "task_ids": []}
    task add -> {"task_id": "e294872464724220a0a9ac63d4db0109"}
    task transition to ready -> {"status": "ready", ...}
    task transition to active -> {"status": "active", ...}
    task transition to awaiting review -> {"status": "awaiting review", ...}
    review -> {"evidence_id": "89de121e1314458b84c82e9fcfd3aabf", "status": "verified", ...}
    status -> project fresh-home-demo: Fresh Home Demo; open tasks by state: verified: 1
    next -> no recommended next task: 0 task(s) currently in state 'ready'
    deliver --partial -> {"closed_tasks": 0, "partial": true, "total_tasks": 1}
    CANVAS.md, DELIVERY-PACKET.md and .brothermode/store.sqlite3 all present under fakehome/projects/fresh-home-demo
[7/7] scripts/uninstall.py --remove-consent: PASS
    hooks_gone, consent_gone, vault_untouched all true
    hooks: removing SessionStart[0], SessionEnd[0], Stop[0], PreCompact[0], PreToolUse[0]
    hooks: 5 entry(ies) removed; every other hook left in place, in order.
    consent: --remove-consent was given; removing it.
    consent: removed .../fakehome/.brotherme/config.json
    hooks_gone=True consent_gone=True
    vault_untouched=True (11 file(s) before, 11 after, byte-size manifest identical: True)

rehearse_fresh_install.py: 6/7 step(s) PASS. NOT ALL GREEN
EXIT:1
```

(Paths abbreviated to `.../fakehome/...` above for readability; the raw
run wrote the full absolute temp path on every line. Nothing was edited
out of the substance: every step's PASS/FAIL line and every assertion
result above is verbatim.)

## Tracing the two step-2 suite failures

Both failures were reproduced in a second, disposable, git-less copy of
the repository built the same way step 1 builds one (`rsync -a --exclude
.git --exclude .brothermode --exclude node_modules`), so this trace never
touched the live tree or a concurrent session's own gate run.

**test_bm_docs.py, 1 failure: `test_the_public_install_target_tag_resolves_in_git`.**
This test asserts that the tag `v2.0.0-rc.9` (the pinned install target
docs/QUICKSTART.md and docs/SETUP.md point at) resolves inside the git
repository. It does, in the real repository (`git rev-parse --verify
v2.0.0-rc.9` succeeds there). It cannot in the copy, because copy-stands-
in-for-clone (step 1's disclosed deviation) excludes `.git` entirely, so
there is no git history at all in the tree this test runs against. This
failure traces directly and only to the copy deviation, not to anything
wrong with the actual product. A real `git clone` (the documented command
this rehearsal stands in for) would carry the tag and this test would
pass against it.

**test_install.py, 5 failures: the `DoctorCase` calibration tests.**
`test_calibrated_1_healthy_install_passes`,
`test_calibrated_3_a_hook_that_never_denies_is_detected`,
`test_calibrated_4_a_hook_that_gates_only_edit_is_detected`,
`test_calibrated_5_a_hook_that_bricks_by_exit_code_is_detected`, and
`test_the_simulation_leaves_nothing_behind` each assert that
`scripts/doctor.py`'s overall return code is 0 against a throwaway install
these tests build for themselves (their own settings.json, consent config,
and vault under a fresh temp directory, unrelated to step 1's copy). Each
of the five fails on that same assertion, and the doctor output attached
to the failure names the reason: check 9, `CHECKSUMS.sha256 self-check`,
reports FAIL (31 of 191 listed files do not match). This is not a copy
artifact: `git log -1 --format=%H -- CHECKSUMS.sha256` shows the manifest
was last regenerated at commit `8b98bbb`, and `git rev-list --count
8b98bbb..HEAD` (HEAD is `7aae09c` at the time of this rehearsal) returns
15. CHECKSUMS.sha256 is fifteen commits behind HEAD. `doctor.py`'s
`check_checksums` only downgrades this to SKIP when git reports the
working tree as literally dirty (uncommitted local edits); a clean tree at
a newer commit than the manifest still gets a real, honest FAIL, which is
exactly what these five tests are tripping on. This is a real, standing
property of the tree at this commit, independent of the copy method, and
it is out of scope for this rehearsal's allowed files
(scripts/rehearse_fresh_install.py and this evidence file only): flagged
separately for whoever owns the checksum manifest to regenerate it.

So each finding above traces to a distinct cause: one is inherent to the
disclosed copy-for-clone stand-in, the other is a real, independently
confirmed staleness in this development tree's CHECKSUMS.sha256, already
covered by the "checksums recorded as-is, not asserted" carve-out in this
rehearsal's own step 5.

## Run 2: `--skip-gate`, disclosed

Command:

    python3 scripts/rehearse_fresh_install.py --skip-gate

This is not a substitute that erases Run 1's result above. The work order
names `--skip-gate` as one of two acceptable forms for this file's own
required command. Run 1, above, already traces both gate failures to
causes outside the install, consent, CLI, and uninstall mechanics this
file exists to rehearse, which is why this second invocation is shown as
a supplement rather than a replacement. Result: 7 of 7 steps report PASS,
exit code 0.

Full numbered output:

```
rehearse_fresh_install.py: fresh-HOME clone-path rehearsal
  temp root: /var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/bm-rehearsal-i7s4g9uh
  fake HOME: /var/folders/bx/4mv547hj3nxdv72rb00whvjsgmklcm/T/bm-rehearsal-i7s4g9uh/fakehome
  gate: SKIPPED (--skip-gate)

[1/7] copy (clone stand-in) into fakehome/.claude/skills/brothermode: PASS
    237 files copied from /Users/.../BrotherModeUp to .../fakehome/.claude/skills/brothermode
    disclosed deviation: this is a plain recursive copy, not git clone. It excludes .brothermode, .git, node_modules, the same list scripts/checksums.sh and scripts/verify-install.sh use.
    present at target: SKILL.md, VERSION
[2/7] python3 tools/test_all.py from the copy: PASS
    skipped with --skip-gate, a disclosed deviation from the default; the default runs this suite
[3/7] scripts/install.py against the fake settings.json: PASS
    exit code 0, five hooks wired into .../fakehome/.claude/settings.json, smoke line present
    dry-run exit code: 0
    real-run exit code: 0
    hooks: 0 BrotherMode entry(ies) replaced, 5 installed: SessionStart, SessionEnd, Stop, PreCompact, PreToolUse
    smoke: the fence hook ran end to end and exited 0; every file a hook command names exists.
[4/7] scripts/setup.py flag mode consent, plus the vault-template copy: PASS
    config at .../fakehome/.brotherme/config.json: setup_complete True, installation_mode clone, vault_path .../fakehome/BrotherModeVault
    vault-template copied to .../fakehome/BrotherModeVault (10 files), mirroring docs/SETUP.md Step 3
    exit code: 0
    [1/10] fence hook wired and live: PASS
    [2/10] VERSION matches the plugin manifest: PASS
    [3/10] python3 3.9+ and git are available: PASS
[5/7] scripts/doctor.py --json checks: PASS
    status PASS for: fence, consent, vault, duplicate_install, settings_json
    exit code: 1
    fence              PASS
    version            PASS
    runtime            PASS PASS: python3 3.9.6, git on PATH.
    consent            PASS
    vault              PASS
    duplicate_install  PASS
    store              SKIP SKIP: no project store under the current directory
    mode_wiring        PASS
    checksums          FAIL FAIL: 31 of 191 listed file(s) do not match CHECKSUMS.sha256 (same finding as Run 1, traced above)
    settings_json      PASS
    checksums status recorded as-is: FAIL (a live development tree, not a clean checked-out release, so CHECKSUMS.sha256 disagreeing is expected here; this key is not in the asserted set)
[6/7] one project through tools/bm_project.py: PASS
    nine CLI calls all returned exit code 0; CANVAS.md, DELIVERY-PACKET.md and the store are present at the documented paths
    init -> bm_store: initialized .../fakehome/projects/fresh-home-demo/.brothermode/store.sqlite3
    start -> {"forecast_id": null, "project_id": "fresh-home-demo", "task_ids": []}
    task add -> {"task_id": "5151d690249749f7af56dbd604f4dc4c"}
    task transition to ready -> {"status": "ready", ...}
    task transition to active -> {"status": "active", ...}
    task transition to awaiting review -> {"status": "awaiting review", ...}
    review -> {"evidence_id": "9322bb939bdf4122943c1b1aeedcd754", "status": "verified", ...}
    status -> project fresh-home-demo: Fresh Home Demo; open tasks by state: verified: 1
    next -> no recommended next task: 0 task(s) currently in state 'ready'
    deliver --partial -> {"closed_tasks": 0, "partial": true, "total_tasks": 1}
    CANVAS.md, DELIVERY-PACKET.md and .brothermode/store.sqlite3 all present under fakehome/projects/fresh-home-demo
[7/7] scripts/uninstall.py --remove-consent: PASS
    hooks_gone, consent_gone, vault_untouched all true
    hooks: removing SessionStart[0], SessionEnd[0], Stop[0], PreCompact[0], PreToolUse[0]
    hooks: 5 entry(ies) removed; every other hook left in place, in order.
    consent: --remove-consent was given; removing it.
    consent: removed .../fakehome/.brotherme/config.json
    hooks_gone=True consent_gone=True
    vault_untouched=True (10 file(s) before, 10 after, byte-size manifest identical: True)

rehearse_fresh_install.py: 7/7 step(s) PASS. ALL GREEN
EXIT:0
```

## Limits (what this does not cover)

- **One physical machine, the author's own environment.** Every command in
  both runs above executed on this same machine, under this same user
  account, with this same Python (3.9.6) and this same git. No second
  machine, no second operating system, no second account.
- **Copy stands in for git clone.** Step 1 is a recursive filesystem copy
  excluding `.git`, `.brothermode`, and `node_modules`, not the documented
  `git clone --branch v2.0.0-rc.9 --depth 1 ...` command. This was a
  deliberate choice (testing this machine's install code, not GitHub or
  the network) and it is disclosed inline in the script's own output on
  every run, plus it is the direct cause of one of the two Run 1 gate
  failures (the git-tag test traced above).
- **No naive users.** Every command here ran under an agent following the
  docs literally, never a person encountering this project for the first
  time, unsure what a terminal is, or copy-pasting a command wrong. Five
  naive users trying the real path is Loop 8's job, not this file's.
- **The plugin path is not exercised at all here.** This rehearsal is the
  clone path only (`/plugin marketplace add` and `/plugin install` are a
  separate, single-observation path recorded in
  docs/evidence/2026-07-31-first-plugin-install.md, still not reverified
  since).
- **Checksum check: recorded as-is, not asserted, and the result is FAIL.**
  31 of 191 files in CHECKSUMS.sha256 do not match, both runs. Cause
  traced above: the manifest is fifteen commits behind HEAD (`8b98bbb` to
  `7aae09c`), a real property of this development tree independent of the
  copy method. This is expected on a mid-development tree per this work
  package's own instructions and is why `checksums` is excluded from the
  five required-PASS keys (`fence`, `consent`, `vault`, `duplicate_install`,
  `settings_json`) that step 5 does assert.
- **The gate (`python3 tools/test_all.py`) is red at this commit**, for
  the two reasons above (one copy-only, one a real, standing tree issue).
  This file states that plainly instead of relying only on the
  `--skip-gate` invocation to look green.
- **Sample size of one project, one task.** Step 6 drives one project
  through three of the ten canonical lifecycle states (ready, active,
  awaiting review) plus one review call to `verified`, then delivers
  `--partial` since the task never reaches the terminal `closed` state.
  Deeper lifecycle paths (blocked, a full walk to closed, --allow-second
  for a genuine second project) are not exercised here.
