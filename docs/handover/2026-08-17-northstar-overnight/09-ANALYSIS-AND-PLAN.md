Status: CURRENT. Ratified 2026-08-15, eight founder decisions recorded in the
store against work record e082b639. Board: the project's stable artifact link,
named in PROJECT.md. One founder task is outstanding, clearing the Bitbucket
workspace to five seats, and it blocks W12 and W13 rather than anything before
them.

# The north star push: self-analysis, positioning, and the two-week plan

Written 2026-08-15 (Saturday, 21:30 JST) on the founder's order: plan the
next two weeks against the north star, serve the the adopter team team's daily work,
and unify BrotherMode with BrotherSBE end to end. Six read-only agents ran
one wave, tiers declared per brief. Every claim below names the file or the
command that produced it, and the corrections this session made to its own
agents are kept in place rather than tidied away.

North star served: this page serves the CHANGE PASSPORT and VERIFIED
REALITY stages, and the plan it carries names a stage per work item.

## 1. What was actually checked, and by what

| Claim | How it was checked | Result |
|---|---|---|
| Repo health | `python3 scripts/doctor.py` | 11 of 12 proven, 1 skipped, 0 failed |
| The assurance product sees nothing here | `sbe status --json` | every store NO-DATA: no intake, no evidence, no task registry, no dossiers |
| The assurance product cannot read our fences | `sbe fences` | 52 lines, every one "did NOT enforce it" |
| The passport consumer exists | `ls ~/Documents/BrotherSBE/tools/sbe_passport.py` | present, 18,015 bytes, written 2026-08-15 18:42 |
| The passport consumer ships | `ls <plugin 3.2.0>/tools/ \| grep passport` | absent from the installed build |
| The passport producer exists | `grep -rln passport tools/` | only `tools/bm_idle.py`, a stage-name string. Nothing produces one |
| The install carries an identity stamp | `ls ~/.claude/skills/brothermode/INSTALLED-FROM` | no such file, so `check_install_identity` SKIPs forever |
| The install registers as a plugin | read `~/.claude/plugins/installed_plugins.json` | brothersbe present, brothermode absent |
| The measured 22-commit install skew | `diff -rq ~/.claude/skills/brothermode/tools tools` | 0 differing files. That defect is CLOSED today |
| Backlog depth | `python3 tools/bm_idle.py` | depth 57; 94 items total, 34 done, 3 blocked |
| Backlog names its stages | same command | 37 queued items name no chain stage; 74 of 94 overall |

Two corrections this session made to its own agents, kept because the
correction is the evidence:

1. An agent concluded that BrotherMode's automatic half "is inert on the
   install people actually have". Refuted by observation: this session's
   own start injected the BrotherMode laws digest, the progress-page
   verdict, the stall sweep and the handover detect. Those hooks ran. The
   real defect is narrower and still real: the clone is absent from the
   plugin registry and carries no `INSTALLED-FROM`, so the identity check
   can never reach a verdict and `/plugin` cannot manage it.
2. An agent proposed building an install-identity check. It exists, at
   `scripts/doctor.py:924`, registered at line 509. The gap is not a
   missing control, it is a built control that SKIPs forever because the
   documented install writes no stamp.

## 2. Self-analysis: where we stand against our own chain

The chain's own status table (`docs/NORTH-STAR-CHAIN.md`) grades fifteen
rows. Counted: three SHIPPED, one GOOD with a hole, five PARTIAL, five DO
NOT EXIST, one deliberately NOT OURS.

Working: execution provenance, behaviour, risk, required proof.
Partial: human intent, development method, evidence integrity,
accountability, human decision.
Absent: change passport, business impact, release readiness, production
observation, verified reality.

The four absent stages that are ours are consecutive, and they are the four
after the merge. The product is complete up to the pull request and blind
after it. That single sentence is the whole diagnosis, and the ninefold
hole list found the same thing from the opposite direction.

### The three weaknesses as a product, not as a codebase

1. **Zero external installs.** `PRODUCT-DIRECTION.md` section 16 requires
   five external users and twenty deliveries before the product is done.
   Queue item G2, the first cold tester install, is still `queued` and
   blocked on another person and machine. The north-star metric has never
   had a numerator, and the founder himself scored market proof 1 of 10.
2. **The documented install is the broken shape.** `docs/QUICKSTART.md`
   line 109 tells a new person to `git clone` straight into
   `~/.claude/skills/brothermode`. Hooks do load that way, but nothing
   registers the plugin and nothing writes the identity stamp, so the
   product's own identity check is permanently mute and the plugin
   surface cannot see it. One documented line produces that state.
