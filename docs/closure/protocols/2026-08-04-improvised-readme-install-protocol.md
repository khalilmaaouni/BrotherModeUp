# Improvised README install observation protocol, 2026-08-04

Status: CURRENT

This is a protocol, not a result. It defines how to run an unaided install
observation and how to record it. As of this writing, the observation
described here has never been run under controlled conditions: no run record
exists yet under `docs/evidence/` that follows the discipline below. This
document keeps saying so until a numbered record file sits next to it.

(A separate, earlier document, `docs/closure/reports/2026-08-04-P-3b-improvised-install.md`,
records a different exercise: a probe that was handed the README and the
documented install steps and asked to follow them. That is not this protocol.
The value of what follows is specifically that the probe is given no
documented route at all and has to find or invent one, so its choices are the
finding.)

## What the probe agent is given, and nothing else

- The repository URL and only that: `https://github.com/khalilmaaouni/BrotherModeUp`.
  This is confirmed as the `repository` and `homepage` field of
  `.claude-plugin/plugin.json` and as `REPO_URL` in `tools/bm_project_facts.py`.
- A throwaway HOME that contains no prior Claude configuration, with three
  environment variables pinned inside it before the probe starts, exactly as
  in the environment block below.
- One sentence of task: install this and get it working.

Explicitly NOT given, in these words, because the whole value of the
observation is that the probe chooses rather than follows instructions handed
to it:

- the documented install command, in any form
- the pinned tag
- the marketplace name
- the plugin name
- the README text, pasted into the prompt or otherwise
- the existence of `scripts/install.py`
- the existence of `scripts/verify-install.sh`
- any hint that more than one install route exists

A probe that is told which route to take is re-running the automated test by
hand, not observing what an unaided reader does.

## The environment pinning block

Reproduce this for every run, before the probe starts, and pass it to every
process the probe spawns without exception:

    tmp = a fresh throwaway directory, created for this run only
    fake_home = tmp/home
    env = {
        "PATH": <the ambient PATH>,
        "HOME": fake_home,
        "BROTHERMODE_VAULT": tmp/vault,
        "BROTHERSBE_VAULT": tmp/vault,
    }

This mirrors `tools/test_bm_plugin_install.py` and
`tools/test_bm_packaging_install.py`, both of which carry the same incident
note: `tools/bm_ledger.py` resolves its storage as
`os.environ.get("BROTHERMODE_VAULT", "~/BrotherModeVault")`, so the
environment variable wins over HOME whenever the invoking shell has it
exported, which it has on any machine that has ever run this project's own
tooling. HOME alone does not isolate the vault; a HOME-only override was
reproduced writing a live row into a real, non-throwaway vault. The pin must
never point at `/Users/khalil.maaouni/Documents/Kay Vault` or any other real
vault, under any circumstance.

## What must be recorded, per run

The record is a file at
`docs/evidence/YYYY-MM-DD-improvised-readme-install-run-N.md`, one file per
run. It carries all seven of these:

1. **Every command run, in order**, with its exit code and the first line of
   its output. Including the failed ones, including the ones the probe
   retried, and including anything it ran to look around before installing.
   Order is part of the finding: a probe that read the README before running
   anything is a different result from one that guessed.
2. **Every file written under the throwaway HOME.** Because the HOME starts
   empty, the after state IS the answer: record a full recursive listing
   with sizes. Also record anything written outside that HOME, which is a
   defect if it happens and must be reported as one, not smoothed over.
3. **Every hook registered, from all three observation points**, because
   they can disagree: `$HOME/.claude/settings.json` (what the clone
   installer writes), the `hooks/hooks.json` inside the installed plugin
   copy if a plugin route was taken, and the `Hooks (N)` line of
   `claude plugin details`. If the probe ended up with BOTH routes wired,
   say so loudly: that is the double-wiring hazard already recorded in
   `docs/evidence/2026-07-31-first-plugin-install.md` and in
   `docs/KNOWN-LIMITS.md`, and every hook then runs twice.
4. **Whether it chose the pinned tag or the moving branch.** Both exist:
   `git tag -l` resolves `v2.0.0-rc.13`, and `main` is the default branch.
   The answer is read from the actual command the probe ran, not inferred: a
   `git clone --branch v2.0.0-rc.13` is the pinned choice, a
   `git clone --branch main` or a bare `git clone` is the moving choice, and
   a `plugin marketplace add khalilmaaouni/BrotherModeUp` is a third answer,
   namely the moving default branch reached through the marketplace. Record
   which, and record whether the probe was even aware there was a choice.
5. **The verify-install result inside the installed copy**: run
   `scripts/verify-install.sh` from inside whatever the probe installed, and
   record its exit code and its counts of OK, MISSING, EXTRA and MISMATCH
   verbatim. A route that produces EXTRA files is a route whose own
   integrity check fails on first use, and that is precisely the finding
   this whole protocol is hunting.
6. **Every question the probe asked, and every point where it stopped and
   could not proceed.** Time or turn count to the first working
   `/brotherme` or `/brothermode` invocation.
7. **A one-line verdict**: did an unaided reader end up with a working,
   verifiable install, yes or no, and by which route.

## Run discipline

Each run gets its own throwaway HOME and its own record file. Runs are never
merged into one document, and a failed run is never deleted: a probe that
gave up is the most informative result available, not a blemish to hide.

This document stays saying "the observation has never been run under
controlled conditions" until a numbered record exists under
`docs/evidence/` that follows this protocol. When the first such record
lands, this line should be updated to point at it rather than silently left
to contradict the record sitting next to it.
