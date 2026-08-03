# Proposal: Full-Auto Mode and Codex-Execution Mode

Status: CURRENT. Written 2026-08-02. The founder ratified both decision windows
the same day (reversible-everything autonomy with the five floors retained, and
the trigger-point silence-biased sentinel over Meta's every-step variant), and
Phase 1 was built and landed against this document that night. Phases 0 and 3
are blocked on OpenAI credits, a founder-only floor; Phase 2 is specified in
docs/superpowers/specs/2026-08-02-full-auto-phase2-design.md and not yet built.
Work record: d6cfdc55 (proposal-full-auto-and-codex-execution-modes).
Founder rules surfaced before writing: e5c8f605, 7bb759b1, ca5c0a4e (all three shaped Part 4 and Part 5).

## The outcome in three sentences

BrotherMode gets two new operating modes: Full-Auto, where it takes a project from kickoff to delivery on its own and interrupts you only when a decision is genuinely yours, and Codex-Execution, where Claude (Fable) plans and verifies while OpenAI's Codex executes the mechanical work on its own separate quota. Both modes are built on the same new piece of machinery, a Memory Sentinel adapted from Meta's July 2026 research, which is the strongest published answer so far to the exact failure our own defect ledger records most often: an agent that knew the right thing earlier and stopped acting on it. The recommended path is four build phases starting with a 20 to 90 minute proof that Codex can be driven end to end on this machine, and one decision from you is needed before any build starts.

## Part 1: What Meta actually found

The paper is "Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents", from Meta AI researchers (Yifan Wu and seven co-authors), submitted 2026-07-09, arXiv 2607.08716. The link you sent (powerdrill.ai) carried only the paper's title and no content, so everything below comes from the arXiv paper itself, cross-checked against independent reporting of the headline number.

The problem they name: behavioral state decay. In their words, information that should shape future actions "stops influencing the agent's next decision" even though it "may remain present in the transcript, or may even remain within the model's context window." The agent read it, understood it, and stopped steering by it. They measured three recurring patterns:

1. The agent identifies a requirement early and later violates it while fixing something unrelated.
2. The agent observes that an approach failed and later retries a near-identical variant.
3. The agent diagnoses an error pattern and later treats the same pattern as new.

Their fix is not a bigger context window and not a retrieval database. It is a second agent, a memory agent, that runs alongside the worker without modifying it. The memory agent does two things at every step:

- It maintains a structured memory bank with three parts: a private status view of progress and risks (never shown to the worker), knowledge memories (verified facts, requirements, file paths, environment properties), and procedural memories (what failed, what fixed it, which hypotheses were ruled out).
- It decides between injecting one short reminder into the worker's next turn, or staying silent. Silence is an explicit action the memory agent chooses on purpose, with its own reasons, not a default it lands in. Reminders are transient context, never edits to the worker's instructions.

The numbers, from their two benchmarks:

| Benchmark | Worker model | Alone | With memory agent | Gain |
|---|---|---|---|---|
| Terminal-Bench 2.0 | Claude Sonnet 4.5 | 37.6% | 45.9% | +8.3 points |
| Terminal-Bench 2.0 | Claude Opus 4.6 | 43.5% | 45.9% | +2.4 points |
| Tau-squared-Bench | Claude Sonnet 4.5 | 55.0% | 61.8% | +6.8 points |
| Tau-squared-Bench | Claude Opus 4.6 | 66.2% | 68.7% | +2.5 points |

Four findings in the paper matter more to us than the headline gains:

1. Dumping the whole memory bank into the worker's context made things worse than selective injection (61.5% vs 64.3% macro average). Passive memory exposure is not the answer; calibrated intervention is.
2. Always injecting, with no silence option, also lost to calibrated silence (63.5% vs 64.3%).
3. A general-purpose memory retrieval system (Mem0) underperformed their structured approach by 2.2 points and on one domain fell below having no memory at all.
4. An untrained smaller model used as the memory agent actively hurt the worker (reward fell from 0.709 to 0.693). Calibration, knowing when NOT to speak, is the hard part and the value.

The transferable lesson, in one line: memory pays only when a separate process decides, per moment, whether a specific reminder is worth an interruption, and the default answer is no.

## Part 2: What our own defect ledger teaches

I mined the vault's Failures-Index, the BrotherMode outcomes ledger, the known-mistakes ledger, and your recorded corrections. Grouped, the strongest failure families and what each demands from the new modes:

1. Stale-context failures. A brief quoted a worktree 24 commits behind and both its "failing" tests were already green; agent worktrees were cut behind main and file-copy landing deleted whole tasks; a four-agent fleet spent a full round on a sandbox three commits stale. This family IS behavioral state decay, on our own machine, with receipts. It is the direct case for the Memory Sentinel's freshness reminders.
2. Repeat-failed-attempt failures. Twelve engine stalls retried during the parallel night; two dead engine runs cost 1.35M tokens and four hours with zero files written. Two of your approved rules (7bb759b1, ca5c0a4e) already encode the escape ladder. The sentinel's procedural memory makes this mechanical instead of remembered.
3. Claimed-done-without-verification failures. An aborted batch edit logged as applied; success reported on an unchecked write, three times in one project; the 2026-08-02 correction you gave (3 of 5, "did not clean after yourself properly") where I ran the verifier only after you doubted me. Full-Auto cannot exist unless every done claim carries a receipt produced after the last edit, and the close-of-run sweep is a gate rather than a habit.
4. Work-loss failures. Scratchpad wipes, stash races, git add -A sweeping a concurrent session's work. Mostly solved by machinery that already ships (autosave, write-ahead intent log, precompact briefs). Full-Auto extends these, it does not need new invention here.
5. The spec itself is the defect. Four times in one project, a specification I wrote was the flaw, and every time it surfaced because the executing agent verified instead of complying. This is the one place I push back on the request as worded, in Part 4.
6. Reporting opacity. The parallel night felt complicated and opaque to you, and your rule e5c8f605 now requires one line per stream before any detail. Full-Auto reporting is designed around that rule.

Meta's paper and our ledger agree on the diagnosis. Their fix covers families 1, 2, and partially 3. Families 3 through 6 are covered by mechanisms we already built or by design choices below. That agreement is why I recommend building this rather than treating the paper as interesting reading.

## Part 3: Full-Auto Mode

What it is: you state the outcome once at kickoff, sign an autonomy contract, and BrotherMode takes the project to delivery. It drives the apps, the browser, Xcode, the simulators, the terminal, and the file system. It asks you nothing unless it hits a forcing condition. You get pulse updates you can read in thirty seconds, and a full decision log you can audit any time.

The autonomy contract, signed once per project at kickoff:

- Outcome and done definition: what will exist, and the checks that prove it.
- Scope of control: which apps, repos, and directories it may drive. Your standing directive of 2026-07-26 already authorizes controlling Xcode and other apps; the contract records scope per project so an audit can compare actions against it.
- Spend ceiling: a token and time budget with a circuit breaker. Crossing 80 percent of either pauses new work and sends a pulse; crossing 100 percent stops.
- Risk envelope: which classes of action are pre-approved (all reversible edits, builds, test runs, local commits) and which stay gated.
- Question policy: the list of forcing conditions, and nothing else, may interrupt you.

What "full access" honestly means. Everything reversible, inside the signed scope, without asking: that is the mode. Five floors stay with you in every mode, permanently, because they are enforced above BrotherMode (by the platform I run on and by your own standing directives), and no mode we design can or should remove them:

1. Credentials, passwords, 2FA codes: never typed, never automated.
2. Payments and any movement of money: never executed.
3. Account creation and sign-ins: prepared up to the consent screen, final click yours.
4. Permanent deletions and production state: printed first, confirmed explicitly.
5. Publishing and releases: founder-gated unless the contract pre-signs a named, specific release.

A Full-Auto run that hits one of these floors does not stall: it queues the item, prepares everything up to the human step (the five-minute click path), and continues all work that does not depend on it.

The question policy. Interruptions are limited to forcing conditions, which are today's L6 list plus the floors: a design-changing ambiguity, a contradiction between what you said and what the machine shows, a hard-gate collision, a disproven plan assumption. Everything else becomes a stated assumption, logged, reversible, and reviewable in the pulse. Non-urgent questions batch at phase boundaries instead of interrupting. The target is zero to three interruptions per project.

The Memory Sentinel, adapted from Meta to our machinery. This is the new build. Meta ran their memory agent as a second model call at every single step; that is the faithful version and also the expensive one. Our adaptation:

- The bank maps onto the store we already have (schema 12), adding the three shapes: private status, knowledge entries, procedural entries. Much of the raw material already exists: the write-ahead intent log, precompact briefs, the fence set, approved rules from bm_learn, the vault's failure notes. What is missing is precisely Meta's second half: a process that decides, at defined moments, whether to inject one of these facts back into the working context.
- Trigger points, instead of every step: at phase boundaries; before any action the intent log classifies as risky; immediately after any failure; every N tool calls (N tunable, start at 15); and at compaction or resume, which our ledger shows is our single worst decay moment.
- Injection discipline, copied from Meta because their ablations earned it: one short reminder or explicit silence; never strategic advice; never restating what is already on screen; silence-biased at launch. Their data shows an uncalibrated memory agent makes the worker worse, so ours starts strict and loosens only against measured evidence (interventions later judged useful vs noise, tracked in the ledger like everything else).

Safety net: kill switch (you say stop, everything checkpoints and halts); checkpoint commits at every green state; pulse updates opening with one line per workstream (your rule e5c8f605); the decision log as a complete audit trail.

Prerequisite, stated plainly: the consent setup from earlier today is still not run. BrotherMode writes nothing durable, including sentinel memory, until you run `python3 ~/.claude/skills/brothermode/scripts/setup.py` once. Full-Auto cannot ship before that.

## Part 4: Codex-Execution Mode

What it is: Fable (Claude, in Claude Code) does everything that requires judgment: planning, decomposition, specification, review, acceptance. Codex (OpenAI's agent, running the newest GPT model your plan offers) does the mechanical execution of precisely specified packets. Fable then verifies every result before it lands. Planning and verification never leave Fable; execution never carries discretion.

Facts about this machine, checked today, 2026-08-02:

- Codex is installed and authenticated: `~/.codex/config.toml` exists, model set to `gpt-5.6-sol` with reasoning effort `xhigh`, auth dated July 23, logs touched today at 13:26 through the ChatGPT desktop app.
- The standalone `codex` command line tool is NOT on the PATH. Driving Codex from scripts needs it installed once (from memory, unverified: `npm install -g @openai/codex`; the exact package name gets confirmed in Phase 0, never trusted from memory).
- Our own runtime registry (docs/RUNTIMES.md) already records Codex CLI as a known runtime whose hook payloads are UNVERIFIED, and the delegation law already says cross-runtime dispatch stays out of use until one runtime has been driven end to end. Phase 0 exists to satisfy that law, not to bypass it.

The packet contract. Every unit of work Codex receives is a standalone brief per the existing delegation law: goal, exact files it may read and write, constraints, return format, a runnable done-check, and a budget. Two additions that our incident history made law: a freshness assertion Codex must run and quote back before doing anything (because a fleet once reported confident findings about code that no longer existed), and a halt-and-report rule, below.

Isolation. Codex works in its own git worktree, never in the shared tree. Reason: our one-writer-per-file fence is enforced by a Claude Code hook, and that hook's contract is unverified inside Codex, and our law says an unverified fence is worse than no fence because it fails open while looking installed. A private worktree is a fence made of mechanism instead of convention. Merging happens only after Fable's verification passes.

Verification, refute-first. For every returned packet, Fable re-runs the done-check itself (a pasted green line is a claim, the re-run is the evidence), reads the full diff as a hostile reviewer, and checks the diff contains only the described change. The executor never verifies its own work; the verifier never edits the work it judged. Both sentences are already law; this mode inherits them.

Escalation ladder, reusing your approved rules: a packet that fails its done-check twice on Codex is not looped a third time; it moves back to a Claude session with the failure evidence attached (the same shape as rules 7bb759b1 and ca5c0a4e, which you approved after two dead engine runs cost 1.35M tokens and four hours).

One honest pushback on the request as worded. You asked that "Codex just executes and only follows the detailed instructions given by Fable." Ninety-five percent of that is exactly right and is the design above. The five percent I recommend keeping: when the packet contradicts what Codex actually observes in the tree (a file the packet names does not exist, a test the packet says is red is already green), it must halt and report rather than comply. Our ledger records four separate times the specification itself was the defect, and every one surfaced only because the executor verified instead of obeying. Blind compliance is the one property our own history says is dangerous. This is not discretion, it is a tripwire; Codex still never chooses an approach.

Why this mode is worth having at all: Codex runs on a separate quota and a separate vendor, so mechanical bulk work stops consuming the Claude capacity that judgment needs; the venue-selection law already names "a second agent when its separate quota genuinely helps" as a recognized move. It also gives us vendor redundancy on execution.

## Part 5: What the two modes share, and how they compose

The Memory Sentinel, the receipts discipline, the decision log, and the question policy are one shared layer, built once. Full-Auto can contain Codex-Execution: in a Full-Auto run, Codex is simply one of the executors the orchestrator dispatches, under the same packet contract. Building the shared layer first is why the phases below are ordered as they are.

## Part 6: Build plan and forecast

Phase 0, prove Codex end to end. Install the CLI, drive one small real packet through plan, execute, verify, merge. Record the result in docs/RUNTIMES.md with date and version.
Likely time: 20 to 90 minutes. Token range: 5k to 20k. Confidence: medium.
Why: the app is installed and authenticated (config and auth files read today), but the CLI path, the headless invocation, and sandbox flags are unverified on this machine.
Reforecast after: the first packet returns.

Phase 1, Memory Sentinel MVP. The three bank shapes in the store, the five trigger points, silence-biased injection, and the measurement counters. Split into three subtasks (bank, triggers, injection policy) because the whole exceeds the 140k splitting threshold.
Likely time: 0.5 to 2 working days. Token range: 60k to 140k. Confidence: medium.
Why: the store's chained migration pattern is documented and was read today (the Loop 1 brief records the migration chain in bm_store.py and the schema 11 to 12 precedent), so adding tables follows a proven path; the injection policy and calibration counters are new design with no precedent here.
Reforecast after: the bank migration passes its tests.

Phase 2, Full-Auto contract and question policy. The contract recorded at kickoff, the forcing-condition interrupt list, the circuit breakers, the kill switch, pulse format.
Likely time: 1 to 4 hours. Token range: 20k to 60k. Confidence: medium.
Why: most parts extend existing machinery (kickoff, pulse, budgets); the circuit breaker is new.
Reforecast after: Phase 1 lands, since the contract references sentinel state.

Phase 3, Codex-Execution pipeline. Packet generator, worktree dispatch, verification harness, escalation ladder, RUNTIMES.md updates.
Likely time: 2 to 6 hours. Token range: 40k to 90k. Confidence: low until Phase 0 reports.
Why: everything downstream of Phase 0's findings; headless behavior on this machine is the unknown.
Reforecast after: Phase 0.

Phase 4, calibration loop. Run both modes on real work, measure sentinel interventions (useful vs noise), loosen or tighten the injection policy on evidence only. Ongoing; the first review after ten recorded interventions.

These envelopes come from the project's planning tables, not from measured history of these exact features. Known unknowns: Codex CLI headless flags, the sentinel's real token overhead per trigger, and whether consent setup lands before Phase 1.

## Part 7: Risks, and what I recommend against

- Against literal unlimited access. The five floors in Part 3 are not restrictions I can lift, and a proposal that pretended otherwise would be selling you something that does not exist.
- Against a chatty sentinel. Meta's own ablations show always-inject loses to calibrated silence and an uncalibrated memory agent hurts the worker. Ours launches silence-biased or not at all.
- Against blind-compliance Codex. Four spec-was-the-defect incidents say the halt-and-report tripwire stays.
- Against skipping Phase 0. Wiring a second vendor into the write path on documentation alone is exactly the unverified-fence mistake our law already names.
- Residual risk, quality drift over long autonomous runs: this is the exact risk the sentinel plus receipts exist to hold down, and Meta's data shows the largest gains precisely on long-horizon terminal work. It does not go to zero; the pulse and the audit log are the honest backstop.
- Residual risk, vendor drift: Codex behavior can change under us. Mitigation: RUNTIMES.md records verified date and version, and anything older than 90 days counts as stale, matching the existing recipe rule.

## Sources

- Meta paper (opened and read): https://arxiv.org/abs/2607.08716 and https://arxiv.org/html/2607.08716v1
- Headline number cross-check (second source): https://aiweekly.co/alerts/metas-memory-agent-lifts-claude-sonnet-45-by-83-points
- Your link, which carried only the title: https://chat.powerdrill.ai/discover/summary-remember-when-it-matters-proactive-memory-agent-cmrgum6hpk7i607r68f9vog0a
- Machine facts: ~/.codex/config.toml, ~/.claude/skills/brothermode/docs/RUNTIMES.md, both read 2026-08-02.

## Decisions needed from you

1. The autonomy floor: confirm Full-Auto means "everything reversible inside a signed scope" with the five floors staying yours. Highest stakes, blocks Phase 2.
2. Sentinel cost posture: trigger-point sentinel (recommended) or Meta-faithful every-step watcher at roughly 5 to 10 times the overhead. Blocks Phase 1 design.
3. Go or hold on Phase 0 now: the Codex proof is cheap and reversible and can start today. Blocks nothing else if held.
