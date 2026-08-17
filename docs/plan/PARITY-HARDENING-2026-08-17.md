# Hardening the six capabilities still below GitHub Actions

Status: CURRENT. This is a live design, not a record of one. Three of its six
items landed on 2026-08-17 (the credential sandbox, the Python 3.9 floor, and
receipt signing); the rest are open, and the Linux item is blocked on disk space
rather than on a decision. Mark this HISTORICAL when the open items close or the
design is superseded.

Founder instruction, 2026-08-17: for each capability where the local gate runner
is still below what Actions gave, design a hardening that reaches an honest pass;
find free and unlimited marketplace plugins that help; and make Actions optional,
used only when absolutely needed and with great care not to burn the 2,000 free
minutes. For BrotherMode and BrotherSBE both.

Architecture by Fable. Every claim below that names a file, a line, or a command
was checked against the machine, and the three checks worth repeating are marked
VERIFIED with what they printed.

## The state this is hardening

Seven of thirteen capabilities are at or above Actions after 2026-08-17. Six are
below. The parity ledger holds the full table:
https://claude.ai/code/artifact/a8363353-7872-4dcd-9d4a-8a33ac3cd325

## On marketplace plugins, answered honestly

There are none. The plugin catalog was searched for local CI runners, test
matrices across Python versions, sandbox isolation, git worktree testing, commit
signing, and supply chain checks. It returned zero results for all six.

This is reported as a finding rather than padded with near misses, because the
real answer is more useful: every one of these six gaps is closed with plain git,
the macOS system tools already installed, and about sixty lines of shell. A
plugin would add a dependency and an update surface to a problem the platform
already solves. The one capability that genuinely cannot be closed locally
(Linux) is not a plugin problem either; it is a compute problem, and Part B buys
it deliberately.

## PART A: the six

### 1. Clean checkout: run in a throwaway worktree
TARGET: the battery executes only the bytes of the commit under test.

MECHANISM: `git worktree add`, NOT `git archive`, and the reason is not
preference. An archive directory has no `.git`, so the post-run guard that
refuses to report when the run modified tracked files cannot run there at all.
That guard is `scripts/local-gates.sh` (BrotherModeUp lines 129 to 133, BrotherSBE
lines 246 to 250). Swapping to an archive would silently DELETE a check while
appearing to add isolation, which is the exact failure class this whole effort
exists to stop. A worktree keeps `git status` working, so the guard survives.

BrotherSBE additionally needs a live `.git`: its workflow checks out with
`fetch-depth: 0   # the approval gate reads commit trailers and signatures`, and
`tools/sbe_release_invariant.py --strict` diffs against origin/main.

Shape, both `scripts/local-gates.sh`, after the poison check:

    WT="${TMPDIR:-/tmp}/gates-wt-${SHA:0:12}"
    git worktree prune
    git worktree add --detach --force "$WT" "$SHA"
    trap 'git worktree remove --force "$WT" 2>/dev/null' EXIT

Run the battery from `$WT`; write the receipt into the real repository's
`evidence/gates/`; add `checkout: fresh worktree` to the receipt.

HAZARD, named: BrotherSBE carries roughly 24 stale prunable worktrees today, so
the `prune` and the `trap` are load-bearing rather than tidiness.

COST: 2 to 5 seconds per run, about 15 lines per script.

PROVEN BY: plant an untracked `x_poison.py`, run the gate, and assert
`[ ! -f "$WT/x_poison.py" ]` plus `grep "checkout: fresh worktree"` in the
receipt. The grep fails on the unhardened script.

### 2. Multiple operating systems: NOT buildable locally, named as a limit
TARGET, honest: continuous macOS coverage (already real, it is the machine the
runner runs on), Linux at release candidates only, Windows by written protocol.
Per-push coverage of three platforms is not the bar for a one-person estate.

MECHANISM: none exists tonight. VERIFIED: `command -v docker colima podman`
returns nothing for all three, and installing any of them needs the founder's
password, so no agent can do it unattended. The design stops there rather than
inventing a route.

KNOWN LIMIT, to be written verbatim into each repository's docs/KNOWN-LIMITS.md:

