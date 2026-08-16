# Patches produced overnight and NOT yet merged, 2026-08-16

## sentinel-orphans-UNMERGED.patch

WHAT IT CLOSES. Four sentinel tables hold founder prose stored deliberately
unscrubbed. They carry a project id with no foreign key, and the purge refuses
to run once the project row is gone. So a sentinel row naming a deleted
project is unreachable by every erasure command that ships: unscrubbed
personal text that nothing can delete, in a product whose argument is that it
tells you the truth about what it erased.

WHAT IT ADDS.
- A read-only report of orphaned rows, per table and project id. It selects
  only the project id and a count, so it can never print the prose itself.
  Printing it to a terminal or a transcript would be the same leak in a new
  place.
- A guarded erasure. Exactly one of a named project or an explicit
  all-orphans flag. A live project refuses and points at the ordinary purge.
  A confirmation token must match. A dry run performs the real deletes and
  rolls them back. Every delete additionally carries a guard restricting it
  to project ids absent from the projects table, as defense in depth. One
  attribution row is written per project actually purged.

EVIDENCE. 13 tests, including that the report never contains the seeded prose
and that a seeded non-orphan survives the sweep. Proven by removal: disabling
the confirmation check turns two tests red, and it was restored and re-verified
green. A command line smoke test ran against a throwaway store only.

OWED, and named rather than skipped: `python3 tools/test_bm_project.py` in
full. It was held back deliberately because a full gate was running on the
shared tree at the time and this repository runs its suites serially on
purpose. A targeted run of the no-SQL guard class passed 3 of 3.

APPLY WITH, from the repository root, once the tree is clean and no gate is
running:

    git apply <this file>
    python3 -m unittest tools.test_bm_store.TestSentinelOrphansFindAndPurge
    python3 tools/test_bm_project.py

WHY IT IS HERE RATHER THAN COMMITTED. It was finished while a full gate was
measuring the tree. Folding into a tree under measurement voids the run, which
this repository already lost forty minutes to once tonight. Held on purpose,
not forgotten.

## WHAT THIS PATCH STILL NEEDS BEFORE IT CAN LAND, learned the hard way

It WAS committed (3d63df5) and then REVERTED (e35bb57), because the full
battery came back red on three suites. Not one of them was about the feature
being wrong. All three were registries the two new command line verbs must
join, which is this repository's PO-6 rule, and the same rule this session
had forwarded to another agent an hour earlier before walking into it.

The three, with the exact failures:

1. tools/bm_effects.py REGISTRY, under the "bm_project.py" key.
   test_bm_effects.py: undeclared commands, "sentinel-orphans" and
   "purge-sentinel-orphans". The intended entries, following how "purge"
   itself is classed there:
       "sentinel-orphans": PURE_READ
       "purge-sentinel-orphans": DESTRUCTIVE_EXTERNAL_ACTION
   The report only ever selects a project id and a count, never the prose, so
   pure read is correct for it.
   BLOCKED at the time by fence F4 over tools/bm_effects.py. The store held no
   such claim.

2. The founder-facing refusal rewrites in tools/bm_visual.py.
   test_bm_visual.py: "reason code(s) with no founder facing rewrite:
   ['ambiguous-target', 'no-target', 'not-orphan']". Every reason code a
   module can emit needs plain-language text, or a non-engineer meets a raw
   code. bad-confirmation and not-found already have entries. This test is
   the best of the three: it caught a real beginner-experience defect in new
   work rather than a bookkeeping miss.

3. The runtime adapters. test_bm_runtimes.py: a tool that grows a command
   makes the adapters stale. Regenerate with:
       python3 tools/bm_runtimes.py emit

DO ALL THREE IN THE SAME CHANGE AS THE PATCH. Landing the patch without them
turns main red, which is exactly what happened.
