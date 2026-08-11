# Overnight work and the long-term horizon, ordered by what it takes to ship V3

Written 2026-08-11 night, at commit d2dd5f5 on main, tree clean.

This file answers one question: what has to happen, in what order, for V3
Final to be a version your team can actually install, and what of that can run
while you sleep. Everything else is subordinate to that ordering.

---

## Part 1: where it actually stands

Content work for the release is DONE. All six tasks across the plan's two
lanes, plus the one added tonight:

| Task | State | Proof |
|---|---|---|
| A1 README repositioning | done | docs suite exit 0 |
| A2 six-name public surface | done | docs suite exit 0, test_bm exit 0 |
| A3 SECURITY.md | done | docs suite exit 0 |
| A4 combined-use guide (added tonight) | done | docs suite exit 0 |
| B1 purge dry-run | done | test_bm_project 47 tests OK |
| B2 data-locations check | done | test_bm_consent 44 tests OK |
| B3 verify skill | BLOCKED on your ruling | see Part 4 |

The last full battery was ALL GREEN at 5b7c52e (3020 tests, 32 suites, 886.9s,
exit 0). Four commits have landed since, three carrying code or documentation.
**That battery verdict no longer covers HEAD.** It must run again before
anything is tagged, and that is step 2 below.

What has NOT happened: the version is still 3.1.0, nothing is tagged, nothing
is released, and no install of the new version has been rehearsed.

---

## Part 2: the deployment path, in strict order

Each step names its command and the gate that has to pass before the next one
starts. Steps 1 to 3 are mechanical. Step 4 is yours by law.

### Step 1. Version and changelog (G3), 15 to 30 minutes

Files: `VERSION`, `CHANGELOG.md`.

Set `VERSION` to `3.2.0`. Add a changelog entry in the same shape as the 3.1.0
entry. **Write it against what actually shipped**, which is not what the plan
predicted: the verify skill is NOT in this release, and the changelog must not
list it. What it lists is the repositioning, the six-name public surface with
two names marked unshipped, the purge dry-run, the data-locations check, and
the combined-use guide.

Gate: `cat VERSION` reads `3.2.0`, and no changelog line names a capability
that does not exist.

### Step 2. The full battery (G1), 10 to 20 minutes, unattended-safe

```
rm -f "$TMPDIR/gate.exit"
nohup bash -c 'BROTHERMODE_SESSION_CAP=99 python3 tools/test_all.py > "$TMPDIR/gate.log" 2>&1; echo $? > "$TMPDIR/gate.exit"' > /dev/null 2>&1 &
for i in $(seq 1 80); do pgrep -f tools/test_all.py > /dev/null || break; sleep 10; done
cat "$TMPDIR/gate.log"; cat "$TMPDIR/gate.exit"
```

Two rules that cost real time tonight. Clear the sentinel first, or you will
read a previous session's verdict as your own. And write NO tracked file while
it runs, not even a progress page, or it refuses to report green even when all
32 suites pass.

Gate: the log's last line reads `ALL GREEN` and the exit file reads `0`. Note
the commit hash; the verdict binds to that hash and nothing else.

### Step 3. Manifest and install trust (G2), 5 minutes

```
git add -A
sh scripts/checksums.sh CHECKSUMS.sha256
python3 scripts/doctor.py
bash scripts/verify-install.sh
```

Order matters: `git add` first, because the manifest hashes tracked files
only, so a new file added afterwards is silently omitted.

Gate: doctor's checksums check reads PASS, and verify-install reads PASSED
with 0 extra.

### Step 4. Tag and release (G4). YOURS. Not startable by an agent.

```
git tag -a v3.2.0 -m "V3 Final: repositioning, six-command public surface, purge dry-run, data locations check"
git push origin v3.2.0
gh release create v3.2.0 --title "BrotherMode v3.2.0, V3 Final" --notes-file <(sed -n '/## 3.2.0/,/## 3.1.0/p' CHANGELOG.md | sed '$d')
```

Gate: `gh release view v3.2.0` shows it published, and the release's tag
matches `git rev-parse v3.2.0`.

### Step 5. Rehearse the install your team will actually run, 20 to 40 minutes

Everything above proves a repository. None of it proves an install, and those
are different things: the tests run from a checkout, while your team will run
a plugin install and then type into Claude Code.

The plugin path is the one proven end to end the most times, and
`scripts/release-smoke-install.sh` exercises it inside a throwaway
configuration. Run it after the tag exists, not before.

Gate: a fresh install reports the new version, doctor passes on it, and the
six-name surface in its README matches what that install actually offers.

