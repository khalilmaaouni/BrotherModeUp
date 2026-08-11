Status: CURRENT

# Session decisions, 2026-08-11 afternoon, session 53c70dcb

Recorded at the moment they were taken, per the order-of-work law. This file
sits beside `SESSION-2026-08-11-afternoon.md`, written by session
`bm1-6ed31697927542d2dc2aab16`, deliberately: two sessions worked this
repository at the same time and each keeps its own record rather than editing
the other's. No em or en dashes.

## D-B1. Two sessions are live in one working tree, and neither is wrong

CONTEXT. At 12:17 a commit appeared in this checkout that this session did not
make: `8452914`, by session `bm1-6ed31697927542d2dc2aab16`, recording its own
afternoon decisions. A store read then showed that session holding an ACTIVE
`sd2-sentinel-build` fence over `tools/write_sites.json`, `tools/test_all.py`,
`hooks/hooks.json` and four SD2 sources, plus an adopted `cx1a-host-neutral-seam`
fence. Both sessions received the same founder instruction to keep working, and
both intend to push to the same `main`.

THE COLLISION, precisely. This session edited and committed
`tools/write_sites.json` at `6be2b47` (one added entry for the ceremony tool).
That file is inside the other session's SD2 fence. The edit was not a fence
violation at the time it happened: the SD2 record was in `adopted` state and the
controller's own per-unit claim over that file was granted rather than refused.
The other session later re-claimed it as ACTIVE. Two lawful claims, sequenced,
with no mechanism that shows one session what the other is about to claim.

DECISION. This session touches none of the other session's claimed files again.
Its remaining work (the ceremony pack, the gate, the push) reads `test_all.py`
rather than writing it, and adds nothing further to `write_sites.json`. The full
gate runs in an ISOLATED detached worktree at this session's own commit, not in
the shared tree, because a gate binds to one commit and the shared tree is being
edited by somebody else; running it here would produce a verdict about a tree
neither session controls.

ALTERNATIVES CONSIDERED. Stop and wait for the other session to finish: rejected,
because both were told to continue and the work is disjoint everywhere except one
already-committed line. Take over the SD2 fence: rejected, because that displaces
a session that is actively building against it, which is the precise failure the
fence exists to prevent. Ask the founder: rejected only because they are away;
this is reported to them in the close, not resolved silently.

FLIP CONDITION. If the other session's work and this one's collide again on any
file, or if either push is refused for a non-fast-forward, both lanes stop and
the founder arbitrates.

## D-B2. The public repository keeps its private vault name, and this session
stops adding more

CONTEXT. This repository is PUBLIC, confirmed from GitHub rather than from the
local registry (`gh repo view --json visibility` returned PUBLIC). The push
policy in `~/.claude/skills/github-desktop-push/repos.md` records a sanitization
sweep for this repo, and names the founder's private vault name as a term that
was caught leaking here once before. The sweep this session ran over its own
outgoing range found that name in seventeen tracked files, including two handover
packs already published, and found absolute home paths in dozens more.

DECISION. New code and documentation written by this session name the memory
vault generically ("the memory vault"), which is also what an outside installer
of a public tool actually has: nobody outside this machine owns a vault by that
name, so the generic term is better product language as well as safer. Nothing
already published is rewritten.

WHY NOT SCRUB THE HISTORY. Removing a term from published history is a force
rewrite of a public repository. That is founder-only under the safety floor, it
breaks every clone, and the exposure it would address is a directory name rather
than a credential. It is surfaced to the founder as a decision with its options
rather than taken by a session while they are asleep.

ALTERNATIVES CONSIDERED. Sanitize this session's files and say nothing:
rejected, because a half-sanitized repository reads as clean while the exposure
continues. Leave the new files matching the published wording: rejected, because
"every change lands here only after the sanitization sweep" is the recorded
policy and the generic wording costs nothing.

FLIP CONDITION. The founder decides either that the exposure is acceptable and
the term may be used freely again, or that a history rewrite is worth its cost,
at which point they run it.

## D-B3. Push happens, and what it carries

CONTEXT. The founder granted push authority explicitly. The standing policy for
this repository is direct to main with every gate mandatory (ratified
2026-08-10, decision 5).

DECISION. This session pushes only after a full gate green quoted from the
gate's own receipt, with the secret scan, the dash scan and the sanitization
sweep all run over the full outgoing range. The push carries the other session's
commit `8452914` as well, because it sits in the same range; its content is a
decisions document and was included in every scan this session ran.

WHAT THE WAIVER DOES NOT COVER, stated because the founder said "I waive any
limitation" and a waiver is not a control: credentials are never typed, no force
push, nothing destructive, and GitHub's own branch protection is obeyed wherever
it speaks. Those are refusals this system does not accept a waiver for.
