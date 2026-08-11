# Vault best practices to keep, and how to optimize the memory system

Status: CURRENT, 2026-08-11 morning. No em or en dashes.

## Best practices this run proved, to be kept as standing vault habit

1. CHECKPOINT AT MILESTONES, NOT AT CLOSE. Tonight's session log gained a
   dated line at every loop close (nine appends). When context ran out
   twice, nothing was lost, because the log was already current. The law
   exists; tonight is its worked example.
2. ONE LINE PER EVENT, EVIDENCE INSIDE THE LINE. Every vault append names
   its SHA or command inline, so the log reads as a receipt trail rather
   than a diary.
3. HANDOVER CONTENT LIVES IN GIT AND THE VAULT, ZIP AS A COPY. The evening
   pack set the precedent (commit e17a8f6); this pack repeats it: sources
   under `docs/handover/`, the zip is packaging, never the only home.
4. LEARNINGS TRAVEL WITH THEIR SCARS. Each learning names the incident
   that earned it, which is what makes the Failures-Index queryable later.

## How to optimize the vault and its Obsidian shape

The session log for this one night is ~120 lines of append-only prose.
Fine for a receipt trail, bad for retrieval. Recommended structure work,
half a day total, MEDIUM-HIGH confidence, all inside
`Kay Vault/10-Projects/brothermode/`:

1. ATOMIZE LEARNINGS. Each learning from 02-LEARNINGS becomes one note in
   `40-Failures/` (vault-wide space) or a project `Learnings/` folder, one
   fact per file with frontmatter (`type: failure-lesson`, `earned:` date,
   `evidence:` line) and a stable kebab slug, for example
   `[[gate-verdict-binds-to-one-sha]]`, `[[copy-drift-two-renderers]]`,
   `[[park-cannot-free-foreign-fence]]`. Session logs then LINK these
   instead of restating them, which is what makes the Obsidian graph show
   which scars recur.
2. A LEARNINGS MOC (map of content). One `Learnings-MOC.md` per project
   listing the atomic notes by theme (fences, gates, evidence, audits),
   linked from Overview. Ten minutes to create, keeps Home short.
3. FAILURES-INDEX GETS THE RECURRING CLASSES ONLY. Seven stale-fence bites
   are ONE index row pointing at one atomic note with a count, not seven
   entries. The index is for before-work consultation; counts tell it
   loudest.
4. SESSION LOGS ROTATE. One file per session (already true), but a session
   spanning a night gets dated section headers instead of a flat append
   stream, so Obsidian's outline pane becomes the timeline.
5. AUTO-MEMORY STAYS POINTERS. The `~/.claude` auto-memory already follows
   the pointer-only law; tonight added no duplicates. Keep MEMORY.md lines
   one per fact with the hook in the line, and move anything that grew a
   second sentence into the vault.
6. PRUNE THE BAK NOISE. STATE.md.bak files churn five at a time in the
   repo root and appear in vault snapshots that mirror the tree. They are
   generated recovery artifacts; exclude the pattern from any vault mirror
   so graph search stops surfacing them.
7. CONTEXT-PACK REFRESH AFTER PROGRAM CHANGES. The category ownership
   program changed the project's shape; the vault space's Context-Pack
   should be regenerated to name the execution ledger as the live roadmap
   pointer, or a fresh session will read last week's shape first.

## What NOT to change

Do not add semantic or vector retrieval to the vault on the strength of
this night. That is exactly Loop M1's point: the labeled corpus and the
evaluation come first, and lexical retrieval plus good linking may win.
The optimization above is structure and linking, which improves BOTH
lexical retrieval and human navigation at zero model cost.
