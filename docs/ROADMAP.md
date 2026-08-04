# BrotherMode roadmap

Status: CURRENT as of 2026-08-04.

This page says how far every claim this project makes has actually been
checked, what is being worked toward next, and what is deliberately not on the
list at all. It carries no dates, because a date on a roadmap written by one
person is a promise about a calendar rather than a statement about evidence.

The register behind it is [`capabilities.status.json`](../capabilities.status.json),
which answers a narrower question: is a thing offered, in four states. This
page answers the other half, how far each claim has been proven, in six proof
states. Section 3 is GENERATED from that register, so the two cannot say
different things about the same capability.

## 1. The six proof states

A rung says who checked a claim and where, not how much anyone wants it to be
true.

1. **Planned.** Named here, with no evidence in the tree behind it yet. A
   reader should treat it as an intention.
2. **Implemented.** Built, with something in the tree describing it, and not
   measured. The code exists; the claim about what it achieves does not have a
   number behind it.
3. **Verified locally.** The evidence names a file or a test in this tree, and
   no continuous integration job covers it yet. It passes on the machine it was
   written on.
4. **Verified in CI.** The evidence names a job under
   [`.github/workflows`](../.github/workflows), so the check runs somewhere
   other than the author's own machine, on a schedule nobody controls by hand.
5. **Verified externally.** Checked by someone outside this project, or on a
   machine this project does not own.
6. **Certified.** The register marks it certified: a named evidence file in
   this tree plus a test or a job that goes red when the claim stops being
   true.

Two honest notes about that list, because the ordering invites a reading it
does not support.

Certified sits at the top as the strongest claim this project can make about
its own tree, and it does not include an outside opinion. Rung 5 is about who
did the checking; rung 6 is about how strong the proof inside the tree is.
Nothing is at rung 5 today, and section 3 prints that empty rung rather than
hiding it. What filling it would take is written down in
[`docs/closure/CLOSURE_REGISTER.md`](closure/CLOSURE_REGISTER.md), items X-01
to X-06: a second runtime with credits, participants who did not build this, a
benchmark corpus, measured dogfood, ecosystem thresholds, and fault injection.
All six are open, and none of them close by writing code.

The rungs are also not a queue every item walks in order. A capability can be
certified against this tree while no outside party has ever run it, which is
exactly the position most of section 3 is in.

## 2. What it takes to move up a rung

No item on this page reaches certified through a documentation-only change.
Editing this page moves nothing at all: section 3 is rendered from the
register, and a state written into the register has to name evidence that
resolves to a file in the tree before `tools/test_bm_docs.py` will pass. A
promotion is therefore always at least three things in one change: the work,
the file that proves it, and the register line pointing at that file.

The two checks that hold this, both runnable from a clone:

- `bm-docs roadmap-status --check` (from a clone, the same subcommand on
  `tools/bm_docs.py`) refuses a page whose generated block is not what the
  register renders today.
- `bm-docs verify-docs` runs that check, the same check for the README block,
  the identity manifest agreement, and a link check across the current pages,
  and reports one line per lane.

What those checks cannot do is judge whether the named evidence is the RIGHT
evidence. A test that proves the wrong thing still resolves to a file. That
judgement stays with the person reading the review, which is why every row in
section 3 carries its evidence sentence in full rather than a checkmark.

## 3. Where every capability stands today

The block below is GENERATED from
[`capabilities.status.json`](../capabilities.status.json) by
`bm-docs roadmap-status --write` (from a clone, the same subcommand on
`tools/bm_docs.py`). The mapping from the register's four states to these six
proof states is code, printed inside the block so a reader never has to take it
on trust. To change what this says, change the register and rerun the command.

<!-- BEGIN GENERATED ROADMAP STATUS -->
<!-- Generated from capabilities.status.json by `bm-docs roadmap-status --write` (the packaged console script; from a clone, tools/bm_docs.py). Edit the register, not this block. -->

