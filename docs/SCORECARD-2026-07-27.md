# Where the dimensions actually stand, 2026-07-27

An external comparison scored BrotherMode V2 against native Claude Code and
returned an overall of 7.6 "until blockers are fixed", with security and product
maturity at 5.5 and recovery at 6.8.

The blockers are fixed. This page says what that did and did not move, and it is
deliberately unflattering where the honest answer is unflattering. Two rules
applied to every line below:

- A self-score caps at 8 without external validation named as evidence.
- A dimension that did not move says so, rather than being quietly re-described.

## What is now true, proven by command

All 17 findings from the adversarial audit are closed. CI is green on Linux,
macOS and Windows across both supported Python versions, with the recovery suite
included, which it never was before today. Suites: 92 legacy, 244 store, 34
recovery, 49 fence hook.

| Dimension | Their number | Now | Evidence, and why it is capped where it is |
|---|---:|---:|---|
| Security and product maturity | 5.5 | 8.0 | All 8 release blockers closed, each reproduced by execution BEFORE the fix. External validation named: the audit itself, plus CI on three platforms. Capped at 8, not higher, because it has still never run on a real project. |
| Recovery design | 6.8 | 8.0 | The false "your files are autosaved" claim is gone; the check is present-tense and re-resolves the ref. Recovery suite now runs in CI on every platform. Capped: recovered work is owner-only on POSIX ONLY, and handovers are lock-serialized rather than transactional. |
| Verification and quality governance | 8.4 | 8.0 | DOWN, deliberately. Two mechanical gates this project already had (the write-site inventory, the doc-drift check) CAUGHT real problems tonight that humans and agents had missed. But three of my own checks this week were incapable of failing until calibrated. An honest number goes down when the evidence says the practice was weaker than the score implied. |
| Multi-agent orchestration | 8.0 | 8.0 | UNCHANGED. Ten agents ran tonight across four waves with disjoint fences and no collision, which is the good news. The bad news is that I dispatched three of them BEFORE writing their fences, and gave two agents the same file as an "add-only" fence. The practice did not improve; only the outcome was lucky. |
| Simplicity | 6.8 | 6.8 | UNCHANGED, and this is the honest headline. Nothing shipped today made the tool simpler. The always-on cost is still 10,407 tokens before the first useful action. The design to fix it is written and measured, and NOT built. |
| Setup and immediate usefulness | 6.8 | 6.8 | UNCHANGED. Deliberately deferred: the founder chose blockers first, and nothing public should ship a nice install for an unsafe tool. |
| Small, contained tasks | 7.2 | 7.2 | UNCHANGED, same reason as simplicity. Every trivial task still pays the full ceremony cost. |

## The claim that changed shape rather than improving

"Two agents cannot write the same file" was never true. It is now closer, and
still not that:

- BEFORE: the fence was a ledger. Nothing checked a write against a claim.
- NOW: a PreToolUse hook blocks a write outside an active claim, and session
  identity is no longer a value printed in the file every session reads.
- STILL NOT: Bash writes bypass it. Any process running as this user can read the
  token and impersonate. The hook is shipped but NOT installed by default.

So the supportable claim is "two REGISTERED writers cannot SILENTLY write the
same file, and bypassing it now takes deliberate effort rather than an accident."
Anything stronger would be the same category of overstatement the audit found.

## What did not move, stated plainly

- **It has never run on a real day of founder work.** Everything here still rests
  on tests, adversarial review and simulated lifecycles. This is the single
  largest gap and no amount of test-writing closes it.
- **Simplicity is unchanged.** The measurement exists (10,407 tokens, per-section
  breakdown in the lazy-core design) and the work is not done.
- **Handovers are not transactional.** A lock plus a read-back is a real
  improvement and is not what the audit asked for. The follow-up shape is
  recorded in the code.
- **The adopt defect from the earlier audit is still open**: a refused adoption
  still writes a permanent handover block into STATE.md.

## The four Windows classes, kept because they are a class

Four failures tonight, all invisible on macOS and Linux, each a different cause:
repr doubling backslashes; an 8.3 short path versus its long form; MAX_PATH; and
locale-dependent decoding where the SHIPPED PARSER WAS RIGHT and the test was
wrong.

Two lessons worth more than the four fixes:

1. Four green platforms are not evidence when the wrong rule and the right rule
   agree on all four.
2. On a platform you cannot run, an assertion that reports only an exit code buys
   exactly one round of guessing per failure. Making one assertion carry git's own
   error text is what turned a guess into a diagnosis.
