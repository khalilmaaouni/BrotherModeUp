# BrotherMode for Dummies

Status: CURRENT. Part one (chapters one to twelve) was written 2026-07-30
against commit `471efdc` (2.0.0-rc.4), with every transcript run against a real
throwaway project at that commit. Part two (chapters thirteen to sixteen) plus
the chapter two install rewrite and the corrected Windows-CI limit were added
2026-08-01 at 2.0.0-rc.11, after a founder review asked for the expert half:
the guided command layer, the vault and Obsidian in depth, and two composed
persona walkthroughs (a multi-week product build; analytics under scrutiny).

The adoption book, phase D of
`docs/superpowers/specs/2026-07-30-documentation-and-gate-packs-design.md`
section 7. Part one is written for someone who has never heard the words agent,
loop or hook; part two takes the same reader to expert use.

HONEST NOTE ON THE PDF: `brothermode-for-dummies.pdf` is the 2026-07-30 export
of part one only (56 pages, twelve chapters). It has not been regenerated for
part two; the HTML file is the current book. Regenerate the PDF by opening the
HTML in a browser and printing to PDF, then update this note with the new date.

## The files

| File | What it is |
|---|---|
| `brothermode-for-dummies.html` | the book. One self-contained file, inline CSS, diagrams as inline SVG, no external reference of any kind. Open it by double clicking it. |
| `brothermode-for-dummies.pdf` | the PDF export, 56 pages, produced from the HTML on 2026-07-30. See the note below on how, and on what that means for regenerating it. |
| `brothermode-team-briefing.html` | the team briefing, a different book for a different reader. See below. |

## The team briefing (added 2026-08-08)

`brothermode-team-briefing.html` is written for a working engineering and
analytics team, not for a first-time beginner. Where the dummies book teaches
someone who has never heard the word hook, the briefing answers the four
questions a developer actually asks: what is this, what does it refuse to do,
how is it different from every other Claude Code plugin, and how do I run my own
project on it.

Its shape, and why: part zero is a two-page summary anyone can read, and it
carries the largest limit (never measured on a real project) on its second page
rather than in an appendix. Part two is the full feature register, every
capability with its role AND its limit, plus the four capability states. Part
three is the differentiation chapter, which names peers directly and labels
every peer claim a desk assessment, following the fairness rules in
`docs/market/CATEGORY.md`. Part four walks six end-to-end projects, one per
work-nature profile in `references/profiles.md`. Part five is six personas with
what each will like and what each will resent. Parts six and seven are the
inherited rules and the look-up reference.

