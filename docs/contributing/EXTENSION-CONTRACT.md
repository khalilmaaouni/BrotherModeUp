# What a third party may extend in BrotherMode, and what is off limits

This is a contract, not a suggestion. It names the surfaces a contributor may
build on, the surfaces that stay internal, and why the line sits where it
does, grounded in the files that already draw it inside this tree.

## The shape this project already commits to

Three things repeat everywhere in this codebase and any extension has to
repeat them too, or it will fail the project's own gate:

1. **Generated, not hand-written, facts.** `tools/bm_project_facts.py` is the
   one place allowed to state the version, the schema version, the test
   suite list, the hook count, and the install commands. Its own docstring
   says why: a hand-typed number goes stale the moment the tree moves, and a
   reader cannot tell a stale page from a broken install. Everything it
   deliberately refuses to print (a total test count) is refused for the
   same reason, and it says so in the docstring rather than leaving the gap
   unexplained. `tools/test_bm_docs.py` is the enforcement: it fails any
   current page that states a version, schema version, or install command
   that disagrees with what this tool reads out of the tree.

2. **A four-state capability register.** `capabilities.status.json` allows
   exactly four states: `certified` (proven in this tree today, evidence
   named), `beta` (real but with a named gap), `experimental` (built or
   planned but not measured), `unsupported` (not offered, and no plan makes
   it offered). Its own `source_of_truth` field states the rule directly:
   `tools/test_bm_docs.py` "refuses an entry with an unknown state, an empty
   evidence field, or an evidence pointer naming a file that is not in the
   tree." An extension that adds a capability, or changes the truth behind
   an existing one, updates `capabilities.status.json` in the same change,
   with an evidence string that names a real file or test, never a claim on
   its own, then regenerates the pages rendered from it:
   `python3 tools/bm_docs.py capability-status --write` and the
   `roadmap-status` subcommand. The register is the input; the capability
   block in `README.md` and the status block in `docs/ROADMAP.md` are output
   and are never edited by hand.

