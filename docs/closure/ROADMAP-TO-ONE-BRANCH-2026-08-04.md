# Roadmap: one branch, every feature deployed

Status: CURRENT. Written 2026-08-04 against `main` at `268ee33`, tag
`v2.0.0-rc.13` published. Every fact below was read off disk or off the remote,
not recalled. No em or en dashes.

The founder asked a two-part question: what stands between here and (A) a
repository with exactly one branch, and (B) every built feature actually
deployed. Those are different problems and they are separated below.

---

## LOOP 1: One branch. READY, blocked only on a permitted command.

**Goal.** `origin` carries `main` and nothing else.

**Measured state, 2026-08-04.** Five remote branches exist. Four are dead
weight, and this is proven rather than assumed, two independent ways per
branch: zero unique commits (`git rev-list --count origin/main..origin/<b>`)
AND the branch tip is an ancestor of main (`git merge-base --is-ancestor`).

| Branch | Unique commits | Contained in main |
|---|---|---|
| `feature/closure-final-c02-c04-c06-c11` | 0 | YES |
| `feature/explainer-personas` | 0 | YES |
| `feature/product-craft-review` | 0 | YES |
| `release/2.0-final` | 0 | YES |

Nothing is lost by deleting any of them. Local branches: `main` and the closure
branch. Worktrees: the primary checkout alone, already correct.

**Why it is not done.** `git push origin --delete` is refused by this machine's
safety classifier, which blocks destructive remote operations. That is a harness
guard, not a project rule, and it is not something a session can waive.

**The command.** One line, deletes all four:

```
git push origin --delete feature/closure-final-c02-c04-c06-c11 feature/explainer-personas feature/product-craft-review release/2.0-final
```

Then the local leftover: `git branch -d feature/closure-final-c02-c04-c06-c11`
(lowercase `-d` refuses if anything is unmerged, which is the safety property
worth keeping; do not reach for `-D`).

**Done-check.** `git branch -r` lists `origin/HEAD` and `origin/main` only, and
`git branch` lists `main` only.

**Note for the record.** A previous session recorded a standing founder call to
leave remote refs untouched. The founder's 2026-08-04 instruction to reach one
branch supersedes it. Stating it rather than silently reversing it.

---

## LOOP 2: The records disagree with the code. NOT STARTED.

This is the highest-value loop after Loop 1, because a stale record is worse
than a missing one: it is read as current.

**2a. `docs/NOT-FINALIZED.md` item 2 is FALSE as written.** It says "Bash writes
are not gated by the fence hook. OPEN", and explains that gating Bash would need
a design rather than a patch. That design landed today as C-02: under
`BM_FENCE_MODE=enforced` an obvious destructive command aimed at BrotherMode's
own store or fence directory is refused, and a control snapshot now detects
changes to the enforcement state itself. The item must move to PARTIAL and carry
the three limits verbatim (literal matcher not a shell parser, no operating
system containment, deliberate fail-open when `bm_store.py` cannot be imported).

**2b. Sweep the same file for other items today's work moved.** Candidates seen
but NOT verified: item 6 (recovered work owner-only on POSIX only) may be
affected by the C-09 quarantine chmod; item 9 (three scoring checks red) and item
10 (suites cannot be run concurrently) are unchecked against today's tree. Each
needs reading, not assuming.

**2c. `docs/PACKAGING.md` is stale on its own counts.** It says six console
scripts and nine `bm_*` modules. Today it is twelve and seventeen. Flagged during
the C-06 work and deliberately not fixed then, because it was outside that
lane's fence.

**2d. `docs/REMAINING.md` item 1 calls the telemetry audit the biggest gap.**
Verify whether that is still true after today, and correct or confirm it.

**Method.** Read-only fan-out to check each claim against the code, then one
writer applying corrections. Never edit a DATED entry to agree with today: add a
dated correction under it, which is this project's own anti-gaming rule.

**Done-check.** `python3 tools/test_all.py` green, and a grep for each corrected
claim returns the new wording.

---

## LOOP 3: The public install path. PARTLY DEFERRED by founder decision.

