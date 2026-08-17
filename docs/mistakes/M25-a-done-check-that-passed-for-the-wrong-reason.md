Status: CURRENT as of 2026-08-17. Written by the session that made the mistake.
Line numbers were correct on 2026-08-17 and may move.

# M25: a done-check that passed for the wrong reason, written by the orchestrator

## What happened

A brief was handed to an implementer to add two keys, `owner:` and `expires:`, to
two mirrored `parse_exemption` functions in the sibling repository, one in
`tools/sbe_design.py` and one in `tools/sbe_gate.py`. The brief ended with a
runnable done-check, as every brief here must. The done-check was this:

    body='checks: adr\nowner: the QC lead\nexpires: 2000-01-01\nreason: ...'
    wd,rd,pd = design_parser(body)
    wg,rg,pg = gate_parser(body)
    assert pd and pg, 'both parsers must refuse an expired exemption'

It printed `OK both parsers refuse an expired exemption`. The implementer ran it
as given, reported that output faithfully, and was right to.

The check is worthless. The two parsers do not share a vocabulary: the design
parser's exemption file names `checks:` and the gate parser's names `gates:`. So
the gate parser refused the fixture for having the wrong key entirely, and its
`problem` string was non-empty for a reason that has nothing to do with expiry.
The assertion only tested that both problems were non-empty. Both were. It
passed.

## How it was found

By re-running the implementer's own done-check rather than accepting its reported
output, and printing the problem strings instead of only asserting on them:

    design problem: 'its expires: 2000-01-01 is in the past; an expired
                     exemption is refused, not honored'
    gate   problem: 'addressed to tools/sbe_design.py: it names checks: and
                     no gates:'

The second line is the whole finding. It was invisible while the check only
asked whether the string was empty.

## The evidence

Re-run with each parser given its own vocabulary, the implementation turns out to
be entirely correct:

    gates: ran + expires: 2000-01-01   refused, "its expires: 2000-01-01 is in
                                       the past; an expired exemption is
                                       refused, not honored", checks []
    gates: ran + expires: 2099-01-01   accepted, reason gains
                                       "[owner: the QC lead; expires: 2099-01-01]"
    gates: ran + neither key            accepted, reason gains
                                       "[no owner recorded, no expiry recorded]"

So nothing was wrong with the code. What was wrong was the proof, and the proof
was written by the orchestrator, not the implementer.

## How it was fixed

The done-check was replaced with one that feeds each parser its own vocabulary
and prints the problem string rather than testing it for emptiness. The
distinction that matters and that this record exists to preserve: the
implementation was right and the verification could not have detected if it had
been wrong.

## The rule it produces

An assertion on the SHAPE of a failure is not an assertion about the failure. A
check that asserts a problem string is non-empty passes on any problem,
including one the change did not cause and one that proves the fixture was
malformed. Assert on the CONTENT: the expected substring of the expected
message, from the expected component.

The corollary, and it is the reason this is filed under mistakes rather than
notes: an orchestrator who writes the done-check owns its correctness. A brief
whose done-check can pass for the wrong reason has handed the implementer a
green it cannot earn, and reviewing the implementer's report will never catch it,
because the implementer did exactly what it was told and reported the truth.

The founder's standing rule already covers this and it was not applied at the
moment of writing the brief, only afterwards: a green from a script you wrote is
worthless until you have tried to make it lie. The way to try, concretely, is to
run the check against code you know is BROKEN and confirm it goes red. That
takes one extra command and it is now the last step of writing any done-check.

## Caught before or after it could hurt a user

Before. The change had not been committed and no verdict had been reported to
anybody. But note what nearly happened: this was one of the three items whose
entire purpose is to stop a green verdict over-claiming, and its own proof was
over-claiming. Had it merged on that evidence, the fix for a lying green would
have shipped on a lying green.
