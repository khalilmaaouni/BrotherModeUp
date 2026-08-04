# The category BrotherMode sits in

Status: CURRENT as of 2026-08-04.

This page states which market category BrotherMode belongs to, why it is not
the five things it is most often mistaken for, and how it compares to its
nearest peers. Everything under section 3 is a desk assessment of the field
as of 2026-08-04, read from each peer's own documentation and independent
coverage, not a hands-on trial by this project. Item X-03 in
docs/closure/CLOSURE_REGISTER.md records that the benchmark corpus a
measured, cross-tool score would need has not been run, so no such score
appears here.

## 1. The category

BrotherMode belongs to a category best named a verified autonomous delivery
system for a solo builder: a tool that turns a plain-language description of
a wanted outcome into finished, working software, or another artifact, end
to end, on the builder's own machine, while keeping a durable and checkable
record of what happened, refusing to advance past a step that has not
actually been verified, and stopping to ask before an action a human has to
own. The word doing the most work in that name is verified: the deliverable
is not the code an agent wrote, it is the code an agent wrote and a passing
check that ran after the last change, plus a written trail explaining why. A
solo builder is who this category serves: someone who does not have a team
of reviewers standing behind the agent, so the tool itself has to supply
some of what a second engineer would otherwise catch.

## 2. What BrotherMode is not merely

Five neighboring categories get reached for first, because BrotherMode
shares surface features with each. Each paragraph below states the honest
overlap, the real difference, and what the neighboring category does better.
capabilities.status.json is where a reader checks whether a specific
BrotherMode capability named here is certified, beta, experimental, or
unsupported today, rather than this page restating that state.

### Not merely a prompt pack

A prompt pack is a folder of instructions a model reads and, at its own
discretion, follows. BrotherMode's laws start the same way, as text in
SKILL.md, but the parts that matter most are not left to the model's
discretion: the single-writer rule is refused by a PreToolUse hook
(tools/bm_fence_hook.py) rather than requested in prose, and the naming,
evidence, and absolute-claims rules this very page is held to are checked by
tools/test_bm_docs.py rather than trusted. A prompt pack does better than
BrotherMode at exactly the thing it is: it is lighter to read, easier to
fork line by line, and asks nothing of the builder's machine beyond the
words in the file. BrotherMode's machine-checked laws cost more to set up
and cannot be skimmed in thirty seconds the way a prompt pack can.

### Not merely a methodology

A methodology, like the role and phase patterns several of the peers below
teach, is a way of working that a human or a model has to choose to follow
each time. BrotherMode borrows the same shape, roles, phases, gates, but
wires the parts a methodology usually leaves to discipline into code and
CI: a fence line has to exist before a write is even attempted, and a suite
run is what tools/test_bm_docs.py and the rest of the gate check, not a
checklist item a session can quietly skip under deadline pressure. A
methodology does better than BrotherMode at portability: it travels to any
tool, any model, any language, because it is only ever an idea written
down, while BrotherMode's enforcement is specific to this codebase and this
hook surface.

### Not merely an agent runtime

An agent runtime executes a task: it reads a prompt, takes actions, and
stops. BrotherMode runs on top of one, Claude Code, rather than replacing
it, and adds the layer a runtime does not supply on its own: a durable
state file that survives a crash or a compaction, a fence registry that
stops two sessions from clobbering the same file, and a telemetry layer
written by hooks rather than by the model, so the record of what happened
cannot be flattered by the thing being graded (docs/HOW-IT-WORKS.md,
section 1). An agent runtime does better than BrotherMode at raw
flexibility and at doing nothing else: it is not opinionated about
process, so it fits tasks BrotherMode's laws were never written for, and it
carries none of the governance overhead this project asks a session to pay
on every write.

### Not merely a hosted app builder

A hosted app builder, like the two hosted platforms compared below, runs
the agent in the vendor's own environment and hands back a deployed
result. BrotherMode runs locally: every artifact, every decision record,
and every git history entry stays on the builder's own disk, in the
builder's own repository, under no account and behind no per-message
credit meter (README.md states there is no shared server, no account
system, and no multi-user coordination layer; SECURITY.md states there is
no analytics, no account, and no server). A hosted app builder does better
than BrotherMode at zero-setup speed to a live URL: there is no local
environment to configure, no model API key to hold, and the deploy step is
the same click that started the build. None of that is what BrotherMode
offers, because owning the artifact and owning the deploy step are the
same tradeoff pointed in opposite directions.

### Not merely a project manager

