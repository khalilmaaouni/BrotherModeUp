Status: DRAFT for the founder to send. Not sent by any session.

# The note that ships 3.2.0 to the five reviewers

CORRECTED 2026-08-15, and the correction is the whole point of this section.

An earlier version of this page said nothing had to be pushed, because the
tag `v3.2.0` is on the remote. The tag IS on the remote. It does not contain
the work. An adversarial check was asked to disprove the claim and did, and
the same commands re-run here confirm it:

    git rev-parse v3.2.0^{}                     -> 96d6d12
    git show 96d6d12:VERSION                    -> 3.2.0
    git ls-tree 96d6d12 templates/dossier/08-behaviour.md tools/sbe_testkit.py
                                                -> (empty)
    git ls-tree origin/main <same two paths>    -> (empty)
    git rev-list --count origin/main..HEAD      -> 43

So the public `v3.2.0` carries the version STRING 3.2.0 and carries neither
the behaviour table nor the testkit. Both live in 43 unpushed local commits.
Sending a reviewer to `v3.2.0` today would send them to a build that answers
neither of the two findings this note is about, and the version number would
tell them nothing was wrong.

That is the third instance in one day of one failure: a version that does not
describe its own contents. First the installed clone reporting a number
generations behind the source. Then this page saying a defect was open 28
minutes after it was fixed. Now a public tag whose number promises work it
does not carry. The pattern is not carelessness, it is that nothing anywhere
binds a version to what is inside it, which is exactly finding G3.

WHAT SHIPPING ACTUALLY REQUIRES, therefore, and it is a founder decision
because it is outward facing:

1. Push the 43 commits, or the subset carrying the behaviour table and the
   testkit, to the remote.
2. Cut a NEW version and tag. The number must move, because `3.2.0` has
   already been published meaning something else, and re-pointing a published
   tag is worse than a new number.
3. Only then send the update command below.

Nothing in this session pushed, tagged or released anything.

What the reviewers ran, and it is worse than one number: the installed copies
on this machine alone do not agree with each other.

    ~/.claude/skills/brothersbe/VERSION                          1.0.0-rc.2
    ~/.claude/plugins/marketplaces/brothersbe/VERSION            1.0.0-rc.38
    ~/.claude/plugins/cache/brothersbe/brothersbe/1.0.0-rc.1/    1.0.0-rc.1
    ~/.claude/plugins/cache/brothersbe/brothersbe/1.0.0-rc.38/   1.0.0-rc.38
    ~/.claude/skills/brothersbe/tools/sbe_testkit.py             does not exist

Three distinct installed versions, and no reviewer has any way to know which
one answered their question. Asking somebody to re-test without first telling
them exactly which build they are on is asking for another week of review
against the wrong code.

## Update command for each reviewer, AFTER the push and the new tag

    cd <their BrotherSBE checkout>
    git fetch --tags origin
    git checkout <the new tag>
    ls tools/sbe_testkit.py templates/dossier/08-behaviour.md

The last line is not decoration. It is the one-second check that the build
they are now on actually contains the two things this note claims it does,
and it is exactly the check whose absence caused this correction.

Plugin users update through the marketplace instead, and the pinned version in
`.claude-plugin/plugin.json` has to move with the tag.

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
