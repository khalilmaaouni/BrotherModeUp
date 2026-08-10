# What to do next, in order, and why that order

Status: CURRENT as of 2026-08-10 evening. No em or en dashes.

The order matters more than the list. Each step says why it comes where it does,
because a step done out of order here costs a gate run, and a gate run is about
nine minutes.

---

## 0. Before anything: re-arm the watchdog and take the ground map

WHY FIRST: the watchdog died with the session that armed it. Nothing on disk
enforces it. If you skip this you are working unwatched, which is the shape of
the 8 August incident.

```
git -C ~/Documents/BrotherModeUp status --short
git -C ~/Documents/BrotherModeUp rev-parse --short HEAD @{u}
python3 tools/bm_progress_check.py status
```

Do NOT trust any commit number written in these documents. They were true when
written and the act of committing them made them stale. Run the command.

Re-arm: a read-only audit cron on off-minutes, and a foreign-work monitor that
tests whether `origin/main` holds commits THIS CHECKOUT DOES NOT HAVE
(`git merge-base --is-ancestor origin/main HEAD`), not merely whether origin
moved. The first version of that monitor fired on its own author's pushes.

---

## 1. Collect the two agents' work and VERIFY IT YOURSELF

WHY SECOND: it is the only thing blocking a green tree, and everything after it
needs a green tree.

Two agents were in flight at handover:
- routing `bm_docs.py tier`, `bm_project.py alert list` and
  `bm_threads.py recommend` through `ReadOnlyStore`, plus a `--help` gate on
  `bm_threads.py dashboard`
- the security-verb drift check in `tools/test_bm_docs.py`

VERIFY BY RUNNING, NOT BY READING. This session caught agent claims that did not
survive checking and one that did. The commands:
```
python3 tools/test_bm_effects.py      # target: OK, without weakening the test
python3 tools/test_bm_docs.py         # target: OK
```

If the effects test is still red, READ THE FAILURE. Each one names a real
defect. Do not make it pass by changing the test.

---

## 2. Apply the deltas the agents name outside their fences

WHY: agents are fenced to their own files on purpose, so anything they need
elsewhere comes back as a REPORT. If you skip this the gate fails for a reason
that looks unrelated.

Most likely `tools/write_sites.json` counts. Read the write sites before writing
a number; the gate exists so a human looks, not so a number matches.

---

## 3. Register the new suite in FOUR places, or the repo refuses it

WHY: `test_all.py` refuses a test file it does not know about, and three other
inventories refuse an unregistered tool. All four fail separately and each costs
a run to discover.

1. `SUITES` in `tools/test_all.py`. NO APOSTROPHE anywhere in that comment: the
   fact loader parses the tuple quote to quote, and an apostrophe made it read a
   bare `s` as a suite name tonight.
2. A step in `.github/workflows/tests.yml`.
3. `py-modules` in `pyproject.toml`.
4. `tools/write_sites.json`.

---

## 4. Regenerate the checksum manifest LAST

WHY LAST: it hashes TRACKED files, so a new file that has not been `git add`ed
is silently omitted, and any edit after regeneration invalidates it.

```
git add -A
sh scripts/checksums.sh CHECKSUMS.sha256
sh scripts/verify-install.sh          # target: PASSED, nothing missing or extra
```

NEVER `sh scripts/checksums.sh > CHECKSUMS.sha256`. That hashes the file while
writing it and produces a manifest that fails against itself.

---

## 5. Commit, then run the FULL gate on the committed tree

WHY IN THAT ORDER: `test_all.py` refuses to report green on a dirty checkout,
because a suite that writes into the tree invalidates the manifest. So commit
first, then gate.

```
BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py
```

The cap override raises the limit for the TEST PROCESS so the liveness tests can
see headroom. It does not touch the machine-wide cap that governs session
spawning.

THIS STEP IS THE ONE THAT MATTERS. Until it passes, Loops 2 and 5 are not
closed, whatever their individual suites say. A suite passing is not a loop
closing.

Afterwards, re-check that HEAD did not move: a verdict belongs to one commit.

---

## 6. Loop 4's last item, if the agent did not finish it

The security-verb drift check: a security verb (refuses, prevents, blocks,
guarantees, enforces) in a shipped page with no test reference nearby should
fail the docs suite.

An honest "not ready" is an acceptable outcome. A check with false positives
gets deleted by the first person it annoys, so if it cannot be calibrated
without a long exclusion list, report that rather than shipping it.

---

## 7. Loop 6, the Codex cross-family audit

WHY BEFORE THE TAG: it is the only review by a different model family, and it
has already found what three same-family reviews missed, including a live
fail-open.

```
codex exec "reply with exactly: CODEX_ALIVE"     # confirm it is alive first
codex --version                                  # record it
```

Run it READ-ONLY against the merged tree. Save the output VERBATIM: a findings
list rewritten by the party being audited is not an independent finding.

Then triage every finding into FIXED, PUBLISHED as a known limit, or OPEN with a
reason. A FIXED row cites a file read fresh, never a commit message alone.

FOUNDER DECISION D8, confirmed twice: an unresolved CRITICAL or HIGH HOLDS THE
TAG, even if that means tagging tomorrow.

---

## 8. Loop 7, the tag. FOUNDER GATE.

Not cut without an explicit yes from Khalil in the moment. A tag is permanent
and this project has already withdrawn one release for publishing a claim it
could not support.

Order inside the step: regenerate the manifest, set the version in all three
places (`VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`),
update the changelog from real commits, run the full gate on the exact commit to
be tagged, confirm CI agrees on THAT SAME commit, then ask.

---

## After the tag: the control dashboard

Approved and specced, build scheduled after the tag by founder decision. Seven
steps, each naming its files and its done-check, in
`04-plans/2026-08-10-project-control-dashboard-design.md` and section 6 of the
handover.

The finding that shapes it: the dashboard ALREADY EXISTS as a generator, so the
work is a convergence and the hand-kept page gets deleted rather than extended.

---

## The one thing worth doing that nobody owns

A sweep for fences whose owning session is dead. Five instances blocked writers
today, each cleared by hand, and the detection is trivial. It is not in any loop
and has no owner. It would take under an hour and would have saved this session
several.
