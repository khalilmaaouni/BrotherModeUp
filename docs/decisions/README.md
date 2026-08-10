# Decision records the shipped code cites

These are the documents that BrotherMode's own source refers to by name. They
were written on 2026-08-07 and were NEVER COMMITTED until 2026-08-10, which
meant nineteen citations across seven shipped files pointed at reasoning that
nobody cloning this repository could read. That is fixed by their presence
here. No em or en dashes anywhere in this file.

## What is here

| File | Cited in code as | What it is |
|---|---|---|
| `V3-FREEZE-2026-08-07.md` | `V3-FREEZE-2026-08-07.md` | The v3 architecture freeze: the founder decisions binding that run, and the freeze gate's answers. Cited for the namespace rename (answer 5, founder decision 1), the runtime boundary (answer 4), and the public command surface. |
| `architecture-refutation-2026-08-07.md` | `v3/architecture-refutation.md` | An adversarial refutation of that freeze, written by a reviewer briefed to disprove it rather than confirm it. 5 BLOCKER, 6 HIGH, 5 MEDIUM, 4 LOW. Cited for its adjudication rulings, chiefly B1 and B3. |

The code cites the second one under its ORIGINAL path,
`v3/architecture-refutation.md`, because that is where it lived when the
citations were written. It is the same document, moved here rather than
rewritten, and the old path is recorded in the table rather than edited out of
the source, because a citation that silently changes its target is worse than
one that needs a lookup line.

It carries a date in its filename now, and that is not cosmetic: this
repository decides whether a page reads as CURRENT state by whether its name is
dated, and this page uses the retired product name throughout. Undated, the
naming suite correctly refused it as a current page claiming a retired name.
Dated, it is what it actually is, a record.

## Why they are kept verbatim

Both are evidence records. The only edits made when committing them were
mechanical: absolute paths under the author's home directory were replaced with
`~` and `<repo root>`, so a public repository does not publish one machine's
folder layout. Nothing else was touched, and in particular no finding, no
severity and no ruling was softened. A decision record rewritten by the party it
judges is not a decision record any more.

## What they are NOT

They are historical. They record what was decided on 2026-08-07 and what an
adversarial reviewer said about it that same week. Several of their findings
have since been closed, and at least one thing they assert has since been
disproved by measurement. They are the reasoning behind the code's shape, not a
current status page. For what is true today, read `docs/limits/CURRENT.md` and
the generated status sections, which are maintained; these are not.