**Why this step is here rather than optional, stated from evidence rather than
from a hunch.** Three first-contact failures were hit by running the products
tonight, and none of them would show up in a test suite: `brothermode` is not
on PATH at all, which reads as a broken install; the sibling's released build
does not carry the command its own card names first, so the first thing a data
engineer types errors out; and creating a work record leaves the health check
red on a user's first substantial task. Whether an install rehearsal catches
this class is NOT established, and this project's own README says plainly that
no first run by a person who has never used it has ever been measured. The
honest claim is narrower than "this decides adoption": there is a real gap
between what the suites cover and what a new person meets, three examples of
it turned up in one evening, and this step is the cheapest probe of that gap
available.

**KNOWN RISK, from this repository's own records: the live installed copy is
older than the store schema it would have to read.** If that is still true
after this release, a team member installing today gets a copy that cannot
read a current project. Verify it explicitly during this step rather than
assuming the tag fixed it.

---

## Part 3: what can safely run overnight, and what cannot

**Before any unattended stretch, these need your hand and nothing else can
supply them.** Enumerated now rather than discovered at hour six:

1. The tag and the GitHub release (step 4). A hard founder gate.
2. Enabling GitHub private vulnerability reporting. A settings click. SECURITY.md
   now names it as an outstanding action rather than claiming it is done.
3. The two rulings in Part 4, both of which block work that is otherwise
   finished.

**Safe to run unattended**, all mechanical with deterministic checks: steps 1
to 3 above; the booklet update under `docs/book/`, which currently ships one
release stale on the command surface; and a documentation link sweep.

**Never unattended:** step 4, anything touching the store schema, and any
first-time install rehearsal on a machine you care about.

If you do start an unattended run, the standing conditions apply and are not
optional: the relay brake with its depth cap and deadline, the overnight
watchdog, and the spend guard, all three active, cheap model tiers only, and a
hard stop by 07:00 JST.

---

## Part 4: the two rulings that block ready work

**Ruling 1, B3 and the canonical skill count.** The verify skill is written and
its checks passed, and it is backed out. Ruling B5 of
`docs/decisions/V3-FREEZE-2026-08-07.md` pins the public surface at nine
canonical skills; giving verify its own folder makes ten, which a pinned test
catches. Six files carry that count, including your brand identity contract.

Two options. Amend the ruling to ten and name verify in it, which touches a
ratified decision and a founder-owned brand document. Or keep verify as a
routing name inside the guided skill with no folder of its own, which keeps
the count at nine and needs no amendment. **The second is cheaper and is the
recommendation.** Either way it is your call, not an implementer's.

**Ruling 2, the external security review.** Your product direction files the
small technical team as a later persona, unlocked after four things. Three
shipped tonight. The external review has not happened and is not something
this repository can produce. SECURITY.md now states its absence in the open.
The question is whether your own team counts as the internal case where that
bar does not apply, and that is a judgement only you can make.

---

## Part 5: the long-term horizon, with its deployment implications

Ordered by what each tranche demands of a release, since that is what tends to
be underestimated.

**R1, the week after. One record, zero-tax adoption, memory designed.**
The change record becomes the atomic object; adopting costs a team nothing;
the memory architecture is designed and ratified but not built. Deployment
implication: R1 is the first tranche whose exit gate is a person rather than a
test, because it requires a second person to complete a governed change
without the author's help. Budget for that.

**R2, the month. Toolkit broker, memory built, first connectors.**
Deployment implication: this is where the release stops being one repository.
Connectors are separately versioned surfaces with their own auth failure
modes, and the toolkit broker introduces trust tiers and quarantine. The
release process in Part 2 stops being sufficient at R2 and needs a
per-connector gate of its own.

**R3, the quarter. Enterprise fabric.**
Multi-repository records, organization policy packs, a portfolio view. Entered
only after R2's exit checklist passes. Deployment implication: the first
tranche that needs a migration story for existing records, which is the most
expensive single thing in this horizon and the reason it is deliberately not
planned in loop detail yet.

**The three defects found tonight** sit across this horizon and each has a
natural home. The sibling's missing `review-route` belongs to that project's
own release, not this one. The provisional record leaving the health check red
is a small fix and belongs in R1, because it hits a new user's first
substantial task. The fence registry problem, where two hooks read one file
and disagree about what is enforceable, belongs in R1 as well and is the
largest of the three.

---

## Part 6: if you read only one page of this

Do steps 1 to 3 tonight or first thing, in that order, and stop at step 4
because it is yours. Then do step 5, because the gap between what the suites
cover and what a new person meets produced three real failures in one evening.
Answer the two rulings in Part 4 whenever you have five minutes; both are
blocking work that is otherwise finished.
