Status: DRAFT for the founder to send. Not sent by any session.

# The note that ships 3.2.0 to the five reviewers

Nothing has to be pushed first. Checked 2026-08-15: the tag `v3.2.0` is
already on the remote (`c8a20e2`, confirmed with `git ls-remote --tags`), so
the build the reviewers need is public today. The local repository is 43
commits ahead of it, which is later work, not a blocker for this.

What the reviewers ran, and why the mismatch matters: their installed copy
reports `1.0.0-rc.2`. Two of their findings were answered in source on
2026-08-15, after their review was written.

## Update command for each reviewer

    cd <their BrotherSBE checkout>
    git fetch --tags origin
    git checkout v3.2.0

Plugin users update through the marketplace instead; the pinned version in
`.claude-plugin/plugin.json` is `3.2.0`.

## The message, to send with it

Draft below. Roles rather than names, so it can be pasted into any channel
without a scrub pass; put the real names in when sending.

---

Two of the strongest findings in your review were answered in a build you did
not have. Rather than argue the point, here is the build, and a request.

To the architecture reviewer, on the largest gap you named, that none of the
design documents states the rules the software must follow. There is now a
behaviour table in every design folder from the second tier upward:
`ID | Starting point | Trigger | Required outcome | Proof`. Its check refuses
a rule with no agreed proof, refuses rows that are still the shipped example,
refuses a verification plan citing a rule that was deleted, and fails on an
unreadable table rather than passing quietly. One clause of your finding
stands and we are not claiming otherwise: it does not say who writes the
table. Your observation that the one step with no tooling is the step where
behaviour gets defined is the reason that clause is still open.

To the QC lead, on the question nobody could answer. The behaviour table now
generates your own working sheet, one case per rule, plus an exploratory tail
whose first charter is named `unnatural-behaviour`: the software does
something nobody asked it to. Interface problems, misunderstandings from the
design phase and awkward translated text have their own charters beside it. A
filled sheet reads back and drafts new behaviour rules from what you found, so
a discovery becomes a rule for next time instead of a comment on a ticket.
None of it is a gate, deliberately: the moment exploratory testing becomes a
gate it stops being exploratory.

The request is one run each, not a re-review. Run the sheet once on the change
we tested together, and tell us the only thing that decides whether this idea
is worth anything: did it catch what you would have caught anyway.

Three other things, said plainly rather than promised:

- The sizing complaint is confirmed exactly as reported. One question, whether
  a contract changed, produces the heavy tier on its own. It is four lines of
  code and it is the next thing being fixed.
- The step called PROVE checks that documents exist, not that the software
  matches the design. You are right, including that it belongs to the engineer
  rather than to QC. That is a rewrite of the process page, not a defence.
- The queue problem behind all of this, that QC verifies more slowly than
  developers now build, is not something any of this fixes. We will measure
  it and show the numbers either way rather than adding a step and calling it
  a fix.

---

## What to do with the answers

Both replies land against P9 and P14 in the problem analysis. If the
architecture reviewer confirms the behaviour table closes the gap, P9 closes
and P2's ownership question is what remains. If the QC lead says the sheet
caught nothing she would have missed, P14's tooling half is worth keeping and
the honest next move is the unexamined-classes line on every green summary,
not more sheets.
