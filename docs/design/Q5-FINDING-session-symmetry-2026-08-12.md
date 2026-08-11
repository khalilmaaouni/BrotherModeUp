# Q5 finding: claim and park now disagree about session identity

Status: CURRENT

Q5 of `docs/plan/REPLAN-2026-08-12.md`. **Not fixed. This records a defect I
introduced tonight and then chose not to patch, with the reason.**

---

## The defect

The fence identity fix (commit `9346f93`) made `claim` convert a
harness-shaped session id into the label the write hook compares against. It
did **not** make the transition commands (`park`, `resume`, `complete`,
`adopt`, `checkpoint`) do the same.

So the tool became inconsistent with itself within an hour of that fix
landing.

## Reproduction, run 2026-08-12

```
python3 tools/bm_store.py claim q5-consistency-probe --lifetime ephemeral \
  --session 31456097-4efb-4470-aa61-5ff5e8b9afa7 ...
  claimed 'q5-consistency-probe' as lifecycle 41f75c7c... (version 1,
  session bm1-19d165ecdcbfb8ada77a15d6)
```

Note the stored session is the derived label, which is the fix working.
Then, with the **identical** session string:

```
python3 tools/bm_store.py park 41f75c7c... --version 1 \
  --session 31456097-4efb-4470-aa61-5ff5e8b9afa7
  refused (not-owner): lifecycle 41f75c7c... is ACTIVE under a different
  session; only that session may move it to 'parked'
```

**The same string that successfully claimed the fence cannot park it.** Before
tonight's fix both failed; now one works and one does not, which is arguably a
worse state to be in because it looks like it should work.

## Why it is not fixed tonight

I attempted it and reverted. The attempt inserted the same normalisation into
`_cmd_transition`, and it silently did nothing, because `root` is not yet in
scope at that point in the function and `_normalize_session_for_fence` catches
exceptions and returns its input unchanged. That exception-swallowing is
correct behaviour for its stated purpose (never take a command down over a
derivation) and it is exactly what made a broken edit look like a working one.

Three reasons to stop rather than push on: a second session was live in the
same repository; this is the transactional core, where a half-applied change
is the worst possible artefact; and the reverted state is the one an ALL GREEN
battery actually proved.

**Verified after the revert:** `python3 tools/test_bm_store.py`, `Ran 1029
tests`, `OK`. `tools/bm_store.py` shows no modification against the pushed
tree.

## The fix, for whoever takes it

1. Resolve `root` in `_cmd_transition` **before** normalising, or pass the
   already-resolved root in. Read the function's opening lines first; do not
   assume `root` is available where `claim` has it.
2. Apply the same conversion in every command that takes `--session` and
   compares it against a stored owner. One shared call site, not five copies.
3. **Add a test that claims and then parks with the same string.** No such
   test exists, which is why one hour of inconsistency shipped unnoticed. That
   test is the actual deliverable here; the code change is the easy half.
4. Consider whether `_normalize_session_for_fence` should distinguish "the
   derivation is unavailable" from "the derivation blew up". Today both are
   silent, and that silence hid this.

## The wider lesson, worth more than the fix

A conversion added at one entry point is a contract change for every entry
point that compares against what it stored. I changed what gets written
without checking what reads it, in a module whose own documentation says it is
the one place ownership is decided.

The repository already has a rule for exactly this, PO-6: before adding to any
registry, open the file that READS that registry first. The same rule applies
to a value's shape, not just to a registry's entries, and that generalisation
is the amendment this finding proposes.
