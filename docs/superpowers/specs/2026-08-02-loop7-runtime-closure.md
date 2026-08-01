# Loop 7 closure: runtime adapters, verified narrowly and labeled honestly

Status: CURRENT. Written 2026-08-02 by the orchestrator. Program gate:
one core, a conformance suite, Claude Code fully verified plus at most
two more runtimes, the rest labeled; conformance passes on real runtimes
only.

## The one-paragraph version

Loop 7 closes by audit, not by construction. The runtime machinery the
program asked for already shipped before the program started, survives
under amendment A4 (existing machinery is load-bearing, briefs that
would fork it are refused), and passes its own conformance suite inside
the standing gate. Claude Code is the one Tier A runtime. Every other
runtime ships an adapter instruction file, an honest capability row, and
an UNVERIFIED label wherever a claim could not be proven against a real
captured payload. Nothing in this loop pretends otherwise, and the suite
fails any page that starts pretending.

## What the ratified program accepted, restated

The external review's section 17 asks for a brotherme/runtimes adapter
package with normalized events and, for every Tier A runtime, payload
fixtures captured from the actually installed runtime ("do not infer
payload shape from event names"). The ratified program (2026-08-01,
founder-approved) accepted instead the four-level runtime truth ladder
and the narrow-release rule: fully verify Claude Code, verify at most
two more runtimes, label the rest honestly, expand after evidence.
Amendment A4 refuses forks of existing machinery. The existing machinery
here is tools/bm_runtimes.py: one registry, one renderer, one command,
every fact carrying the vendor URL and the date it was read.

Building the section 17 adapter package tonight would have required
installing foreign runtimes and authenticating their accounts, which is
founder-gated twice over (software installs and credentials), and would
have produced adapter parsers with no captured payloads to parse, which
is the exact inference section 17 forbids. It was not built. That is
compliance, not shortfall.

## Tier assignment, with the evidence for each claim

Tier A, fully verified: Claude Code, and only Claude Code.

The source plan's Tier A checklist, item by item, each with the suite
that proves it inside python3 tools/test_all.py:

- Installable package or plugin: scripts/install.py clone path and the
  hooks/hooks.json plugin manifest, both exercised by
  tools/test_install.py end to end; first real plugin install recorded
  in docs/evidence/2026-07-31-first-plugin-install.md.
- Commands registered: the seven files under commands/, wired and
  drift-tested by tools/test_bm.py.
- Instructions loaded: SKILL.md plus the guided skill at
  skills/brotherme/, loading proven by the first-install evidence and
  the wiring tests in tools/test_bm.py.
- Session lifecycle captured: SessionStart and SessionEnd hooks through
  tools/bm_telemetry.py, proven by tools/test_bm_consent.py and the
  telemetry assertions in tools/test_bm.py.
- Pre-write gate: tools/bm_fence_hook.py on PreToolUse, proven by
  tools/test_bm_fence_hook.py.
- Post-tool reconciliation: tools/bm_bash_audit.py pre and post phases,
  proven by tools/test_bm_bash_audit.py.
- Telemetry: outcomes.jsonl written by the SessionEnd hook, proven by
  tools/test_bm.py and tools/test_bm_ledger.py.
- Compaction and recovery: PreCompact runs bm_autosave.py plus the
  telemetry precompact brief, proven by tools/test_bm_autosave.py.
- Conformance suite passes: tools/test_bm_runtimes.py, inside the gate
  since it landed, so a red conformance run blocks every loop close.

Tier B and below: every other registry runtime. docs/RUNTIMES.md keeps
the two questions apart on purpose: whether a runtime has hook points at
all (verified per runtime from vendor pages, URL and date recorded), and
whether BrotherMode's OWN hooks work there, which is UNVERIFIED
everywhere but Claude Code because nobody has captured a real payload
from any other runtime. UNVERIFIED means do not wire it. The adapter
files under docs/runtimes/ teach the instruction file and the CLI, never
the hooks.

## What the conformance suite actually enforces

tools/test_bm_runtimes.py, in the standing gate:

- The registry is structurally sound and every entry carries at least
  one vendor source URL; unverified entries carry their reason.
- The adapters teach no invented command names: every command an adapter
  names must exist in the module it names.
- The committed output matches the registry: a hand-edited capability
  table or a missing adapter file is reported stale, so docs/RUNTIMES.md
  cannot drift from the generator.
- Capability claims stay separate: a runtime with hook points never
  claims BrotherMode hooks work; a runtime without hook points says the
  fence is advisory there.
- Emit is non-destructive, deterministic, and refuses to overwrite
  hand-written tables.

That is what "conformance passes on real runtimes only" means in this
tree: the only runtime whose hooks any page claims work is the one whose
hooks a suite actually exercises.

## What Loop 7 leaves open, stated plainly

- No second runtime is verified. Codex CLI is the recommended next
  candidate (registry says it has hook points). Verifying it needs the
  founder: install the runtime, authenticate it, run the payload capture
  against a fixture repository, then write the adapter parser against
  captured fixtures. Until then its row stays UNVERIFIED and that is the
  designed state, not a debt.
- The brotherme/runtimes adapter package from source plan section 17.2
  is deliberately not built. The trigger to build it is the first
  captured foreign payload, nothing earlier.
- No payload capture harness ships. When the founder wants the Codex
  verification, the harness is the first brief of that work, and it is
  small: a hook target that appends raw JSON to a file, redaction pass,
  fixture directory.

## Gate evidence

python3 tools/test_all.py after the last content edit of this loop's
commit train: the exact green line is quoted in the message of the commit
that lands Founder Report 5 (the file
2026-08-02-founder-report-5-loop7.md beside this one) and in the wave 15
close record. test_bm_runtimes.py runs inside that gate; a failure there
fails the loop. The Loop 9 preliminary refuter panel additionally re-ran
TestCommittedOutputMatchesTheRegistry and TestCapabilityClaimsStaySeparate
directly, both OK, while attacking this closure.