`docs/NOT-FINALIZED.md` item 11 defers Phase 3, the public install, on the
founder's own sequencing call: blockers first, nothing public ships a nice
install for an unsafe tool. It was corrected 2026-08-01 to note part has since
landed.

**What is now DEPLOYED and proven**, this session: the pinned clone install.
`git clone --branch v2.0.0-rc.13` was run against the published tag into a
throwaway directory; `skills/`, `commands/` and `.claude-plugin/` are all
present, `VERSION` reads `2.0.0-rc.13`, and `verify-install.sh` inside that fresh
clone reported PASSED at exit 0.

**What item 11 still names as missing**, and none of it is verified against
today's tree: a one-command installer, hooks written by the installer rather than
by hand, and a Windows-native hook dispatcher, because the documented install
path is still shell-dependent.

**The unverified one that matters most.** The repository ships
`.claude-plugin/marketplace.json` and `plugin.json`, so a plugin-marketplace
install path exists in the tree. NOBODY HAS INSTALLED THROUGH IT END TO END and
this document will not claim otherwise. That is the single highest-value
verification left, because it is the path a beginner would actually take.

**Done-check.** A real plugin install into a throwaway `HOME`, with the
resulting hooks listed and one command run through them.

---

## LOOP 4: Deploy-blocking defects still open. NOT STARTED, needs triage first.

`docs/NOT-FINALIZED.md` carries roughly a dozen entries still marked OPEN,
PARTIAL, UNPROVEN or DEFERRED. They are NOT all worth closing, and treating them
as one list is how a session burns a day on the wrong ones. Triage into three
buckets before touching any:

1. **Blocks a user.** Fix now.
2. **Deliberately deferred with a stated reason** (the FTS5 fast path shipping
   disabled, `relevant` deprecated but not removed, `retrieval_uuid` nullable
   forever). Leave, and make sure the reason is still true.
3. **Honest limits that cannot be fixed by code.** Move them to
   `docs/KNOWN-LIMITS.md` so they stop reading as a backlog.

**Done-check.** Every entry in that file carries one of the three labels and a
date, and the count of untriaged entries is zero.

---

## LOOP 5: The telemetry audit pass. NOT STARTED. Named as the biggest gap.

`docs/REMAINING.md` item 1: `tools/bm_telemetry.py` is about 1,211 lines and
holds the corrections ledger, the outcomes ledger, the handover export and
project identity. Roughly thirteen findings from the original audit live in it
and almost none are fixed, because the work went into the ownership path (the
store) and the recovery path (the autosave) instead.

This is a real, large, single-file body of work. It wants its own design pass
before any edit, and it is the wrong thing to start late in a session.

**Done-check.** Each of the thirteen findings is either fixed with a test that
fails without the fix, or recorded as a limit with a reason.

---

## LOOP 6: The measurement gap. NOT CLOSABLE BY WRITING CODE.

Register items X-01 to X-06. Named here so no roadmap reads as though finishing
loops 1 to 5 would finish the project.

- **X-01** Second runtime conformance. Codex is authenticated but out of credits.
  Adding credits is a payment and is permanently the founder's.
- **X-02** External user study. Needs participants who did not build this.
- **X-03** Benchmark corpus. Thirty projects, five users, three operating
  systems, two runtimes.
- **X-04** Sustained dogfood. Real use EXISTS, weeks of daily founder use plus
  other people on their own machines. The MEASUREMENT does not: no counted
  projects, no recorded failure or rework rate, no observed outside participant,
  no comparison against working without the tool.
- **X-05** Ecosystem thresholds. Twenty-five active users, five contributors, two
  maintainers able to release.
- **X-06** Fault-injection reliability. The protocol asks for 10,000 sequences;
  zero have been run, so no reliability figure exists to report.

These are why a 9 out of 10 cannot honestly be claimed, and why the closure
register keeps them visible rather than letting a scorecard omit them.

---

## Sequencing, and why this order

Loop 1 first: it is one command, fully proven safe, and it is half the founder's
stated goal. Loop 2 next, because every later loop reads those records to decide
what to do, so working from stale ones multiplies the error. Loop 3 third,
because the plugin path is the beginner's path and it is unverified. Loops 4 and
5 are real engineering and want their own sessions with a design pass first. Loop
6 never closes from this chair.