> Linux: NO automatic coverage. The battery is proven on macOS on every run.
> Linux is checked only by a deliberate, budgeted workflow_dispatch at release
> candidates. Between dispatches, a Linux-only breakage is undetected.

The Linux leg is BOUGHT from Part B's budget, not built.

### 3. The Python 3.9 floor: already possible, zero installs
TARGET: the 3.9 floor promised on the product's front page is tested on this
machine rather than only in a dormant workflow.

VERIFIED, and this is the unlock: `/usr/bin/python3 -V` prints `Python 3.9.6`
(Apple Command Line Tools) beside the `Python 3.13.14` on PATH. Both interpreters
are already here. Nothing to install, no password.

MECHANISM: a `--floor` flag on both runners that prepends a shim directory to the
PATH entry inside `GATE_ENV`:

    mkdir -p "$TMPDIR/py39" && ln -sf /usr/bin/python3 "$TMPDIR/py39/python3"

and records the floor interpreter in the receipt. The receipt's `python:` line
currently reports the outer shell's interpreter, so it must move inside the
pinned environment to stay true.

CADENCE mirrors the workflow's own founder decision, quoted from
brothersbe-gates.yml: the 3.9 floor is the BLOCKING leg because it is the promise
on the front page, the newest interpreter is informational. So: 3.13 every run,
floor leg at release candidates and on any dependency or syntax-surface change.

COST: doubles wall clock on floor runs (about +15 minutes BrotherSBE, +44
BrotherMode). About 10 lines.

CAVEAT, stated: 3.9.6 is Apple's build and slightly behind the latest 3.9.x. That
is acceptable floor semantics, and the proof below catches Apple removing it.

PROVEN BY: `/usr/bin/python3 -V | grep -q "Python 3.9"`, and after a floor run,
`grep "Python 3.9" evidence/gates/<sha12>.txt`. Both fail today.

### 4. Credential isolation: macOS seatbelt, no password needed
TARGET: code under test cannot read the founder's credentials or reach the
network, even while running as his user. Actions-style fork isolation is NOT
reachable without a container and is not claimed.

MECHANISM: wrap only the battery invocation in `sandbox-exec -f scripts/gates.sb`.
Profile: allow default, then `(deny network*)` and `(deny file-read*)` over
`~/.ssh`, `~/.config/gh`, `~/Library/Keychains`, and the Kay Vault. Allow-default
with a denylist rather than deny-default, because the batteries legitimately read
the toolchain broadly; the denied roots are exactly the assets the audit named.
The runner's own fetch and status POST stay OUTSIDE the sandbox.

KNOWN LIMIT: `sandbox-exec` is deprecated by Apple (still present and functional),
and a denylist is not a container: an unlisted path stays readable. This is
credential and exfiltration isolation, not fork parity. The standing rule holds:
read the diff before running any fork checkout.

PROVEN BY: under the profile, both
`sandbox-exec -f scripts/gates.sb cat ~/.ssh/<key>.pub` and
`sandbox-exec -f scripts/gates.sb /usr/bin/curl -m 5 https://example.com`
must exit nonzero. Both succeed today, which is the measured gap.

### 5. Identity binding: sign the receipt
DECISION: sign with `ssh-keygen -Y sign`. Reject git notes. Keep detection as the
second layer.

WHY: forging a green status needs only the gh token, whose scopes are `gist`,
`read:org`, `repo`, `user`, `workflow`. A signature demands a SECOND, different
credential that never leaves this machine. Git notes are another push-scoped ref,
forgeable by the same token: ceremony, not identity.

KEY: generate a dedicated `~/.ssh/id_ed25519_gates` rather than reusing the
Bitbucket push key, so rotating either does not break the other.

    ssh-keygen -Y sign -f ~/.ssh/id_ed25519_gates -n gates-receipt <receipt>
    ssh-keygen -Y verify -f scripts/allowed_signers -n gates-receipt ...

HONEST LIMIT: a malicious process running as this user can read the key and sign.
This defeats a leaked-token remote forger, not a compromised machine. Capability
4's sandbox is what keeps the code under test away from the key.

COST: milliseconds, one keygen, about 6 lines.