3. **The engine dwarfs its promise.** Six public commands are promised;
   `tools/` holds 83 entries and `bm_store.py` is 19,132 lines whose
   import cost is paid three times per shell command (SBE5). Three
   unreconciled sources of truth for work items (SBE4). A stranger cannot
   learn this, and one person cannot maintain it.

### Where we overclaim, in our own words

- `capabilities.status.json` grades `single-writer-enforcement` as
  certified, defined by that same file as "proven in this tree today".
  It is proven in the tree. It is not proven on an install.
- `PRODUCT-DIRECTION.md` tagline reads "From intent to verified delivery"
  while the chain's own table reads "Verified reality: DOES NOT EXIST".
- `docs/plan/PROBLEMS-2026-08-16.md` lists SBE1's 22-commit skew as a
  live P1. It measures zero today. Listing a closed defect as open sends
  a reader away from the open one beside it.
- `docs/plan/DELIVERY-VS-FEEDBACK-2026-08-16.md` calls a written risk
  paragraph SHIPPED. This corpus's own standard, used against the team's
  own findings, is that an instruction to the model is not a control.

## 3. Benchmark against the competition, checked live 2026-08-15

The orchestration-layer table in `docs/plan/FINALIZATION-ROADMAP-2026-08-15.md`
stands. This session covered the gap it left: the Claude plugin and skill
ecosystem, and Anthropic's own first-party moves.

What nobody else ships, confirmed by opening their pages:

- **Enforced single-writer file ownership.** Anthropic's own Agent Teams
  documentation tells users to avoid same-file conflicts by convention,
  not by a block. No plugin found ships a write-refusing hook.
- **A handover close check that refuses a hollow pack.** Several handoff
  plugins exist at 1 to 8 stars; none refuse anything.
- **Forecast calibration that prints NO-DATA below a sample threshold.**
  The nearest analog is a 4-star time estimator with no refusal logic.
- **Progress pages written for a non-engineer.** The scan found only
  developer status lines.

Where the moat is genuinely weakening, and this is the part worth acting on:

- Anthropic's Claude Security plugin already ships verification over an
  agent's own work: independent verifier agents review every finding, and
  a revision-stamp file ties findings to a commit. That is our evidence
  and provenance pattern, first-party, scoped to security findings. The
  general case is still open, and it will not stay open.
- Checkpointing does not restore subagent edits, by Anthropic's own
  documentation, which is the strongest live argument for our fence. The
  changelog shows that seam being hardened release by release. The claim
  has a shelf life, not a permanent advantage.

## 4. Positioning, in one paragraph

Every product in this ecosystem competes on **capability**: more agents,
faster swarms, more skills, longer autonomy. Not one of them competes on
**accountability**. BrotherMode and BrotherSBE are two halves of a
delivery-control layer: BrotherMode records what one person's session
actually did, and BrotherSBE decides whether a change is fit to pass to
another person. The object that makes them one product rather than two is
the change passport, and its fourth field, what was NOT established, is
the thing no competitor ships and no green gate can fake. We are not a
faster way to write code. We are the record of what was done and what was
not proven, in a form the next human can act on.

The honest qualifier that belongs in the same paragraph: the moat is real
and unproven. Zero people outside this machine have installed it.

## 5. The seam is broken, and this is the architecture finding

`sbe status` inside this repository reports NO-DATA on every store,
because no `.sbe/` directory exists here. The two products have never been
connected on the machine where both are installed.

Worse, and verified by running it: `sbe fences` reads
`BrotherModeUp/STATE.md` and prints 52 lines, each saying it "did NOT
enforce it". It is parsing narrative history as live claims, including
lines that say a fence closed clean.

The reason is in BrotherMode's own store contract: **STATE.md is a
GENERATED view, never hand-edited truth**. The registry is a sqlite store
with an API. BrotherSBE is parsing the rendered human-readable page. That
reframes queue item O23: the question is not only which fence hook
survives, it is that the assurance product must ask the store instead of
reading the view. That is a founder decision, section 8.

Four other reach-arounds exist, none of them at the passport: the SBE test
suite hardcodes a BrotherMode tool path, and BrotherMode's toolkit
enumerates BrotherSBE plugin versions.

And one word means two different things across the seam. BrotherMode's
tier is EFFORT (T1 one session, T2 a few subagents, T3 a fleet).
BrotherSBE's tier is RISK (T0 to T3 from five intake answers). The same
STATE.md lines carrying "Tier T1" are what the assurance product parses.

## 6. The the adopter team team, answered end to end

Fourteen distinct struggles were recorded from the analyst lead, the engineering lead, the delivery lead, the non-developer reviewer,
the senior reviewer, the QA lead, and the live the reference change run. Nine of
the fourteen are owned by BrotherSBE, two by BrotherMode, two by both, one
by the adopter team itself.

