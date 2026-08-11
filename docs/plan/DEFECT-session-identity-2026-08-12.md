# The fence identity defect: a person cannot claim a fence for themselves

Status: CURRENT

Found 2026-08-12 by running the product. This is the top-ranked sprint one
item because it is the sharpest edge against zero-tax adoption: a new person
who locks themselves out of their own file on day one does not come back.

**Everything below was verified by running commands, and the outputs are
quoted. STATUS: the fix LANDED 2026-08-12, and its live proof is at the
bottom of this file.**

---

## The symptom

You claim a fence over a file. You then edit that file. The write hook
refuses you, as a foreign writer, on your own claim.

Hit four times in one night by one session, including on its own README edit.

## What is actually happening

Three different identifiers exist and only one of them counts.

| Identifier | Where it comes from | Does the hook accept it? |
|---|---|---|
| `31456097-4efb-…` | the conversation id, what a person can actually see | **No** |
| `cli-442d97dc…` | minted per shell invocation when `--session` is omitted | **No** |
| `bm1-19d165ec…` | derived by `bm_fence_hook.session_label()` | **Yes, only this** |

The hook compares against the third. A person can only discover the third
**from a refusal they have already hit**, because nothing prints it before
that.

### Verified: omitting the flag does not help

```
claimed 'omit-session-probe' as lifecycle 32c531a9... (version 1, session cli-442d97dcd6f44116825d62ca4ec68708)
```

then asking the hook, as the real session, to write that same file:

```
"permissionDecision": "deny", ... "is owned by session cli-442d97dcd6f44116825d62ca4ec68708.
 This session is bm1-19d165ecdcbfb8ada77a15d6, so it is not the writer for that path."
```

**So in this environment there is no way to claim a fence from the command
line that the hook will accept as yours.** Both available inputs produce an
id it rejects.

### Verified: why the existing mitigation is inert

`_hook_derived_session_id()` already exists and its docstring says it was
earned by this same incident. It reads `BM_FENCE_SESSION_ID`, then
`CLAUDE_SESSION_ID`. Neither is set in the shell the CLI runs in:

```
BM_FENCE_SESSION_ID=[unset]
CLAUDE_SESSION_ID=[unset]
```

So it returns nothing, and the mitigation never fires. **A guard that depends
on an environment variable nobody sets is not a guard.** This is the same
class as the rule in the founder's own laws: a rule is not a control unless a
file enforces it.

### Verified: the label is a pure function of the harness id

This is what makes the fix possible.

```
derived from conversation uuid: bm1-19d165ecdcbfb8ada77a15d6
hook says this session is:      bm1-19d165ecdcbfb8ada77a15d6
```

`session_label(root, "31456097-4efb-4470-aa61-5ff5e8b9afa7")` returns exactly
the label the hook reports. The store does not need an environment variable.
It needs to convert the input a person already has.

## The current cost, per occurrence

Claim, edit, get refused, read the label out of the refusal, `adopt` with
`--adopt-from-live-session` (plain adopt is refused because the one-shot CLI
session still reads as live), `resume`, then re-claim. Six commands to undo
one. Four times in one night.

## The fix, designed and not yet landed

In `cmd_claim`, normalise the explicit session on the way in:

- Already a derived label (`bm1-…`) or the CLI's own minted id (`cli-…`):
  pass through untouched. Converting those would hash a hash.
- Anything else: run it through `session_label()` and store the result,
  printing one line saying the conversion happened. **A silent conversion is
  its own trap**, so it is announced.
- Derivation unavailable, or it raises: pass the input through unchanged.
  Never invent an id.

Two things this deliberately does NOT do. It does not refuse a mismatch,
because claiming on another session's behalf is a real workflow (an
orchestrator fencing for a worker) and the store cannot tell that apart from
a mistake. And it does not touch records already stored under raw ids.

### Landed, and what the first attempt got wrong

The first attempt converted EVERY session string that was not already a
label. That broke five CLI tests which legitimately pass short labels like
`S1`, because hashing those invents an identity nobody asked for. The rule
was narrowed to the canonical 8-4-4-4-12 harness shape, which is exactly what
a person copies when they reach for "my session id", and the narrowing has
its own test case. No test was weakened to get green.

LIVE PROOF, by the control rather than by the claim's own output:

```
claimed 'zero-tax-proof' ... (version 1, session bm1-19d165ecdcbfb8ada77a15d6)
```

after passing `--session 31456097-4efb-4470-aa61-5ff5e8b9afa7`. Feeding the
fence hook an Edit payload for that file as that session then returned an
ALLOW (empty output). The identical sequence was DENIED four times earlier
the same night.

Suite after the last edit: `python3 tools/test_bm_store.py`, `Ran 1029 tests`,
`OK`.

### Done-check when it lands

1. A unit test over the normalisation covering: raw id converted, `bm1-`
   untouched, `cli-` untouched, empty untouched, derivation returning nothing
   untouched, derivation raising untouched.
2. The live proof: claim with the conversation uuid, then feed the hook a
   payload for that file as that session, and get an **allow** rather than the
   deny quoted above.
3. `python3 tools/test_bm_store.py` and the full battery, both green.

## Related, same family, also open

`bm_store.py` mints a fresh session per shell invocation, so a fence claimed
from the command line without `--session` can never be parked by a later
command-line call. Way out is the same adopt-then-park sequence. Filed as
sprint one rank three.