3. **`LOAD WHEN`, not always-loaded.** Every file under `references/` opens
   with a one-line `LOAD WHEN:` header stating the exact moment it should be
   pulled into context (for example `references/fences.md`: "a writing
   agent is about to be dispatched, or files could be touched by more than
   one writer at once"; `references/definition-of-done.md`: "a task is
   about to be called done, a review is being run, or acceptance of any
   piece of work is being decided"). A reference is a conditional load, not
   background reading. A new reference file follows the same header
   convention or it breaks the pattern every other file in that folder
   relies on.

## Stable to build on

These are the surfaces this project intends third parties to extend. They
have a declared shape, an existing example to mirror, and a test that
enforces the shape.

- **`commands/*.md`.** Confirmed shape from `commands/brotherme-status.md`:
  YAML frontmatter with one `description` line, then prose that (a) states
  the outcome the command produces in plain language, (b) names the exact
  mechanical command it runs and where that command's output comes from
  (never "answer from memory"), (c) says what to do with a field the
  records cannot answer, and (d) states what stays out of the default view
  and what an explicit flag (`--advanced`, `--ic`) adds. A command file is
  a thin instruction wrapper around a real, testable tool in `tools/`; it
  never contains business logic of its own. Confirmed by reading
  `commands/brotherme-status.md` in full and cross-checking it against
  `tools/test_bm_lead.py`, which tests the backing tool
  (`tools/bm_lead.py`) that command drives, not the markdown file itself.

- **`references/*.md`.** Confirmed convention: a `LOAD WHEN:` header line,
  then the guidance itself, written to be pulled in conditionally rather
  than read every turn. Confirmed by reading `references/fences.md` and
  `references/definition-of-done.md` in full. Run `ls references/` to see
  the current set following the same pattern; the count moves as files are
  added, so it is not pinned here.

- **`skills/brotherme/SKILL.md` and its flow sections.** Confirmed by
  reading the file in full: each flow (Guided kickoff, Next-step, Deep tour,
  Status, Review, Deliver) names a plain-language outcome and the reference
  file that governs it, and names the exact tool command it runs where one
  exists. Kickoff, Next-step, Deep tour, and Deliver each name a command
  (`bm_project.py start`, `bm_project.py next`, `bm_view.py render`,
  `bm_project.py deliver`); Status and Review name no command and are
  governed entirely by their reference files (`references/status-view.md`
  and `references/definition-of-done.md`). A third-party flow follows the
  same shape: an outcome in plain words, a reference for the rules, and a
  real command to run wherever the flow has one, and it stays inside the
  "How to speak, always" contract at the top of that file (outcome first,
  one recommended action, ranges never single numbers, plain words per
  `references/terminology.md`, bad news first).

- **The store CLI as a caller, not as a schema editor.** `tools/bm_store.py`
  states its own contract in its module docstring: it is "the ONE
  transactional store every ownership mutation goes through" and "the only
  writer of `<root>/.brothermode/store.sqlite3`." A third party may call
  `bm_store.py`, `bm_project.py`, `bm_lead.py`, and the other `tools/bm_*.py`
  entry points as subprocesses or through their documented command-line
  surface, exactly the way `commands/brotherme-status.md` calls
  `tools/bm_lead.py status`. That is a stable, versioned CLI surface: a
  contributor writes to the store only through it, never by opening the
  sqlite file directly or writing a second store of ownership truth (the
  docstring calls that exact mistake out by name as the failure this store
  was built to close).

## Internal, off limits

- **The store's own schema.** `SCHEMA_VERSION` in `tools/bm_store.py`, the
  table shapes underneath it, and the sqlite file at
  `<root>/.brothermode/store.sqlite3` are internal. A third party reads and
  writes through the CLI or the documented Python entry points, never
  through a raw SQL statement against that file and never by asserting a
  particular table layout will still exist next release. `tools/bm_project_facts.py`
  reads `SCHEMA_VERSION` out of the source with a regex specifically so that
  no other file has to hardcode it; that is the tell that the number itself
  is not a stable interface, only the fact-reading path to it is.

- **Hook payload parsing.** The fence hook (`hooks/hooks.json` plus its
  Python handlers, referenced from `references/fences.md` section 5) reads
  and interprets the harness's own hook event payloads. That parsing is
  wired to the specific shape Claude Code's hook events carry today.
  `references/fences.md` itself flags this kind of surface as fragile even
  internally: it records a past mistake (the orchestrator writing fence
  lines for others but not itself) as evidence that this machinery is
  easy to get subtly wrong even for the people who own it. A third party
  extends behavior by adding a new command or reference that calls the
  existing tools, not by adding a second parser of hook payloads or a
  second writer of fence state alongside the one `references/fences.md`
  describes ("One writer per file, ever.").

- **Anything `bm_project_facts.py` deliberately does not print.** Its
  docstring names one example directly: a total test count, refused on
  purpose because it drifts within a day of any test landing and a stale
  number is worse than none. A third-party page follows the same
  discipline: state the gate command (`python3 tools/test_all.py`) and its
  expected verdict (`ALL GREEN`), never a hand-typed count.

- **Declaring a capability state without evidence.** `capabilities.status.json`
  is enforced by `tools/test_bm_docs.py`, but the enforcement only catches
  a missing evidence field or a dangling file pointer, not a false claim
  behind a real-looking pointer. Writing `"certified"` for something that
  is not proven in the tree today is a violation of the contract even when
  it would pass the mechanical check, because the mechanical check is a
  floor, not the whole rule.

## The rule that ties it together

Every stable surface above resolves to the same shape: a markdown file that
states an outcome in plain language, and a real command underneath it that
can be run and checked. If a proposed extension cannot name the exact
command a reader would run to verify its claim, it does not belong on a
stable surface yet, no matter how reasonable the prose sounds.
