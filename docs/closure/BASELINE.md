# Closure baseline, Phase A

Status: CURRENT. Written 2026-08-02 for the 9/10 Closure Protocol
(`docs/evidence/` holds the founder-supplied source). This is the ground truth
the closure register is built on. Nothing here is taken from a prior review,
a plan, or a commit message; every line names the command or the file that
produced it.

## Commit and tree

- Commit: `c5ceccc` on `release/2.0-final`, working tree clean.
- Local gate, run after the last edit:
  `test_all: 1393 tests across 12 suites, 6 skipped, 170.5s wall. ALL GREEN`,
  exit 0.
- CI: GitHub Actions run 30739559052, OVERALL success, nine of nine jobs green
  (gate; suite macos; suite ubuntu; store windows 3.9 and 3.x; store ubuntu 3.9
  and 3.x; store macos 3.9 and 3.x).
- This is the FIRST green CI run in the branch's history. The three before it
  were red: 30686128796 at `8b98bbb`, 30719540323 at `4116d3a`, 30730065699 at
  `4030ca9`, all while local gates read ALL GREEN.
- Platform of record for local runs: macOS, Python 3.9.6 and 3.14.6 present.

## Method

Seven agents, four inventory and three probes, at this commit. Inventory was
read-only. Probes executed only inside throwaway `/tmp` directories with their
own `HOME`, against a `git archive` export of `c5ceccc`; the real repository and
the real `~/.brotherme` were never mutated. Two agents failed on output
formatting and their areas are named as gaps below rather than quietly dropped.

## Results by area

### Consent before persistence: PASS

The protocol's zero-write consent test was executed, not reasoned about. A fresh
`HOME`, an exported tree, every wired hook command driven with a representative
payload plus the discovery surfaces a new user would touch, filesystem snapshot
before and after. No project store, vault, telemetry file, learning file or
session record was created before consent. This is the one gate that came back
clean on its first hostile run.

### Enforcement boundary: FAIL, and this is the critical finding

The fence hook denies a foreign cross-fence Edit and allows the owner's, which
is the happy path working. Every other outcome tested is ALLOW. Nine failure
conditions each allowed the write with exit 0: store missing, store corrupt,
store zero bytes, **store present with zero active claims**, five shapes of
malformed payload, an unrecognized path key, an internal exception mid-decision,
`bm_store.py` unimportable, and an underivable session identity.

Three findings inside that deserve naming separately:

1. **A store with no active claims disables the fence entirely.** That is the
   state a fresh or fully released project sits in, which is exactly when
   claim-before-edit matters most.
2. **`BM_FENCE_STRICT` is a no-op in that state.** It is read after every
   fail-open path, so on a zero-claims store it changes nothing. It is a
   tightening flag, not a fail-closed mode.
3. **Bash is ungated and silent**, and enforcement state lives inside the tree
   the ungated channel can write. `rm -f .brothermode/store.sqlite3` turned a
   proven DENY into an ALLOW. Five mutation forms (shell redirection, `sed -i`,
   `tee`, `python3 -c`, `git checkout`) all wrote a file under an active foreign
   fence with no hook consulted.

Three documents overstate this boundary, one of them inverting the actual rule.
The protocol's Law 4 and Law 5 are not met.

### Release truth, packaging and portability: FAIL in parts

- Several CLIs ship no console script and are unreachable on a pip-installed
  copy, including `bm_project.py` and its eighteen subcommands, `bm_ledger.py`,
  and `bm_project_facts.py`.
- `hooks.json` and `scripts/install.py` disagree on timeout and status message
  for `SessionStart` and `SessionEnd`, so the two install paths produce
  different effective configurations.
- The CI push trigger names a branch `v2` that does not exist, so release
  branches get no push-triggered run and are covered only by pull request.
- Only three of thirteen test files execute under Python 3.9 in CI; the rest run
  only under `3.x`, currently 3.14.6, so most of the suite has never run on the
  declared floor.
- `docs/ba/QA-GATES.md` is stale against the live workflow and no test covers it.

### State authority and views: mostly PASS, one real defect

No path parses a generated view back into authoritative state, and redaction is
fail-closed, both proven live. Storage permissions are tight (store directory
0700, files 0600, fence tokens, migration backups and consent config likewise).
Two defects: the quarantine directory is never `chmod`'d while the files inside
it are, and `STATE.md` embeds a fresh timestamp on every render, so it is not
byte-stable with unchanged source state, which Law 3 requires.

### Write-site manifest: FAIL

`tools/write_sites.json` is a partial map presented as a complete one. Its
generating test matches only `open(w)`, `os.open(` and `.write()`, so roughly
forty-seven mutation sites using `os.replace`, `shutil`, `mkdir`, `unlink` and
`chmod` inside the very same reviewed files are untracked. It is also hard-scoped
to `tools/`, so `scripts/` and `mcp/` have no review-gate coverage at all.

## What this baseline does NOT cover, stated rather than implied

- Two of seven agents failed on output formatting; their areas (a second pass on
  public surfaces, and the dedicated release-truth probe) are partly covered by
  the surviving agents and by the maintainer's own verification, not by an
  independent pass.
- No fault-injection campaign was run. The protocol asks for 10,000 sequences;
  the number run today is zero, and no reliability figure is claimed.
- Windows and Linux behavior is known only through CI, not through a local
  hostile session.
- No external user, no second runtime, no benchmark corpus. Those are named in
  the register as not machine-closable.
