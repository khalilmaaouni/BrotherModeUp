# Phase 1 fix round 7 (2026-07-26)

From refute round 6 (fresh code confirmed, 170 tests quoted). Calibration lens CLEAN
again. Three gates, six soft, and FIVE of the soft items are the same class.

## The class fix that must come first: ONE OUTPUT FUNNEL

Five separate findings say the same thing: a founder-typed string reaches a terminal or a
file unredacted or unsanitized, at an exit nobody remembered. Round 5 fixed the dashboard,
round 6 fixed dump and overlap refusals, and this round finds it again in verify's problem
list, the path-escape refusal, the record NAME (whitelisted, and valid_name happily accepts
AKIAIOSFODNN7EXAMPLE or password=hunter2 as a name), and the --session echo.

Patching four more call sites guarantees a seventh round of the same. Required instead:
make it IMPOSSIBLE to emit raw. Every byte leaving this module (stdout, stderr, or a
generated file) goes through one funnel that redacts and sanitizes by default. Call sites
lose the ability to opt out; the only raw path is the explicit --raw export, which already
warns. Structural test: no direct print(), sys.stdout.write, sys.stderr.write, or file
write of a rendered string exists outside the funnel functions (scan the source, allow the
funnel's own definitions by name), so a new call site cannot bypass it.

Record names are founder-typed text and must be redacted at every exit like any other
field. If a redacted name makes a record unusable to refer to, print the lifecycle uuid
prefix beside it, which is already how records are identified elsewhere.

## GATE A: a generated view can destroy the founder's own writing (VERIFIED BY ORCHESTRATOR)

Reproduced: render a view, hand-edit STATE.md the way a human would (delete the closing
marker line, add "## My notes / CALL BOB ABOUT THE CONTRACT"), render twice.

    after render 1, my notes present: True
    after render 2, my notes present: False
    bytes left in file: 330

Every byte of human prose is gone, exit 0, no warning, no backup. The marker-injection
guard neutralizes markers arriving from the STORE but trusts markers already in the FILE.

Fix, fail-closed: if the marker structure in an existing STATE.md is not exactly one BEGIN
followed by one END, REFUSE to write it (reason 'view-markers-damaged'), name the file and
what was found, and tell the founder how to repair it. Never rewrite a file whose structure
we cannot parse. Additionally, before any rewrite that would remove existing non-generated
bytes, write the previous content beside it as STATE.md.bak-<UTC stamp> and say so. A
generated file may overwrite its own block; it may never silently discard what a human
wrote.

## GATE B: the fail-closed redaction promise does not hold

With bm_telemetry.py absent, render_state_md and write_state_view emit and WRITE a view
containing founder text, exit 0, with zero warning bytes on stderr. The spec says: degrade
LOUDLY and REFUSE to write generated views. The hole exists because the record name is
interpolated raw and the redaction helper is only invoked on non-empty optional fields, so
the missing-redactor warning never fires.

Fix: the funnel above is the natural home for this. If the redactor is unavailable, every
funnel call refuses (or, for stderr advisories, prints the one-line warning), and no
generated file is written at all. Test with bm_telemetry.py genuinely absent.

## GATE C: quarantining can DESTROY the sidecars it promises to preserve

The connection is closed BEFORE the -wal and -shm sidecars are moved. On a newer bundled
SQLite (3.53.1, shipped with a recent Python 3.13), close() deletes those stale sidecars,
so they are never quarantined: destroyed rather than merely left behind, which is worse
than the original defect. This is library-version-dependent, so it will appear on some
machines and not others, which is the hardest kind of failure to trust a green suite about.

Fix: preserve the sidecars BEFORE closing the connection (copy or rename them into the
quarantine directory while the handle is still open), then close, then move the main file.
The calibrated test must assert the sidecars EXIST in the quarantine directory with their
content, and must not depend on the local SQLite version to pass. State in the test's
docstring which SQLite version behavior it is guarding against.

## SOFT D: a hardlinked store file bypasses the symlink guard

The containment check detects symlinks only, so hardlinking .brothermode/store.sqlite3 to
a git-visible path publishes the raw database (reproduced: secret found in committed
history). Fix: refuse when the store file's link count is greater than 1, naming the risk,
since a hardlink cannot be detected by path inspection.

## SOFT E: render_digest discards a whole decision that exceeds its budget

A single decision longer than the 1200 character budget results in ZERO decision content
(62 of 1200 characters used) rather than a truncated decision. The spec says each section
truncates itself within its own budget. Fix: truncate the decision text to fit, with an
explicit marker, so a resuming session sees the beginning of the decision rather than
nothing.
