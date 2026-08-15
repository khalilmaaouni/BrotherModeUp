Status: OPEN defect, found 2026-08-15, FILED NOT PATCHED by deliberate
decision recorded below. Not a historical record: this one is still true.
No em or en dashes.

# M22: the ignore rule was written for ourselves and never carried to a user

Found by asking a question a BrotherSBE session asked of itself first and then
handed across. Their hole was real and they closed it; this is the same
question turned on us, and the answer is the same shape.

## The claim, and the commands that establish it

Nothing in this product writes an ignore rule into a user's repository:

    grep -rnE "open\([^)]*gitignore|write.*gitignore" --include=*.py \
        --include=*.sh scripts/ tools/ hooks/ | grep -viE "read|parse|rules|test_|pattern|regex"

returns one hit, a comment in tools/bm_docs.py. There is no writer.

BrotherMode creates `<root>/.brothermode/` in any project it is used in, and
that directory holds store.sqlite3: session ids, objectives, claimed file
paths, evidence text, and recorded founder decisions with their alternatives.

In THIS repository it is ignored, which is why nobody noticed:

    git check-ignore -v .brothermode/store.sqlite3
    .gitignore:9:.brothermode/	.brothermode/store.sqlite3

That line is in OUR .gitignore because we wrote it for ourselves. A user who
installs BrotherMode into their own project inherits nothing: the directory is
neither tracked nor ignored there, which is the worse of the two states,
because tracked would at least have been a visible decision.

## Why it is not fixed in the same session that found it

It changes a shipped setup path, on behalf of machines nobody here can see, at
the end of a session. The BrotherSBE session reached the same conclusion about
their identical hole an hour earlier and filed rather than patched, and the
reasoning holds in both directions: a filed defect with a runnable done-check
is worth more than a rushed change to code that runs on someone else's laptop.

## Done-check, to be run when it is fixed

Run BrotherMode's documented install into a scratch git repository, open one
claim, then run `git status --porcelain` and observe that no file carrying a
session id, an objective, or an operator's name appears as untracked.

## Status of a control

NOT ENFORCED. No test asserts that a consumer repository ends up ignoring what
we write into it. Candidate control, not built: a test that runs the install
into a temporary git repository and fails if `git status --porcelain` lists
anything under the marker directory.

## The class this belongs to, and the practical form of the rule

Three instances of one failure class landed in about four hours on 2026-08-15,
across two products and two sessions, twice against sessions that were
actively looking for it:

1. A behaviour node called unshipped after running a check at one repository
   root (BrotherSBE).
2. The seam number: 4 of 5 here with a deposit present, 2 of 5 there with
   none, quoted by this session as a property of the seam until corrected.
3. This ignore rule, verified in the one directory where it happened to hold.

The vault already carries the class as
a-number-true-in-one-directory-reported-as-true-generally. What it did not
carry is a form that survives a tired session at midnight, because "be
careful" is not a control. The form, agreed across both sessions tonight:

    A measurement is quoted with its tree and its revision beside it,
    or it is not quoted.

Both products were writing the ignore rule in their own repository, for
themselves, and never carrying it to anyone else. That sentence is what makes
this obvious in hindsight, and it should survive into whatever fixes it.
