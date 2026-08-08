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
| `brothermode-solo-builder-booklet.html` | THE OFFICIAL BOOKLET for this project. Written for solo founders and individual contributors deciding whether to adopt it. See below. |

## The official booklet (2026-08-08)

`brothermode-solo-builder-booklet.html` is THE official HTML artefact about
this project. The founder settled that on 2026-08-08. Anything else in this
folder is either a different audience kept for a stated reason, or history.

It is written for a solo founder or individual contributor deciding whether to
adopt this, and it is ordered pain first: what goes wrong when you hand serious
work to Claude, what relieves that immediately, what stops it coming back, and
only then the machinery. Five acts, 19 diagrams, roughly 5,700 words.

Tagline: **Build with Claude. Stay in control.** Category line: **The
reliability layer for Claude Code.** Both were checked against
`docs/brand/IDENTITY-CONTRACT.md` and the naming test before use; neither
touches a governed name token.

It is policed. Because it sits under `docs/` with no date in its filename,
`current_pages()` in `tools/test_bm_docs.py` picks it up, so
`TestCurrentPagesUseTheCanonicalNames` and `TestNoUnbackedAbsolutes` both run
against it. What does NOT run against it is `TestNoDashes`, scoped to a
different file list, and any check that a feature description in it is still
true. A renamed command would fail nothing here.

Three blocks in it are real captured tool output, not mock-ups: the eight-field
status, the section headings of a generated project page, and the node labels
of the three drawings that page produced. They were captured by running a
project through `tools/brothermode_cli.py` against a throwaway repository
outside this tree, and pasted exactly as printed.

HONEST LIMITS, stated rather than implied:

- Nobody outside this project has read it.
- It has no pinned test of its own, the way the dummies book has
  `TestTheAdoptionBook`. Adding one is the most useful follow-up for this file.
- No PDF export. Any browser's print dialogue produces one; the file carries a
  print stylesheet with a page break per act.

### What was retired, and why it is not simply gone

`brothermode-team-briefing.html` was removed on 2026-08-08. It was a good book
aimed at an internal engineering team, superseded when the founder chose the
solo-builder framing, which is also the framing `README.md` and
`docs/market/CATEGORY.md` already used ("built to scale down to one person
doing the work of several roles, not up to a team").

It is not lost. Recover it with:

    git show d4f2f91:docs/book/brothermode-team-briefing.html > restored.html

### Why the other HTML files in this repository stayed

Two of them cannot be deleted without turning the gate red, which is a fact
about the tests rather than a preference:

- `brothermode-for-dummies.html` is pinned at `tools/test_bm_docs.py:3406`,
  where `TestTheAdoptionBook` re-runs one of its walkthroughs against the real
  command line.
- `../brotherme-explained.html` is pinned by four assertions in
  `tools/test_bm.py`.

Retiring either one means removing its test in the same change, which is a
separate decision with its own review. `PROJECT-VIEW.html` is generated output
rather than a document, and `../one-pager.src.html` is a source file.

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