Six proof states, mapped from the four states in `capabilities.status.json`, updated 2026-08-04: certified means the register marks it certified, meaning a named evidence file in this tree plus a test or a job that goes red when the claim stops being true; verified externally means checked by someone outside this project, or on a machine this project does not own; verified in CI means the evidence names a continuous integration job, so the check runs somewhere other than the author's own machine; verified locally means the evidence names a file or a test in this tree, and no continuous integration job covers it yet; implemented means built, with something in the tree describing it, and not measured; planned means named, with no evidence in the tree behind it yet.

The mapping is code rather than judgement. Certified stays certified. A beta row becomes verified in CI when its evidence names a job under `.github/workflows`, and verified locally otherwise. An experimental row becomes implemented when its evidence points at a file in this tree, and planned when it points at nothing. An unsupported row is not a rung at all and is listed as a non-goal below.

**Certified**, the register marks it certified, meaning a named evidence file in this tree plus a test or a job that goes red when the claim stops being true.

| Capability | Proof state | What proves it |
|---|---|---|
| One writer per file, refused by a hook rather than by convention | certified | tools/bm_fence_hook.py refuses a write to a file another session has claimed, wired by hooks/hooks.json and proven by tools/test_bm_fence_hook.py. |
| Durable local store that survives a crash and can be recovered | certified | tools/bm_store.py holds the state and tools/test_bm_store.py exercises recovery; the store job in .github/workflows/tests.yml runs that suite on Linux, macOS and Windows. |
| Current pages are held to the facts read out of the tree | certified | tools/test_bm_docs.py refuses a current page carrying a stale count, a stale version, or a dated record that declares no status; docs/ba/QA-GATES.md states the gates. |
| Guided beginner flow on Claude Code | certified | skills/brotherme/SKILL.md drives the flow, commands/brotherme-start.md is its entry point, and docs/QUICKSTART.md is the install path a beginner follows. |
| Continuous integration on macOS and Linux | certified | .github/workflows/tests.yml runs the suite job on ubuntu-latest and macos-latest at Python 3.9 and 3.x, with fail-fast disabled so one platform cannot erase another's result. |
| Session telemetry recorded only after the user consents | certified | scripts/setup.py writes the consent record, tools/bm_telemetry.py is the only writer, and tools/test_bm_consent.py refuses a write without consent. |

**Verified externally**, checked by someone outside this project, or on a machine this project does not own.

Nothing stands at this rung today.

**Verified in CI**, the evidence names a continuous integration job, so the check runs somewhere other than the author's own machine.

| Capability | Proof state | What proves it |
|---|---|---|
| Windows | verified in CI | Only the store job in .github/workflows/tests.yml runs on windows-latest; the suite and gate jobs run on Linux and macOS only. docs/KNOWN-LIMITS.md records that the installer refuses Windows and that WSL works. There is no native Windows install lifecycle. |

**Verified locally**, the evidence names a file or a test in this tree, and no continuous integration job covers it yet.

| Capability | Proof state | What proves it |
|---|---|---|
| Install as a Claude Code plugin from the repository marketplace | verified locally | The manifests are real and installable (.claude-plugin/plugin.json, .claude-plugin/marketplace.json, tools/test_bm_plugin_install.py), and one install is recorded in docs/evidence/2026-07-31-first-plugin-install.md. The verified path stated in README.md is still the git clone, so this stays beta until the plugin path carries the same evidence. |

**Implemented**, built, with something in the tree describing it, and not measured.

| Capability | Proof state | What proves it |
|---|---|---|
| Benchmark harness comparing runs | implemented | docs/BENCHMARK.md describes the method and docs/BENCHMARK-V1-V2-RC2.md records a dated run. No run against the current tree is recorded, so no current number is claimed. |

**Planned**, named, with no evidence in the tree behind it yet.

| Capability | Proof state | What proves it |
|---|---|---|
| Delivering a web build through the same guided flow | planned | not measured |
| Deployment previews attached to a delivery | planned | not measured |

**Not a goal**, and therefore on no rung: the register's unsupported rows, carried here because a roadmap that lists only what is coming reads as a promise about everything it leaves out.