The through-line nobody has drawn yet: the team's five queue numbers (41
waiting on development, 22 waiting on test resource, 23 waiting on the QA
lead, 11 in testing, 48 with a TBD end date) do not move because QC is the
bottleneck, and QC is slow because **nothing tells the tester what was not
checked**. Passport field 4 is literally that artifact. The same object
that closes the largest gap in our chain is the object that moves their
worst number. That is the plan's spine, and it is why the passport
outranks everything else.

Mapped directly onto passport fields:

- U4, decisions vanish into commit messages so we pay twice: field 1 and 2.
- U6, trust evidence from the build system, not somebody's laptop: field 3,
  which the consumer already reads from a receipt's `ciRunId`.
- U7, evidence with one check passes as green as evidence with all of them:
  field 4.
- U11, the PROVE step checks that documents exist, not that the build
  matches the design: field 4.

Not answered by the passport, and named rather than hidden: U1 (Windows
setup defeated the non-developer reviewer), U2 (the BA guide describes a handover practice the
team does not use), U3 (discussion before planning is a prompt instruction,
not a state), U12's assurance half (BrotherSBE is GitHub-only in code).

## 7. The two-host law, and where BrotherSBE breaks it

BrotherMode complies: `bitbucket-pipelines.yml` at the root, `docs/BITBUCKET.md`
with executed proof and honest UNVERIFIED labels.

BrotherSBE does not, in code: its pull-request verification hardcodes the
GitHub API root and accepts only GitHub tokens, its protections module
shells `gh api` for a GitHub branch ruleset, and its build-origin detection
reads `GITHUB_RUN_ID`. That last one feeds `ciRunId`, which is exactly
passport field 3, so the seam inherits the GitHub assumption. There is no
Bitbucket pipeline file in the plugin or its source repo.

BrotherSBE's own research file says it plainly: this team is on Bitbucket,
and both of those commands are dead here.

## 8. What the founder's own vision documents say, read in full

`docs/vision/INTEGRITY-SYSTEM-2026-08-15.md` (2043 lines) and
`docs/vision/STARTUP-10-10-WBS-2026-08-15.md` (1878 lines) were read end to
end this session. Four findings change the plan.

**The intake was wrong on a load-bearing number.** It records a twelve-part
WBS. The blueprint has EIGHTEEN parts, 1.0 to 18.0. A plan sized off twelve
omits ownership and review routing, merge assurance, team UX, release
assurance, security, the quality system and external validation, which is
where most of the unbuilt work lives.

**The two documents contradict each other on who owns evidence freshness.**
The vision's own no-duplicate-governance table gives BrotherMode "Evidence
freshness: Owns". The blueprint puts the freshness engine inside the shared
team plane and says BrotherSBE computes it. Both cannot be true. This is a
forcing condition and goes to the founder, not to a silent resolution. The
recommended split, which the envelope's own shape already implies:
BrotherMode owns evidence PRODUCTION, BrotherSBE owns freshness EVALUATION,
because only it sees the head revision of every bound pull request.

**The Change Envelope is the only labour-positive object in either
document.** Everything else adds typing. The envelope removes it, because
it carries outcome, risk, ownership, acceptance counts and evidence across
the seam so nobody types the same truth twice.

**The blueprint's terminal deliverable is a blocking merge check** on
protected branches across both hosts. That is the largest new blocking gate
either document proposes, and the no-new-gates rule means it needs a
founder decision when it is SCHEDULED, not when it lands.

Six mechanisms fail the labour test for a team of 2 to 15 and are cut or
deferred in the plan below: the hosted team plane as specified (cut to a
hashed envelope file in the repository), the 25-row mandatory gate table
(deferred to the GA claim, five metrics kept), the impact graph past its
seventh package and its BLOCK severity (cut), most of release assurance
(one package kept), the eleven mandatory contract fields at T0 (three
kept), and the 98 percent governed-change coverage target (derive the
identifier from the branch name or accept the work is ungoverned at T0).

### The passport and the envelope are the same seam at two fidelities

The chain specifies a five-field passport and its Decision N1 explicitly
refuses to make it a schema with a lifecycle. The vision specifies a rich
hashed envelope. The plan builds the PASSPORT first and treats the envelope
as its growth path, for one reason: the passport's consumer is already
written and tested in the sibling repository, so the producer is the only
missing half. Building the envelope first means building both sides from
nothing with no consumer to test against.

## 9. The plan

Three moves, in this order, because each unlocks the next.

**MOVE A, CONNECT.** The passport seam end to end, one real change through
both products. Closes the largest gap in the chain, IS the architecture
sync, and hands the tester the list of what nobody checked.

**MOVE B, INSTALL.** The documented install registers the plugin and writes
its identity stamp, then reaches the analyst lead and the engineering lead on Bitbucket. This is the
number the founder scored 1 of 10.

