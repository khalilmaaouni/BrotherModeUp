Status: CURRENT.

# Next session: the plan, the process, and the checklist

Written 2026-08-16 at the founder's order, after a long session that
delivered a great deal and also ran three gates that looked stalled. The
point of this page is that the next session moves in small proven steps
instead of one long flow that fails whole.

## Read this first, in one minute

The repository is healthy and everything finished is on GitHub. What is
NOT finished is listed here with a checkbox each. The single most
important thing to know: the full test gate takes 13 to 25 minutes on
this machine and it looks like nothing is happening while it runs,
because of a real defect written up as SBE2. It is not stalled. Never
kill it before the wall clock says 25 minutes.

## The process for the next session, and it is different on purpose

1. ONE step at a time. Take a single checklist item, finish it, prove
   it, commit it, then take the next. Do not open two lanes.
2. NEVER edit the tree while a gate runs. This session broke that twice
   and both times the gate refused with a dirty-tree message that reads
   like a test failure and is not one. Commit first, then gate.
3. When a gate looks stalled, read tools/test_all.py's own output file
   rather than killing it: the log shows which suite is running.
4. Every claim of done quotes a command run AFTER the last edit.
5. Anything that cannot be finished gets written into the pack at the
   exact step it stopped, never left silently.

## Checklist A: install and test, what remains

- [ ] A1. Run the full gate once, undisturbed, and record the wall time
      and verdict. Command: `BROTHERMODE_SESSION_CAP=99 python3
      tools/test_all.py`. Expect 13 to 25 minutes. If the install suite
      reports 0 tests again, that is SBE2 and not a regression.
- [ ] A2. Fix SBE2, the silence-budget defect, because it is what makes
      the gate look stalled. The root cause is proven and written in the
      queue item: the runner reads whole lines while unittest writes
      dots with no newlines. Two candidate fixes are named there. This
      one item removes the worst part of the developer experience.
- [ ] A3. Verify the two erasure defects, SBE9 and SBE10, are still
      reproducible, then fix them test-first. These are the ones where a
      founder asking to erase a project gets a crash, and where raw
      founder prose survives a purge that claims to have erased
      everything. NOTE: tools/test_bm_store.py sits inside a live fence
      of another session; open or adopt a fence first, the hook prints
      the exact instructions.
- [ ] A4. Fix SBE14, the redaction switch, because every other privacy
      protection leans on that funnel.
- [ ] A5. Close SBE1, the install-boundary identity, by stamping the
      commit into the installed tree and teaching doctor to compare.
      Until this lands, a green gate proves the repository, not the code
      that actually runs the hooks.
- [ ] A6. Only then, the cold install with the two testers, using
      docs/team/TESTER-PACK.md, which was adversarially reviewed and
      corrected this session. File their transcripts under
      docs/evidence/tester-pack/.
- [ ] A7. Bitbucket certification, once the founder creates the mirror:
      push, run both install commands against it, quote one green
      Pipelines run, close the UNVERIFIED labels in docs/BITBUCKET.md.

## Checklist B: the backlog, already filed and prioritised

All eighteen findings from the three BrotherSBE reviewers are in
docs/plan/QUEUE.json as SBE1 to SBE18, and the readable version with
the reasoning is docs/plan/PROBLEMS-2026-08-16.md. Work them in
priority order, one at a time, after checklist A.

## Checklist C: the planning work the founder asked for

- [ ] C1. Fold the two vision documents in docs/vision/ into ONE
      long-range plan amendment, with each mechanism naming its owner:
      BrotherMode or BrotherSBE, never both. Start from
      docs/plan/PARITY-READ-2026-08-15.md, which already names the three
      integration moves.
- [ ] C2. Take the ownership decision SBE-side item O23 names: one fence
      owner across the two products.
- [ ] C3. Ratify through the founder's question windows before building.

## What is already done, so nobody redoes it

Released v3.3.0. Bitbucket support written with executed proof. The
competitor comparison and the finalization roadmap. The weekend
emergency plan. The adopter review adapted into BrotherMode scope. Five
Toolkit items (TK1 to TK4 plus TK10 and TK11). The idle control on
session start. The tester pack hardened. The two-host law and the
narrowed target in PRODUCT-DIRECTION.md. The delivery artifact mapping
the team's feedback to what shipped. All pushed.

## The one number that still matters most

External installs: zero. Every item above is in service of moving that,
and the roadmap says so in its own success section. A green gate is not
the goal; someone else's machine running this successfully is.
