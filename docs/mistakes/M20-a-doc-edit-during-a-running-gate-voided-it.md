Status: HISTORICAL record of one incident, 2026-08-11. It is the ledger's own
rule broken by the session that had just quoted it. No em or en dashes.

# M20: a documentation edit during a running gate voided that gate

## What happened

The full gate was launched on the committed tree at 3efb616. While it ran,
the same session edited docs/plan/COMMAND-CENTER.html, a TRACKED file, to
refresh the board. tools/test_all.py ends with _worktree_dirt() and, on any
modified tracked path, appends a synthetic "clean-checkout" failure and
prints "REFUSING to report green", whatever every suite did. The run was
therefore void as a verdict before it finished, and its ~9 minutes bought
per-suite information rather than a bindable result.

## Why the existing rule did not stop it

references/mistakes.md already carries "A GATE RUN ON A MOVING TREE IS NOT A
RESULT", and this session had quoted that class in its own handover reading
two hours earlier. The rule was read as being about CODE edits by SUITES.
The dirt check cannot make that distinction and should not: it asks one
question, whether any tracked path changed during the run, because a dirty
tree is what invalidates CHECKSUMS.sha256 and makes verify-install tell a
user their install may be tampered with.

The board file felt exempt because it is documentation, is not executed by
any test, and refreshing it is the very ritual the progress-page law asks
for at every closed loop. Two standing obligations pointed in opposite
directions, and the one with no machine behind it lost.

## What is true, therefore

- A gate holds a lock on the WHOLE tracked tree for its whole run, not on
  the code under test.
- "It is only a document" is not an exemption. Tracked is tracked.
- The board refresh and the gate cannot overlap. One of them waits.

## The rule

While a gate is running, edit nothing tracked. Board refreshes, ledger
updates and handover writes either happen BEFORE the gate starts, on the
tree that is about to be measured, or AFTER its sentinel lands. Where a
refresh cannot wait, write it outside the tree and copy it in afterwards.
A gate whose run overlapped a tracked edit is re-run, never explained away.

## What would flip it

A gate that distinguished suite-authored writes from operator-authored ones
(for example by snapshotting tracked state at start and attributing changes
by process) could allow documentation edits mid-run. Nothing does that
today, and the honest cost of the rule is one re-run, so the simpler rule
stands.

## Cost when learned

One full gate run, about 9 minutes of wall time, plus the second run needed
to produce a bindable verdict. No work was lost: the in-flight board edit
was preserved in the session scratch directory and re-applied afterwards.