| Not a goal | Why it is not offered |
|---|---|
| Publishing to production on its own | Not offered. Cutting and publishing a release is a founder-gated sequence of steps in docs/RELEASE.md, and the suite skips the release checks until a human has cut the tag. |
| Spending money on the user's behalf | Not offered. SECURITY.md states there is no account and no server, and that the only outbound call is a version check the user invokes by hand. |
| Legal or security certification of any kind | not measured |
| A guaranteed native mobile result | not measured |
| Replacing a human specialist review | not measured |
| Multi-user or enterprise project management | Not offered. README.md states there is no shared server, no account system and no multi-user coordination layer, and that running this as a control plane for several people is not what it is for. |
| Changing its own safety rules | not measured |

<!-- END GENERATED ROADMAP STATUS -->

## 4. Waves, and the order they are taken in

Waves are named by the outcome that closes them, never by a date, and this page
does not carry the working plan's own loop identifiers: those move as the plan
is replanned, and a page pinned to them goes stale without anything being
wrong. The ordering rule is the only scheduling claim made here: a wave is
taken when it removes the largest unproven claim still standing, and it does
not close until the proof named beside it exists.

| Wave | The outcome that closes it | What would prove it |
|---|---|---|
| One product truth | One name, one register, one story, one roadmap, and one command that checks all of them against the tree | `bm-docs verify-docs` reports PASS on every lane, and the naming, evidence and absolute-claims tests in `tools/test_bm_docs.py` read every current page |
| An install path a stranger can follow twice | The plugin install carries the same evidence the git clone already carries, so it stops being the second-best documented path | The register's plugin row cites a rehearsed install from a clean machine rather than one recorded first install, and leaves beta |
| The whole lifecycle on Windows | Install, hooks, doctor and uninstall exercised on native Windows, not the store suite alone | The Windows row's evidence names jobs beyond the store job in `.github/workflows/tests.yml`, and `docs/KNOWN-LIMITS.md` stops recording a refused installer |
| Measured use, not reported use | Counted projects, recorded failures, and a comparison against working without the tool | Item X-04 in `docs/closure/CLOSURE_REGISTER.md` closes with numbers behind it |
| A comparison someone else can reproduce | A benchmark corpus run under the same conditions for every tool named in `docs/market/CATEGORY.md` | Item X-03 closes, and the benchmark row leaves implemented for a rung with a measurement behind it |
| Verification from outside | People who did not build this install it, use it, and report what broke | Items X-01, X-02 and X-05 close, and rung 5 in section 1 stops being empty |

The first wave is the one this page belongs to. The rest are ordered by how
much of what this project claims about itself they would let a stranger check
without asking the author.

## 5. Deferrals: what this roadmap does not schedule

These are non-promises, listed so that silence cannot be read as a plan. Each
one is a thing a reader could reasonably expect from a tool that says it
delivers outcomes, and each one is out.

- **Native mobile builds.** A guaranteed native mobile result is unsupported in
  the register, and nothing on this page moves it. The guided flow can help
  with a mobile project the way it helps with any project, and it makes no
  claim about the result running on a device.
- **Creative media generation.** Images, video, audio and design assets are not
  produced by this tool, and this roadmap does not schedule them. It
  orchestrates work and records evidence; generating media is a different
  product with different failure modes, and pretending otherwise would put a
  claim on this page that no file in this tree could support.
- **Office document artifacts.** Spreadsheets, slide decks and word processor
  files are not deliverables here. What this project generates is markdown and
  the records behind it, so a delivery packet stays readable by git and
  diffable in review.
- **Multi-user and enterprise coordination.** Unsupported in the register, and
  a deliberate design limit rather than a gap: there is no shared server, no
  account system and no multi-user coordination layer, as
  [`README.md`](../README.md) states. Handing a project to another person
  occasionally is supported; running this as a control plane for a team is not
  what it is for.

Two of those four have a row in the register today, the mobile one and the
multi-user one, and the other two are stated here alone. That asymmetry is
recorded rather than tidied over: this page is not the register's editor, and
adding a row is a register change with its own review.

Nothing on this list is a judgement about the tools that do those jobs well.
[`docs/market/CATEGORY.md`](market/CATEGORY.md) names peers that are better at
several of them, in their own words rather than this project's.
