# Founder Report 3: Loop 2, the commands became real

Status: CURRENT. 2026-08-01. Program: release-closure. Mode:
founder-directed autonomous run.

## Outcome first

The seven beginner commands are now mechanical operations over the one
database, and the claim survived a three-way adversarial review only
after twelve confirmed defects were fixed, each with a regression test
that failed before its fix.

## Gate evidence, quoted

- The Loop 2 gate is executable and permanent:
  test_scripted_first_project_end_to_end drives start, status, next,
  task, review, deliver through subprocess against a temp root,
  asserting rows and one attribution record per mutation.
- Final gate, run in the orchestrator session after the last edit:
  "test_all: 1307 tests across 10 suites, 6 skipped, 117.3s wall.
  ALL GREEN" and "verify: healthy, 0 problem(s)".

## What the refuters caught (the reason this loop is trustworthy)

Correctness: a refused review left an orphan evidence row; evidence
accepted subjects that did not exist or belonged to another project;
deliver succeeded on an empty project; two projects in one folder
overwrote each other's generated pages; the next command claimed an
ordering the data could not support. Privacy: nine free-text columns
rode the export allowlist verbatim (a pasted secret would have
exported); the generated pages were committable with raw prose; the
document funnel masked tokens but not absolute paths. Register: the
help page miscounted the commands, the install path broke plugin
installs, internal jargon leaked, two questions ended the page.
All fixed; the fixes are the majority of the loop's final commit.

## Decisions taken (reversible, yours to overturn)

- One project per folder is now the beginner law; a second project in
  the same folder needs an explicit flag and gets its own page names.
- Local display shows your own data in full; anything that leaves the
  machine stays redacted by default. The rationale sits in the CLI's
  own docstring.

## Spend and forecast

Loop 2 spend: roughly 1.5M subagent tokens (two-stage build, one policy
fix, three refuters, one fix batch). Forecast unchanged: Loops 3 to 7
at this cadence (medium confidence, assumption: no new blocker class);
the calendar gate on dogfood starts the moment you run your first real
project through these commands, which is now possible.

## Next

Push via GitHub Desktop (this report rides along), then Loop 3:
consent-first install, already designed and committed.