A project manager tracks work someone else does: it holds the plan, the
status, and the record, and waits for a human or another tool to make the
work true. BrotherMode's state file and fence registry look like tracking,
but the same session that writes the plan also writes the code, runs the
check, and updates the record from what the check actually said, so the
tracking is a byproduct of doing the work rather than a separate layer
someone has to keep in sync by hand. A project manager does better than
BrotherMode at coordinating other people: it is built for a team where the
humans are the ones doing the work and the tool's whole job is visibility
across many of them, which is out of scope here by design (see the
multi-user-enterprise-pm entry in capabilities.status.json).

## 3. Comparison dimensions and why each peer class is reported separately

Reading the field for this page turned up desk-assessment material along
five recurring dimensions, used below to organize what is said about each
peer rather than to score it:

- **Enforcement.** Is a stated rule checked by code or CI, or only asked for
  in a prompt or a process document.
- **Evidence trail.** Is there a durable, inspectable record of what
  happened, kept separate from the model's own narration of what it did.
- **Environment and ownership.** Does the work happen on the builder's own
  machine with the artifacts on the builder's own disk, or inside a
  vendor-hosted account.
- **Coordination safety.** What happens when more than one agent or session
  reaches for the same file at the same time.
- **Access and pricing model.** Free and open source against a model access
  the builder brings, against metered hosted credits, or a subscription
  tier.

Two peer classes are reported separately rather than folded into one ranked
list. The direct open ecosystem peers run in the builder's own environment
against a model the builder brings, the same terms BrotherMode itself runs
under. The hosted outcome platforms bundle compute, a hosted environment,
and a credit or subscription price into one vendor account. Comparing the
two groups on the same axis, cost to ship one feature is the example that
comes up most, would compare a tool's design against a hosting bill, which
is not the same question, so this page keeps them apart.

No numeric score appears in either list below. A measured comparison needs
a shared benchmark run under the same conditions for every tool named, and
that has not happened yet (docs/closure/CLOSURE_REGISTER.md, item X-03).
What follows is one genuine strength per peer, read from that peer's own
documentation and independent coverage as of 2026-08-04.

### Direct open ecosystem peers

- **Cline.** Runs inside VS Code with Plan and Act kept as separate modes
  and human approval at every step, and supports model access through more
  than two dozen providers with the builder's own key, so a builder who
  already lives in the editor gets the agent without leaving it.
- **OpenHands.** Runs agent actions inside a sandboxed container by
  default rather than the builder's own shell, and ships four separate
  interaction surfaces, an SDK, a CLI, a desktop GUI, and a cloud control
  plane, so a task that goes wrong is contained rather than free to touch
  the host machine.
- **Ruflo.** Coordinates many specialized agents at once with memory
  shared across the group, so a task that genuinely needs parallel
  specialists, one on tests, one on docs, one on a specific module, does
  not have to be serialized through a single session.
- **GSD (Open GSD).** Drives its phase loop on top of several different
  underlying agent CLIs, including Claude Code, Codex, Copilot, and
  Cursor, rather than one, so a team split across tools can share a
  process without first standardizing on a single vendor's agent.
- **Superpowers.** Enforces a strict test-first, red-green-refactor cycle
  as a Claude Code skill, refusing code written before a failing test
  exists, which is a narrower and stricter guarantee on that one practice
  than BrotherMode's own broader law set asks for by default.
- **BMAD-METHOD.** Ships around twenty specialized role personas, product
  manager, architect, developer, QA, and more, with platform-agnostic
  workflows not tied to any single model or IDE, covering a fuller
  software development lifecycle with named roles than BrotherMode's own
  smaller role set.

### Hosted outcome platforms

- **Replit Agent.** Runs and revisits its own work inside a browser
  session for long unattended stretches, testing what it built and fixing
  what it finds, then deploys from the same environment it built in,
  including a QR-code path to a mobile build, with nothing to install
  locally first.
- **Lovable.** Turns a plain-language description straight into a
  deployed React front end with GitHub sync built into every plan, the
  fastest path in this comparison from a sentence to a shareable, running
  link.

## 4. Fairness rules this page follows

- No adoption metric, star count, install count, funding figure, or
  self-reported benchmark percentage appears anywhere in section 3. Every
  number of that kind that turned up while researching this page was left
  out on purpose, not overlooked, because none of it has been
  independently normalized against the same measure for BrotherMode.
- No numeric score, rating, or ranking appears anywhere on this page, for
  the reason stated in section 3: the shared benchmark run that a measured
  score would need has not happened yet.
- A disadvantage is named wherever this page names an advantage. Section 2
  states what each neighboring category does better than BrotherMode in
  the same paragraph that states the difference, not in a separate list a
  reader could skip past.
- A claim about BrotherMode's own behavior traces to a file in this tree:
  tools/bm_fence_hook.py, tools/test_bm_docs.py, docs/HOW-IT-WORKS.md,
  README.md, SECURITY.md, or capabilities.status.json. A claim about a
  peer is labeled desk assessment, because no file in this tree can carry
  evidence about a codebase this project does not own.
