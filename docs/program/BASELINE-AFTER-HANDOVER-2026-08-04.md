# Baseline after the handover program, 2026-08-04

Status: CURRENT as of 2026-08-04.

This is the entry-gate artifact the positioning execution plan requires
before any of its phases may claim a before-and-after improvement. Every
number here was produced by a command run on 2026-08-04 and is quoted from
that command's output, not remembered.

## The release identity

- Stable version: 2.0.0, the first public release.
- Immutable tag: `v2.0.0`, an annotated tag object `1af241d` resolving to
  commit `5158dcf` on the remote (`git ls-remote origin refs/tags/v2.0.0
  refs/tags/v2.0.0^{}`).
- `main` after the release: `ddf6c94` (the immediate development-identity
  bump to `2.0.1.dev1` required by version-law rule 3), pushed and verified
  (`git rev-parse HEAD` equals `@{u}` equals `ls-remote origin main`).
- The repository carries exactly ONE branch: `git ls-remote --heads origin`
  returns `refs/heads/main` and nothing else. Four contained branches were
  deleted after containment was proven twice (zero unique commits versus
  main, each tip an ancestor of main), and the PR #5 feature branch was
  deleted at merge.

## Gate and CI at the release

- Full local gate on the closure tree after its last edit (`91bc596`, which
  main merges unchanged as `ef25c1f`): `test_all: 1573 tests across 15
  suites, 6 skipped, 177.2s wall. ALL GREEN`, exit 0.
- Full local gate on the release commit `5158dcf`: 14 of 15 suites OK and
  exactly ONE red test, `test_the_public_install_target_tag_resolves_in_git`,
  by design, in the window before the tag existed. It is green now that
  `v2.0.0` resolves (`python3 -m unittest ...` reran OK after the tag push).
- Full local gate on `ddf6c94` (post-bump): `test_all: 1573 tests across 15
  suites, 6 skipped, 428.9s wall. ALL GREEN`, exit 0.
- GitHub Actions on the release SHA `5158dcf`: run `30908897689` completed
  SUCCESS with all eleven jobs green individually (gate; store and suite on
  ubuntu, macos, windows, Python 3.9 and 3.x), read directly by job.
- GitHub Actions on `91bc596` (PR #5 head): run `30906411852`, all eleven
  jobs green, read directly.

## Install, update, doctor, uninstall

- Verify-by-clone probe of the tag, hermetic (HOME, BROTHERMODE_VAULT and
  BROTHERSBE_VAULT pinned to a scratch directory): `git clone --branch
  v2.0.0 --depth 1` produced a tree with `skills/`, `commands/` and
  `.claude-plugin/` present, `VERSION` reading `2.0.0`, and
  `sh scripts/verify-install.sh` reporting `255 file(s) match, 0 mismatched,
  0 missing, 0 wrong type, 0 extra`, PASSED.
- Plugin manifests: `claude plugin validate . --strict` (Claude Code CLI
  2.1.207) passed with zero warnings against the pre-cut tree on 2026-08-04;
  the cut changed only version strings and two description sentences in
  those manifests.
- Doctor on this development checkout, 2026-08-04: 7 of 10 proven, 2
  skipped, 1 failed. The failure is check 4, setup not completed on THIS
  working clone (scripts/setup.py has never been run here); the two skips
  depend on it. This is a fact about the founder's development checkout,
  not about the released tree; the beginner install path itself was proven
  in Loop 3 by two independent probes and re-proven against the corrected
  page (9 of 10 proven, 1 skipped, 0 failed, recorded in
  docs/closure/reports/2026-08-04-P-3c-corrected-quickstart-verification.md).
- Uninstall: NOT rehearsed on 2026-08-04. The documented uninstall path in
  README.md exists and was last exercised before this baseline; treating it
  as unverified at this baseline is the honest reading.
- ADDENDUM, 2026-08-04 late night, same day: the rehearsal has now run,
  hermetically (fresh scratch HOME, pinned vault env vars, the v2.0.0 tag
  cloned fresh). Verdict PASS against the plan's own done-check: after the
  documented uninstall, every remaining file is either documented-retained
  user data (vault, consent config) or toolchain noise, and no hook entry
  survives in settings.json. Every documented Path 2 command ran verbatim
  with matching output. The rehearsal also exercised the new schema-skew
  wording in the wild: the doctor met an older store and printed refused
  (schema-behind) with nothing touched, instead of the retired STORE
  CORRUPT message. One near-miss disclosed: two script invocations ran
  with the wrong working directory and the doctor read a real store
  read-only; its content hash was verified identical before and after.

## Known limits accepted into the next program

- `docs/KNOWN-LIMITS.md` in full, unchanged by the cut except the pinned-tag
  reference.
- Register items X-01 to X-06 (docs/closure/CLOSURE_REGISTER.md): second
  runtime conformance, external user study, benchmark corpus, measured
  dogfood, ecosystem thresholds, fault-injection reliability. All OPEN. The
  2.0.0 changelog entry ends by naming them.
- `docs/NOT-FINALIZED.md` entries 25 to 30, added 2026-08-04: the
  never-block blanket handler in bm_telemetry.py, duration_h write-side
  zeroing, the labelled-absence helper and overlap-count dedup suggestions,
  the consent-inventory gap for bm_sessionstart.sh wiring, the
  read_jsonl/read_records split, and doctor's FAIL wording for a healthy
  schema-skewed store.
- Windows is exercised by CI store, suite and gate jobs; the full product
  lifecycle on native Windows (installer, hooks, uninstall) is NOT certified
  and remains the positioning plan's WIN phase.
- CORRECTION, 2026-08-04 late night, same day: the line above overstates the
  Windows matrix. Reading .github/workflows/tests.yml directly: windows-latest
  appears in exactly one job, store; the suite job matrix is ubuntu and macos
  only, and the gate job runs on ubuntu. Windows CI coverage at this baseline
  is the store job alone. Found by the W3 writer while encoding
  capabilities.status.json; the register carries the corrected fact.
