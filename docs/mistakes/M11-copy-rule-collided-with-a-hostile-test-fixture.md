# M11: the copy rule and a hostile test fixture could not both hold

## WHAT HAPPENED

Plain language: the founder has a standing rule that no em dash or en dash may
appear anywhere in this project, and a test enforces it over a named list of files.
The visual surface design said that list should grow to cover the four new visual
files.

At the same time, a different writer was building a test whose entire job is to
prove that hostile characters (an em dash, an en dash, an emoji) never survive into
terminal output. To test that, the test file had to CONTAIN those characters,
written literally.

So the widened copy rule and the new test collided: obeying one broke the other.
Nobody predicted the collision, because the two files were being written in
parallel by two writers who could not edit each other's files.

## HOW IT WAS FOUND

By a writer who checked another writer's file against a rule that had not yet been
applied to it. The tree moved underneath that writer while it was finishing:
`tools/test_bm_visual.py` appeared at 22:21 and the writer re-ran its check rather
than assuming its earlier reading still held.

## THE EVIDENCE

From `/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L05/RED-F.txt`
lines 188 to 219, verbatim:

```
LATE NOTE (added after the last edit, because the tree moved underneath it)

tools/test_bm_visual.py appeared in the tree at 22:21 while this writer was
finishing, landed by Writer D. ...

The new file was checked against the rule it is about to come under:

    tools/test_bm_visual.py em or en dash lines: [956, 959, 964, 978, 985]

Read at those lines, the dashes are deliberate hostile fixture data inside
test_every_text_medium_path_emits_ascii_only ...

So the design's section 13.4 widening and that test collide, and the collision
was not predicted. It was NOT resolved here: tools/test_bm_visual.py is Writer
D's file and this writer may not edit it, and narrowing the dash guard to let a
test file through would be weakening a founder ratified copy rule to fit one
fixture.
```

The writer then proposed the remedy rather than taking it: write the hostile
characters as backslash-u escapes, citing the precedent that the dash guard in
`tools/test_bm_docs.py` is written that way already for the same reason.

## HOW IT WAS FIXED

The owner of the file took the proposed remedy. Verified in the tree now:

```
$ grep -n "u2014\|u2013" tools/test_bm_visual.py
999:    EM = u"\u2014"                          # em dash
1000:    EN = u"\u2013"                          # en dash

$ for f in tools/bm_visual.py tools/bm_view.py tools/test_bm_visual.py \
    tools/test_bm_view.py; do printf "%s: " "$f"; \
    LC_ALL=C grep -c $'\xe2\x80\x94\|\xe2\x80\x93' "$f"; done
tools/bm_visual.py: 0
tools/bm_view.py: 0
tools/test_bm_visual.py: 0
tools/test_bm_view.py: 0
```

The test means exactly the same thing to the machine, and the file now carries no
dash character, so both rules hold at once.

The guard was then widened as the design asked, at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_docs.py:4772`
(`test_no_em_or_en_dash_in_the_active_pages_or_this_toolchain`), whose target list
at tools/test_bm_docs.py:4774 to 4783 now includes all four L05 files. The comment
at tools/test_bm_docs.py:4784 to 4790 records why it is safe:

```
# All four are verified pure ASCII with hostile fixture characters written as
# backslash-u escapes, which is what lets this guard and those fixtures hold
# at once.
```

## THE RULE THIS PRODUCES

When a rule and a test seem to contradict each other, do not narrow the rule and do
not delete the test: change how the test spells its data, and write the reason into
the guard so the next reader does not reopen the argument.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, and no user-facing behaviour was ever at risk here. What was at risk was
the rule itself. The wrong fix (narrowing the dash guard to exempt test files) was
available, cheap, and would have quietly removed the copy rule's teeth for a whole
category of files. It was refused on the grounds that a writer may not weaken a
founder ratified rule to fit its own convenience, which is the part worth copying.