**MOVE C, CLOSE THE LOOP.** The acceptance record and the post-merge
outcome recorder, which are the last four stages of the chain.

Model tier per item follows the blueprint's own routing matrix, translated
to this machine's tiers: haiku for mechanical bulk, sonnet for scoped
implementation from a decided spec, the strongest tier for architecture,
adversarial review and synthesis. One rule is imported that this repository
does not currently enforce: **the planner is not the final verifier**, so
at tier T2 and above the reviewer runs in a different context from the
agent that designed the change.

### Today, Saturday 2026-08-15

| Item | What | Stage | Tier | Done-check |
|---|---|---|---|---|
| T1 | This analysis and the board, published | intent | this session | artifact live, `bm_progress_check.py` exit 0 |
| T2 | Founder answers the decision windows | human-decision | founder | answers recorded as decisions in the store |
| T3 | Retire the two overclaims found tonight: SBE1 as a live P1, and `single-writer-enforcement` graded certified | evidence-integrity | haiku | `python3 tools/test_bm_docs.py` green, doctor unchanged at 11 of 12 |
| T4 | Commit and push tonight's work | provenance | this session | gate exit 0 quoted, HEAD equals upstream |

### Week one, Monday 2026-08-17 to Sunday 2026-08-23

| Item | What | Stage | Tier | Done-check |
|---|---|---|---|---|
| W1 | `tools/bm_passport.py`, the producer, writing the three fields execution owns | passport | sonnet builds, strongest reviews | `sbe_passport.py --root . --json` reads 5 of 5 carried and field 4 no longer says field 2 is not established |
| W2 | Ship `sbe_passport.py` into the plugin build and wire it to the CLI | passport | sonnet | `sbe passport --json` exit 0 from the installed plugin, not the source tree |
| W3 | One real change carried end to end through both products | passport | strongest, orchestrated | a passport for a real commit range, quoted, field 4 non-empty |
| W4 | The install registers the plugin and writes `INSTALLED-FROM`; QUICKSTART line 109 replaced | method | sonnet | doctor check 11 moves SKIP to PASS on a fresh install; the plugin registry lists brothermode |
| W5 | The three P0 erasure and redaction defects: SBE14, SBE10, SBE9 | evidence-integrity | sonnet each in a worktree, strongest verifies adversarially | each documented reproduction fails to reproduce, quoted |
| W6 | Break the tier word collision: BrotherMode effort becomes E1, E2, E3 | provenance | haiku sweeps, strongest reviews | no bare "Tier T" survives in a rendered STATE.md; both products' docs disambiguated |
| W7 | O23 reframed: the assurance product asks the store instead of parsing the generated view | provenance | strongest designs, sonnet builds | `sbe fences` here prints zero unparseable lines, or an honest NO-DATA naming the store API |
| W8 | Tester pack to the analyst lead and the engineering lead with the Bitbucket path | verified-reality | founder-gated | an install transcript on disk from a machine that is not this one |

### Week two, Monday 2026-08-24 to Sunday 2026-08-30

| Item | What | Stage | Tier | Done-check |
|---|---|---|---|---|
| W9 | The acceptance record: who accepted, when, against what (hole H2) | human-decision | sonnet builds, strongest reviews | an accepted change names its accepting person and the criteria it was accepted against |
| W10 | The post-merge outcome recorder: the four observables (H1, H3, H5) | verified-reality | strongest designs, sonnet builds | one merged change reports reopen, rollback, acceptance-held and queue-movement, or NO-DATA per observable |
| W11 | Evidence record gains `commit_sha`, `artifact_digest`, `producer`, `scope`, `result` | evidence-integrity | sonnet | evidence cannot be recorded FRESH without an exact repository and revision |
| W12 | BrotherSBE stops assuming GitHub: provider-neutral origin detection so `ciRunId` works on Bitbucket | evidence-integrity | sonnet builds, strongest reviews | a Bitbucket pipeline run produces a receipt whose origin is the build system, not NOT-ESTABLISHED |
| W13 | Bitbucket certification | release-readiness | founder-gated on the seat blocker | the UNVERIFIED labels in `docs/BITBUCKET.md` close with quoted output |
| W14 | The decorrelation rule enforced at T2 and above | required-proof | strongest | a review whose verifier shares the planner's context is refused, with a test |
| W15 | Chain-stage backfill: 74 of 94 queue items name no stage | intent | haiku | `bm_idle.py` reports zero unstaged items or names each survivor with a reason |

### What this plan deliberately does not do

No hosted team plane. No impact graph. No blocking merge check scheduled
without a separate founder decision. No new engine features outside the
three moves. Each is a recorded decision with a flip condition, and the
flip condition for the team plane is two engineers needing a verdict on the
same change within seconds of each other.

