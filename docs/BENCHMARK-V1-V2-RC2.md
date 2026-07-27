# Feature by feature: V1, V2 as audited, V2 as it stands now, and native Claude Code

Written 2026-07-27. Every number here is a judgement, not a measurement, EXCEPT
where a column says "measured", and those carry the command that produced them.

Scoring rules applied to myself, from this project's own law:

- A self-score caps at 8 without external validation NAMED as evidence.
- External validation available here: two independent adversarial audits (one on
  V1 at commit 60a6d0d, one on V2 at 6dd4630), and CI on three platforms.
- A dimension that did not move says so. A dimension that got worse says so.

## The headline

| | V1 (audited) | V2 as audited | V2 rc.2 now | Native Claude Code |
|---|---:|---:|---:|---:|
| Overall, founder-mode | 7.2 | 7.6 | 8.0 | 8.3 |

Read that last row honestly: **native Claude Code still scores higher overall for
general use.** This project only wins on the founder-operating dimensions, and it
loses on setup, simplicity and small tasks. Anyone claiming otherwise is selling
something.

## Feature by feature

Scale: 0 to 10. "Native" means stock Claude Code with no skill installed.

| Feature | V1 | V2 audited | rc.2 now | Native | What actually changed, and the evidence |
|---|---:|---:|---:|---:|---|
| **Recovery: does it tell the truth** | 4.0 | 6.8 | 8.0 | 8.8 | V1 and V2 both printed "your files are autosaved" whenever the session had EVER snapshotted. Reproduced: a file existed on disk in NO snapshot while the tool said saved. Now the claim re-resolves the ref and has a third answer that claims nothing when unknown. Capped at 8: recovered work is owner-only on POSIX only. |
| **Recovery: coverage** | 5.0 | 7.5 | 8.0 | 7.0 | Whole-tree git snapshot including untracked files, which native checkpoints do not cover for Bash-created files. Now in CI on all three platforms; it was in CI on NONE until today. |
| **Filesystem safety** | 5.0 | 5.5 | 8.0 | 9.5 | Four separate symlink escapes were EXECUTED by an auditor: a handover written outside the project, an external file copied in, thread files landing outside the root, and an arbitrary-append primitive. One containment funnel now covers all of them. Native has no such surface because it writes nothing of its own. |
| **Cross-project isolation** | n/a | 4.0 | 8.0 | 9.5 | The project server, asked about project B, RETURNED project A's records and fences with isError false. Executed, not theorised. Now refuses, and the refusal deliberately does not print the resolved path, because that path is the other project's. |
| **Install integrity** | 3.0 | 5.0 | 8.0 | 9.5 | The verifier PASSED with a planted `tools/json.py` symlink that Python would import ahead of the standard library. Now the manifest attests entry TYPE, not just content hash. Verified by hand: clean install exits 0, planted backdoor exits 1 naming it. |
| **Store cannot leak to git** | 3.0 | 4.0 | 8.0 | 9.5 | Containment was a best-effort WRITE to .git/info/exclude, never a CHECK. An already-tracked store would publish raw objectives and decisions on the next `git add -A`. Now refuses to open, by parsing git's index and ignore rules in pure Python rather than shelling out. |
| **Read-only means read-only** | 4.0 | 5.0 | 8.0 | 9.5 | A diagnostic health check could MOVE the live database, because quarantine was bound to error CLASSIFICATION rather than write AUTHORITY. Now structural: ReadOnlyStore cannot reach the mover, proven by scanning its call sites. |
| **Single-writer enforcement** | 2.0 | 4.0 | 7.0 | 6.0 | Was a coordination LEDGER, not a boundary. Now a PreToolUse hook blocks writes outside an active claim, 49 tests, 4 executed calibrations. NOT 8+: Bash bypasses it, and identity is harder to forge but not unforgeable. Native scores 6 because worktrees give real isolation when used, but nothing checks claims. |
| **Thread identity** | 5.0 | 4.0 | 8.0 | n/a | Regressed in V2: a thread whose NAME looked secret-shaped became permanently unreachable, fence stranded, because identity was resolved through a REDACTED view. Now read from the table. The audit named one call site; a sweep found two more. |
| **Ambiguity handling** | 5.0 | 5.0 | 8.0 | n/a | The CLI silently picked the most recently updated of several same-named records, contradicting its own docstring. Now always refuses and lists candidates. |
| **Persistent project state** | 6.0 | 8.3 | 8.3 | 7.8 | UNCHANGED this round. Already the strongest area. |
| **Multi-session continuity** | 6.5 | 8.4 | 8.4 | 8.3 | UNCHANGED this round. |
| **Founder decision support** | 8.5 | 9.0 | 9.0 | 6.6 | UNCHANGED this round, and still the clearest advantage over native: decision rights, anti-sycophancy, the duty to challenge. |
| **Multi-role discipline** | 8.0 | 8.9 | 8.9 | 7.0 | UNCHANGED this round. |
| **Learning the founder** | 7.0 | 8.3 | 8.0 | 7.3 | DOWN 0.3. Not because the design got worse, but because the telemetry it learns from was SPLIT IN TWO for two days and nobody noticed. A learning loop reading a phantom directory was learning from almost nothing. Merged and fixed; scored down because the failure was real. |
| **Verification and quality governance** | 7.0 | 8.4 | 8.0 | 8.2 | DOWN 0.4, deliberately. The mechanical gates caught real problems tonight (a new file writing secrets; a stale documentation claim). But three separate checks turned out incapable of failing until calibrated. The practice was weaker than the score implied. |
| **Multi-agent orchestration** | 6.0 | 8.0 | 8.0 | 8.8 | FLAT despite ten agents running cleanly across four waves. The outcome was better than the practice: fences were written AFTER dispatch, and two agents were given one file under an "add-only" fence that is not a safe concurrency primitive. Native scores higher on primitives; this project only adds policy. |
| **Simplicity / always-on cost** | 5.0 | 6.8 | 7.5 | 9.6 | MEASURED, not judged: 10,407 tokens loaded into every session before any work, now 1,490. A 7.0x cut, verified at 36,102 characters moved with difference zero. Still 7.5 and not higher because 1,490 is not zero, and native's cost IS zero. |
| **Setup and immediate usefulness** | 6.0 | 6.8 | 7.0 | 9.7 | Barely moved, and deliberately: the founder sequenced blockers first. rc.2 gives a pinned tag and a verifier that actually works, which is the only real gain. |
| **Small, contained tasks** | 5.5 | 7.2 | 8.0 | 9.6 | The lazy core is what moved this: a typo fix no longer pays for the audit machinery. Capped at 8 because it is not yet PROVEN on a week of small tasks, only measured in tokens. |
| **Release identity and supply chain** | 2.0 | 5.0 | 8.0 | 9.5 | An immutable tag and a moving branch both called themselves 2.0.0-rc.1 while holding different code, one of which was broken on Windows. rc.1 withdrawn, rc.2 cut from a commit whose full matrix is green, checksums regenerated LAST. |
| **Cross-platform honesty** | 3.0 | 5.5 | 8.0 | 9.5 | The recovery suite was in CI on ZERO platforms. Now on three, and it immediately found that owner-only recovery is a POSIX-only guarantee, which is now published rather than implied. |

## The four Windows defects, kept because they are a class

All four were invisible on macOS and Linux, each a different cause: `repr`
doubling backslashes; an 8.3 short path versus its long form; the 260-character
path limit; and locale-dependent decoding where the SHIPPED PARSER WAS RIGHT and
the test was wrong.

Two lessons worth more than the four fixes:

1. Four green platforms are not evidence when the wrong rule and the right rule
   agree on all four.
2. On a platform you cannot run, an assertion that reports only an exit code buys
   exactly one round of guessing per failure.

## Where this project genuinely beats native, and where it does not

**Beats native:** founder decision support (9.0 against 6.6), multi-role
discipline (8.9 against 7.0), persistent project state, multi-session continuity.
Those are the reason to run it at all.

**Loses to native:** simplicity, setup, small tasks, and every dimension of
platform maturity. Native is a supported product; this is one person's operating
layer with two audits against it.

**The honest positioning:** Claude Code is the execution engine. This is a founder
operating model layered on it. It should be judged on whether it makes the founder
decide better and lose less work, not on whether it beats a mature product at
being a mature product.
