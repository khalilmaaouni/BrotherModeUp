# BrotherMode V2, QA gates

This file is for anyone about to merge a change, and for anyone auditing
whether a "tested" claim is actually enforced somewhere rather than just
written down. Every gate below names the exact command that runs it, so
nothing here has to be taken on faith. Source: `.github/workflows/tests.yml`,
`SECURITY.md`, `INVARIANTS.md`, and
`docs/superpowers/specs/2026-07-26-phase1-fix-round.md` line 8 to 10 (the
calibration contract).

## The gates

| Gate | Exact command | Expected output | What it protects | Blocks release |
|---|---|---|---|---|
| V1 regression suite | `python3 tools/test_bm.py` | All tests pass, process exits 0 | Secret redaction, owner-only sensitive files, no project-identity collision, non-invasive autosave, and the ten calibrated defects listed in `INVARIANTS.md` (for example a partial `off` command, a false success report, a stamped-over live thread) | Yes, on every push and pull request to `main` and `v2`, on `ubuntu-latest` and `macos-latest` |
| Score checks, strict mode | `python3 tools/bm_score.py --strict` | Exits 0 when every code-graded check passes, exits nonzero on any FAIL | The weekly-review checks that code, not a language model, can decide mechanically | Yes, but only on the `ubuntu-latest` leg of the V1 job |
| V2 store suite | `python tools/test_bm_store.py` | All tests pass, process exits 0 | Every behavior in the ratified V2 API, plus the ten numbered calibrated reinjection tests named in the design spec, plus every fix demanded by the Phase 1 fix round | Yes, on every push and pull request to `main` and `v2`, across the full matrix below |
| Store invariant check, run by hand or by a wrapping script | `python3 tools/bm_store.py verify` | `verify: healthy, 0 problem(s)` and exit 0; otherwise a numbered list of problems and exit 2 | The four machine-checkable invariants over a live store: one active record per name, no overlapping active claims, every active record visible in the generated view, and every record's transition history matching its current state | Not part of the shipped CI workflow itself; this is a runtime check a founder or a CI step can call against a real project's store |
| Toolchain size check | `python3 tools/test_bm.py TestRegistryAbsorbAndView.test_security_md_line_count_claim_is_still_true` | Test passes while the real line count stays within 15 percent of the figure `SECURITY.md` states (about 8,400 lines, measured 2026-07-26) | The claim that BrotherMode is a small, auditable amount of standard-library code, not a growing dependency the founder cannot read in an afternoon | Yes. Resolved 2026-07-26: this is a test inside the V1 suite, so it runs in CI on every push, not by hand |
| No-network-call check | `python3 tools/test_bm.py TestRegistryAbsorbAndView.test_no_network_claim_is_mechanically_true` | Test passes; it fails naming the offending file and line if any shipping tool imports a network or subprocess module, or if any shell tool runs curl, wget, nc, ssh, scp, or a git command that reaches a remote | The "makes no network calls" privacy claim in `SECURITY.md`, which is the single claim protecting the founder's data from leaving the machine | Yes. Added 2026-07-26 because the claim previously had NO mechanical gate at all: it shipped as a grep the reader was expected to run by hand. Calibrated both ways: injecting `import urllib.request` into a tool and appending `git push origin main` to the autosave each make it fail, naming the exact file and line |

## The CI matrix, exactly as configured

Source: `.github/workflows/tests.yml`, verified by reading the file directly.

| Job | Operating systems | Python versions | What it runs |
|---|---|---|---|
| `suite` (the legacy V1 job) | `ubuntu-latest`, `macos-latest` | whatever `3.x` resolves to at run time | `python3 tools/test_bm.py`, then `python3 tools/bm_score.py --strict` on the `ubuntu-latest` leg only |
| `store` (the V2 engine job) | `ubuntu-latest`, `macos-latest`, `windows-latest` | `3.9` and `3.x` | `python tools/test_bm_store.py` |

The workflow file's own comment explains the split: the V1 suite still
depends on platform assumptions (shell scripts, POSIX file modes), so it only
runs where those hold, while the V2 engine is meant to be cross-platform from
the start, so its suite runs on all three operating systems and on both the
oldest Python version the project still supports and the newest. GitHub
Action versions in this workflow are pinned to full commit hashes rather than
a movable tag, specifically so that a tag being moved upstream cannot change
what actually runs in this project's CI without a reviewed change here.

## The calibration rule

A test suite is not proof by itself. `INVARIANTS.md` states this directly: an
early version of the generative test created almost no real work across
three separate random seeds and still passed, because it was exercising
nothing. The rule adopted since, restated by the Phase 1 fix round: **every
fix lands together with a test that is proven to fail when the defect it
fixes is reintroduced.** Concretely, for any given fix:

1. Reintroduce the exact defect in the code (for example, let a same-session
   check treat two empty session ids as equal again).
2. Run the relevant suite (`python tools/test_bm_store.py` for a V2 engine
   fix, `python3 tools/test_bm.py` for a V1 or shared mechanism).
3. Confirm the specific new test fails, and that it fails for the stated
   reason, not some unrelated reason.
4. Restore the fix and confirm the full suite is green again.

A fix that arrives without this calibration is rejected back, per the fix
round's own wording. `INVARIANTS.md` documents this same discipline already
proven out for the V1 suite, in its "Measured power of the tests" table: ten
separate known defects were each reintroduced by hand, and the suite caught
all ten. No equivalent table yet exists for the V2 store suite as of this
pack's writing; `docs/superpowers/specs/2026-07-26-phase1-fix-round.md`
lists ten numbered reinjection tests plus nine additional gate-specific
calibrated tests that the suite is required to contain, but this pack found
no source confirming each one has actually been run through the
reintroduce-and-confirm-it-fails cycle yet. Treat that as an open item, not a
settled claim.

## A known, named gap, now closed (kept here as the record)

The Phase 1 fix round's "out of scope for this round" section named one open
problem: the V1 lifetime tripwire test inside `tools/test_bm.py` failed
against `tools/bm_store.py`'s legitimate use of the literal word "ephemeral",
because that test was written before the V2 store existed. The fix round was
explicit that the right fix was a small, deliberate exemption in that test
file, that the decision belonged to the founder, and that nobody should
rename, split, or obfuscate the literal to dodge the scanner.

RESOLVED on 2026-07-26. The founder approved the exemption, it was applied to
`tools/test_bm.py`, and it was calibrated the same way every other fix here
is: the literal was reintroduced into a V1 module (`bm_threads.py`) and the
tripwire still fired, naming that file and line, which proves the exemption
narrowed the guard to exactly one file rather than blunting it. The full V1
suite returned to green after the change.
