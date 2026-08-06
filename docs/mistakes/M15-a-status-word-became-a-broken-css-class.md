# M15: a status word was pasted straight into a CSS class and broke the page

## WHAT HAPPENED

Plain language: the generated project page colours each box by its status. The code
built the style name by pasting the status word straight in. Two statuses broke it:

- "not run" produced `class="bm-not run"`. A browser reads that as TWO classes, one
  of them called `run`, so the box lost its intended style entirely.
- "NOW" produced `class="bm-NOW"`, while the stylesheet defines the rule as
  `.bm-now`. Case does not match, so nothing applied.

Both were real, both were on the rendered page, and both are the kind of bug that a
passing test suite says nothing about, because the markup was well formed and the
data was correct.

## HOW IT WAS FOUND

By the writer LOOKING at a rendered page, then turning what it saw into a check.
The writer's own report lists it as the fourth of four guards that fired, and it is
the only one of the four that no existing guard would have caught.

## THE EVIDENCE

From
`/Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/evidence/L05/FIX-L05-store-report.md`
lines 444 to 450 (inside the section "Guards that fired, and what was done at the
class", which starts at line 419), verbatim:

```
4. **My own class-coverage check, added after LOOKING at a rendered page.**
   The status "not run" was emitting `class="bm-not run"`, which a browser
   reads as two classes, one of them called "run", and "NOW" was emitting
   `class="bm-NOW"` against a rule written `.bm-now`. Fixed with a `_slug`
   helper, and the check that found it is now an assertion inside
   `TestColourIsNeverAlone`, comparing every class the markup uses against
   every class THEME_CSS defines.
```

## HOW IT WAS FIXED

A `_slug` helper at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_visual.py:1077`, which
lowercases and collapses every run of non alphanumeric characters to one hyphen. It
is applied where the class is built, at tools/bm_visual.py:1096 inside `_box`.

The helper's docstring carries the reason, so the next reader cannot mistake it for
tidiness, verbatim from tools/bm_visual.py:1078 to 1084:

```
Not cosmetic. A token used raw would emit class="bm-not run" for the
status "not run", which the browser reads as TWO classes, one of them
called "run", and class="bm-NOW" would never match the rule written
as .bm-now. Both were real, both were found by rendering the page and
comparing the classes it used against the ones THEME_CSS defines.
```

The one-off check became a permanent assertion inside `TestColourIsNeverAlone`
(`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_visual.py:312`),
which compares every class the markup emits against every class the stylesheet
defines. So the next status word that does not survive slugging fails the suite
instead of silently losing its colour.

## THE RULE THIS PRODUCES

Any string that becomes an identifier (a CSS class, an HTML id, a filename, a URL
fragment) must go through one normalising helper, and the page must be rendered and
looked at, because a well formed page with the wrong class name passes every
structural test you have.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, and only because somebody rendered the page and looked at it rather than
reading the code. It is the clearest argument in this folder for the rule that a
user-interface change is verified by looking, never by reasoning about the source.
