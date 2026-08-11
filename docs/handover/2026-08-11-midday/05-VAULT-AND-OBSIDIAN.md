# Vault state and memory hygiene

Status: CURRENT, 2026-08-11 midday. No em or en dashes.

## Where memory stands

- The session log
  (Kay Vault/10-Projects/brothermode/Sessions/2026-08-11-morning-ratification-and-v310-tag.md)
  was appended at every milestone, nine dated blocks, evidence inline.
  A fresh session reading it plus this pack has the full thread.
- Auto-memory stayed pointers only; nothing duplicated between vault and
  ~/.claude memory.
- The morning pack's vault optimization plan (atomize learnings, MOC,
  Failures-Index counts) is RATIFIED as SL-vault (decision 14, morning
  set) and still unexecuted: half a day, schedulable into any idle slot.

## Best practices this session kept

1. Checkpoint at milestones, not at close: two context boundaries passed
   with nothing lost because the log was already current.
2. One line per event, evidence inside the line.
3. Handover content lives in git AND the vault; the zip is packaging
   (this pack repeats the precedent).
4. Learnings travel with their scars: M20 links the incident file, the
   ledger line, and the session log entry.

## For the successor, in order

1. Read the vault session log's last three blocks.
2. Read this pack 01 then 04.
3. Run `git rev-parse --short HEAD` and `python3 tools/bm_stall.py sweep`
   before touching anything.
4. Open your own work record via bm_learn apply, adopt the SD2 fence,
   and build.