### 6. Concurrency: do NOT build
The serial cap is deliberate and load-bearing: BrotherMode's runner refuses when
`a battery is already running in this tree. One suite at a time`, because two
batteries in one tree produce false failures in both. Cross-repo parallelism
already exists free, since the two runners guard different trees.

MEASURED THE HARD WAY, 2026-08-17: this machine reached load average 243 with two
iOS simulators and a battery running. The founder's own rule is that measurements
above 187 are noise. Adding intra-repo parallelism to a machine that already
oversubscribes 8 cores would manufacture false failures, not speed.

COST of not building: BrotherMode verdict latency stays about 44 minutes.

### Build order
1 first (cheapest, feeds 4, kills the whole untracked-state class), then 5, then
3, then 4. NOT built: 6 by decision. 2 has no local build.

## PART B: Actions as a rationed resource

### The decision rule, for a non-engineer
A cloud run is warranted only when the doubt is specifically about LINUX and the
answer changes what ships. Three questions, all must be yes:

1. Is the question about the operating system, not the code?
2. Did the local gate already pass on this exact commit?
3. Is this a release candidate, a change to install or workflow or host-facing
   files, or a user-reported Linux failure?

Any no: no dispatch. Never to re-prove a local green. Never "just to be sure".

### The budget
Hard cap 200 minutes per month, 10 percent of the 2,000 free. Expected real use
under 100.

Per-dispatch estimates, UNVERIFIED until the first timed run: BrotherSBE gates,
two ubuntu legs, about 25 minutes. BrotherMode tests, two ubuntu legs, about 90
minutes. At cap that is roughly 8 BrotherSBE dispatches or 2 BrotherMode
dispatches per month. The first budgeted dispatch after the reset records actuals
and corrects this table.

THIS MONTH IS ALREADY SPENT. Nothing dispatches before the reset.

### Measurement
VERIFIED: the old endpoint is dead. `gh api users/<user>/settings/billing/actions`
returns HTTP 410, "This endpoint has been moved."

VERIFIED WORKING with the current token, no new scope:

    gh api "users/<user>/settings/billing/usage?year=2026&month=8"

It returns per-SKU `usageItems` per repository. Procedure: measure before,
dispatch, `gh run watch`, measure after, record the delta in a dispatch receipt
beside the gate receipts.

### The brake
Keep every existing block in `~/.claude/hooks/github_cost_wall.py`. Carve the
exception only inside its dispatch pattern:

- `gh workflow enable` stays blocked unconditionally.
- `gh workflow run` is allowed ONLY when a grant file `~/.claude/actions-grant.json`
  exists, is under 24 hours old, names the exact repo and workflow in the command,
  and a ledger shows month-to-date minutes under 200.
- The wrapper appends the ledger row and DELETES the grant: one grant, one run.
- `gh run rerun` stays blocked, so a failed cloud run costs a fresh deliberate
  grant rather than a reflex.
- Workflow authoring, billing and codespaces blocks: unchanged.

HONEST LIMIT, to be stated in the wall's own message: no hook can prove a human
wrote the grant. The grant converts an accidental dispatch into a deliberate
two-step act. Minting one without a founder decision breaks the 2026-08-16 law
exactly as editing the hook would.

PROVEN BY: extend `test_github_cost_wall.py` from 8 cases to 10. Grantless
`gh workflow run` still exits 2; granted-within-budget exits 0; granted-over-budget
exits 2. The suite must still print `0 failures`.

### Never to the cloud, at any budget
Client or private-project content in any form (names, paths, personas, figures).
Credentials or secrets as workflow env or in fixtures. Kay Vault content. Any
macOS or Windows job and any automatic trigger, which are law rather than budget.
And never a dispatch on a commit whose LOCAL gate has not already passed: the
cloud answers the Linux question only, and a cloud green never substitutes for the
local receipt as primary evidence.

## Files this design touches
- `scripts/local-gates.sh` in both repositories
- new `scripts/gates.sb` and `scripts/allowed_signers` in each
- `~/.claude/hooks/github_cost_wall.py`
- `~/SaveClaudeTokens/scripts/test_github_cost_wall.py`
- each repository's `docs/KNOWN-LIMITS.md`, for the Linux wording