Three outside structures shaped it, each read from the page itself on
2026-08-08: Diátaxis (<https://diataxis.fr>) for keeping tutorial, how-to,
reference and explanation apart; SQLite's "when to use" page
(<https://www.sqlite.org/whentouse.html>) for the three-part honesty structure
of part three; and The Good Docs Project README template
(<https://www.thegooddocsproject.dev/template/readme>), which treats a
limitations section as OPTIONAL, which is what makes putting it on page two a
deliberate departure rather than a convention.

Same self-containment rules as the dummies book: no `<script>`, no `<link>`, no
`<img>`, no `@import`, no external font. Diagrams are hand-written inline SVG.
Verify with the same greps below.

HONEST LIMITS OF THIS FILE, stated rather than implied:

- It is PARTLY held by `tools/test_bm_docs.py`, and an earlier version of this
  note wrongly said it was not held at all. Corrected 2026-08-08. Because the
  file sits under `docs/` and carries no date in its name, `current_pages()`
  picks it up, so two rules run against it: `TestCurrentPagesUseTheCanonicalNames`
  and `TestNoUnbackedAbsolutes`. Verify with:

      python3 -c "import importlib.util;s=importlib.util.spec_from_file_location('t','tools/test_bm_docs.py');m=importlib.util.module_from_spec(s);
      exec('try:\n s.loader.exec_module(m)\nexcept SystemExit:\n pass');print([p for p in m.current_pages() if 'team-briefing' in p])"

  What does NOT run against it: `TestNoDashes`, which is scoped to `ACTIVE_DOCS`
  plus an explicit file list this page is not on, and any check that a feature
  description in it is still true. The dummies book additionally has
  `TestTheAdoptionBook`, which re-runs one of its walkthroughs against the real
  command line; this book has no equivalent. So a renamed command would not
  fail anything here, and the page would go stale quietly. That gap is the
  most useful follow-up available for this file.
- It quotes no test count and no productivity number, for the reasons the file
  itself states in its closing note.
- No PDF export exists. Any browser's print dialogue produces one; the file
  carries a print stylesheet with a page break per part.
- It was rendered and inspected at desktop width and at 375 pixels wide, and its
  text contrast was audited in both light and dark themes with zero failures at
  the 4.5 to 1 threshold. It has not been read end to end by anyone but its
  author.

REORGANIZED 2026-08-01 after the founder rated the tour-shaped book 1 of 5:
the book is now task-first, per the ratified rebuild spec
(docs/superpowers/specs/2026-08-01-docs-rebuild-after-1of5-design.md). It
opens with a one-screen cheat sheet, then four parts: DO (three short
tutorials, 217 words to first proven success), SOLVE (the how-to chapters),
UNDERSTAND (philosophy and architecture, behind a divider no first-time
reader must cross), and LOOK UP (references, glossary, and a task index that
maps "I want to..." questions to anchors). All sixteen original chapters
survive inside the parts with their numbers and anchors unchanged, each still
ending in a "try this now" the reader can actually run.

## How to read it offline

    open docs/book/brothermode-for-dummies.html

There is nothing to serve and nothing to install. The page makes no network
request: no `<script>`, no `<link>`, no `<img>`, no `@import`, no `url()`. The
diagrams are hand written inline SVG rather than a mermaid library, precisely so
that no runtime and no external file is needed to see them. The one `https`
string anywhere in the file is inside a code block: it is the `git clone` command
the reader types in chapter two, and it causes no fetch.

Verify all of that yourself:

    grep -c -e '<script' -e '<link' -e '<img' -e '@import' -e 'url(' \
      docs/book/brothermode-for-dummies.html   # expect 0
    grep -n 'https://\|http://' docs/book/brothermode-for-dummies.html
    # expect exactly one hit, the git clone line inside a <pre><code> block

The gate checks it as well, so this cannot rot quietly. `TestTheAdoptionBook`
in `tools/test_bm_docs.py` re-runs chapter six's citation walkthrough and both
of its alert refusals against a real store through the real command line, and
fails on the PAGE when the tool stops printing what the page says it prints.

## The PDF, honestly

The PDF in this folder is real and complete: 56 pages, produced from the HTML on
this machine on 2026-07-30. It was NOT produced by BrotherMode's own optional
exporter, and it could not have been.

`python3 tools/bm_docs_export.py report` on this machine says:

    pdf   NOT available
          no writer for pdf is installed here. Tried reportlab, fpdf, weasyprint,
          none importable.

That is accurate. The exporter is restricted to importable Python modules,
because every shipping tool under `tools/` is forbidden from running a
subprocess (invariant I3), and none of those three modules is installed here.

The book's PDF was therefore produced by hand, outside `tools/`, with the print
engine that happens to exist on this machine:

    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
      --headless=new --disable-gpu --no-sandbox \
      --user-data-dir=/tmp/bm-pdf-profile \
      --no-pdf-header-footer \
      --print-to-pdf=docs/book/brothermode-for-dummies.pdf \
      "file:///ABSOLUTE/PATH/TO/docs/book/brothermode-for-dummies.html"

What that means for you, stated rather than implied:

- **This is not a repeatable build step and it is not wired into anything.** It
  depends on a browser being installed at that path. On a machine without one,
  the HTML is the deliverable and the PDF simply is not regenerable. Nothing in
  the repository depends on the PDF existing.
- **The headless process does not always exit cleanly** after writing the file.
  It wrote the PDF and then hung; the file was already complete and byte-stable
  across two runs. Kill it rather than waiting.
- **Any browser's print to PDF will work**, as will the print dialogue in any
  browser (open the HTML, print, save as PDF). The book carries a print
  stylesheet: one chapter per page break, long commands wrapped rather than
  clipped, and diagrams and tables kept off page boundaries.

The page count `file(1)` reports for this PDF is wrong. It prints `8 pages`
because it reads the first node of a nested page tree. The root node's `/Count`
is 56, which is the real number.

## The rules this book holds itself to

- Every command shown was executed by the author against a throwaway git
  repository built for the purpose, and every block presented as output is
  pasted from that run.
- Every capability claim is true of the code at `471efdc`. Where a capability is
  unverified, the book says unverified in plain words. Chapter ten is entirely
  about keeping "this runtime has hook points" apart from "BrotherMode's hooks
  work in this runtime", because only Claude Code is verified for the second.
- **No productivity numbers, anywhere.** BrotherMode has never been run through
  a real working day (`docs/KNOWN-LIMITS.md`), so any figure would be invented.
- Chapter nine names the task types BrotherMode is NOT worth using for, starting
  with a one line obvious edit.
- No em dashes and no en dashes, including inside the generated PDF (invariant
  I7).

## Four defects the book found and reports rather than hides

Found by driving the real command line against a throwaway store while the test
suite was green. All four are described in the book's own closing note; none is
fixed by this change, because phase D may not touch `tools/`.

1. `bm_store.py claim --help` creates a work record actually named `--help`.
   Usage prints only when the verb is given no arguments at all, so a flag is
   treated as the record name. Reproduced, and the stray record appeared in
   `dashboard`.
2. `--handover "<heading>"` is the entire person to person handover mechanism and
   it is absent from the `park`, `resume`, `complete` and `adopt` usage lines. It
   cannot be discovered from the CLI.
3. `bm_telemetry.py fence-lint` reports `no live fences found` against a
   store-generated `STATE.md` that holds two active records. It matches a V1 era
   hand written fence line format, which requires the literal word `agent`; the
   generated format does not contain it. `docs/HOW-IT-WORKS.md` section 5 says it
   prints the live fences from the project's `STATE.md`, which is no longer true.
4. Every `STATE.md` render leaves another `STATE.md.bak-<timestamp>` file behind.
   Seven accumulated in about fifteen minutes of ordinary use.
