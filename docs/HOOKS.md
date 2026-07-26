# Hooks: turning the fence from a ledger into a boundary

BrotherMode's headline promise is one writer per file. Until `tools/bm_fence_hook.py`
existed, that promise was a **coordination ledger**: `bm_store.py` recorded who claimed
what and refused an overlapping claim, but nothing stood between an agent and an actual
file write. The installed hooks were SessionStart, SessionEnd, Stop and PreCompact, and
none of them can refuse anything, because all of them run after or beside the write and
never in front of it.

So an agent could edit before claiming, claim an incomplete set of paths and edit the
rest, edit a path another record owned, or skip BrotherMode entirely. That is audit
finding 8, and it was confirmed by execution, not theory.

`tools/bm_fence_hook.py` is the missing gate. It is a **PreToolUse** hook: Claude Code
hands it the tool name and the tool's input before the tool runs, and it can deny the
call.

## The contract this hook implements

Read from <https://code.claude.com/docs/en/hooks> on **2026-07-27**. If that page moves,
this section is the thing to re-check first.

**Input**, delivered as one JSON object on stdin:

```json
{
  "session_id": "abc123",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "toolu_01ABC123..."
}
```

The four fields this hook reads are `session_id`, `cwd`, `tool_name` and `tool_input`.

**Output**, to deny a call: exit code 0, with exactly this object on stdout.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Database writes are not allowed"
  }
}
```

`permissionDecision` accepts `"allow"`, `"deny"`, `"ask"` and `"defer"`. This hook only
ever emits `"deny"`, and only ever on a real ownership conflict.

**Exit codes.** 0 means success, and stdout is parsed as JSON; no JSON on stdout means no
decision, and the normal permission flow applies. 2 is a blocking error: stdout is
ignored and stderr becomes the reason shown to the model. Any other code is a
non-blocking error, execution continues, and the first stderr line is surfaced as a hook
error notice.

This hook **always exits 0**. An allow is exit 0 with empty stdout. A deny is exit 0 with
the JSON object above. It never uses exit 2, because exit 2 means "the hook itself
failed", and a failure in this hook must never block a write (see Fail open, below).

## Installation

Add this to `.claude/settings.json` (project scope) or `~/.claude/settings.json` (user
scope). Use the absolute path to your checkout.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /absolute/path/to/BrotherModeUp/tools/bm_fence_hook.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

The `matcher` is a belt-and-braces duplicate of the check the hook does itself: the hook
re-reads `tool_name` and passes through anything that is not a file-writing tool, so a
looser matcher is safe, just slightly more wasteful.

Verify the installation without touching your real project:

```
cd /absolute/path/to/BrotherModeUp
python3 tools/bm_fence_hook.py whoami --session-id test-session
python3 tools/test_bm_fence_hook.py
```

## How a session proves who it is

This is audit finding **8B**, and it is the part where honesty matters more than
cleverness.

The defect: a record's `session_id` was a caller-supplied string, **and** it is printed in
plaintext into `STATE.md`, which every session reads. So the ownership guard compared a
public value against itself, and anyone could pass anyone else's session id.

The fix raises the bar without pretending to solve it:

1. On first use, a session gets a **secret token**: 32 random bytes, hex encoded, written
   to `.brothermode/fence/<slot>.token` with mode `0600` inside a `0700` directory. The
   slot filename is `sha256("bm-fence-slot-v1|" + session_id)`, so the file is found from
   the harness-supplied session id and a session id containing a path separator cannot
   escape the directory. The file is created with `O_CREAT|O_EXCL`, so two processes
   racing on the same session id cannot both write it.
2. The **public label** is a one-way hash of that token:
   `"bm1-" + sha256("bm-fence-label-v1|" + token)[:24]`.
3. `STATE.md` keeps showing the label, and only the label. The token is printed by no
   command in this file, including `whoami`.
4. Ownership is `record.session_id == label_derived_from_the_token_this_process_opened`.

The consequence that matters: **reading a label out of `STATE.md` and presenting it as
your own session buys nothing.** The hook never takes your word for which label is yours,
it computes it from a file you had to be able to open. Writing a stolen label into the
store as the owner of your own claim buys nothing either, for the same reason.

Claim under your own label like this:

```
python3 tools/bm_store.py claim my-work --lifetime ephemeral \
  --objective "..." --files src/thing.py \
  --session "$(python3 tools/bm_fence_hook.py session-label --session-id "$CLAUDE_SESSION_ID")"
```

`session-label` takes the session id from `--session-id`, then `BM_FENCE_SESSION_ID`, then
a hook payload on stdin. It refuses rather than inventing one, because a made up session
id would mint a token nobody could reproduce and quietly lock the session out of its own
records.

### The residual limitation, stated plainly

**Any process running as this user can read the token files.** They are `0600`, not
sealed. A hostile local process can list `.brothermode/fence/`, read any token, derive
that session's label, and impersonate it completely.

So what this actually defends against is:

- accidental collision (two sessions picking the same human-readable name),
- casual forging (an agent copying the owner label it read in `STATE.md` or a thread file
  and passing it as its own),
- a confused agent that believes it holds a fence it never claimed.

What it does **not** defend against is a determined local attacker, or any code running
under this user account that decides to read the token directory. Perfect unforgeability
is not achievable here: same machine, same user, no network, standard library only. There
is no secret this process can hold that another process under the same user cannot read.
Anything stronger needs an OS keychain, a separate uid, or a broker process, none of which
this project has.

Two smaller notes in the same spirit:

- The `0600` and `0700` modes are a real guarantee on POSIX. On Windows they are a
  courtesy: `os.chmod` there can only toggle the read-only bit, and the actual protection
  is whatever ACL the directory inherits. This mirrors `bm_store._chmod_best_effort`,
  which documents the same limit for the store file.
- The redactor that scrubs generated views does **not** recognize a 64 character hex
  string as a secret. That is precisely why the token is never printed anywhere rather
  than being printed and relied upon to be redacted.

## What the hook checks, exactly

1. Not a file-writing tool? Pass through, silently.
2. Pull every path out of `tool_input`, including nested per-edit paths, so a fenced file
   hidden in `edits[1]` is not missed. Bounded in depth and width, because a hostile
   payload must not hang the gate in front of every edit.
3. Resolve the project root with `bm_store.resolve_root`, imported, not reimplemented, so
   the hook and the store can never disagree about where the project is.
4. Canonicalize every target path: `realpath` (symlinks resolved, `..` collapsed,
   relative paths resolved against the payload `cwd`), then express it root-relative.
   Comparing unresolved strings is trivially bypassed by `..`, by a symlink, or by
   claiming from a different directory.
5. Compare with `bm_store.paths_overlap`, the same function the store uses to admit a
   claim, so a directory claim covers its children and a glob claim covers the files it
   spans.
6. Covered by an active record owned by someone else: **deny**, naming the record, its
   lifecycle uuid, the owning label, and the exact takeover command.
7. Covered by an active record this session owns: allow.
8. Covered by nothing: allow, unless strict mode is on.

### Taking a fence over

The deny message names the command. It is `bm_store.py`'s own documented door for a record
that is active under a different live session:

```
python3 tools/bm_store.py adopt <lifecycle_uuid> --version <N> \
  --session <your-label> --adopt-from-live-session
```

Then re-claim the paths you need. This is deliberately a two-step, explicit act. Taking a
fence is allowed; taking it silently is not.

### Strict mode (opt in)

`BM_FENCE_STRICT=1` additionally denies a write to any path inside the project that **no**
active record covers, turning "do not cross a fence" into "claim before you edit". Off by
default because it changes the working rhythm for everyone in the repo. It can only ever
tighten: it cannot override the fail-open rule below.

## Fail open, loudly

This hook sits in front of every edit the founder makes. A hook that failed closed on its
own bug would brick editing entirely. So a refusal must always come from a real ownership
conflict, and never from the hook being broken.

Every one of these allows the write and prints the reason to stderr:

- no BrotherMode project root found,
- no store file,
- store unreadable, busy, zero bytes, or corrupt,
- the store holds **no active claims at all**,
- the payload is missing, not JSON, or missing `session_id` or `tool_input`,
- a write tool arrived with no recognizable path,
- `bm_store.py` could not be imported,
- any unexpected exception at all (there is a blanket catch, and it is deliberate).

The stderr line always begins `bm_fence_hook: FAILING OPEN`, so a fence that has quietly
stopped enforcing is visible rather than silent.

## Known gaps

These are real, and listing them is better than implying coverage that does not exist.

- **Bash is not gated.** `rm`, `sed -i`, `>`, `tee`, `git checkout` and a hundred other
  shell forms write files, and no reliable parse of arbitrary shell exists. Gating
  `Edit|Write|MultiEdit|NotebookEdit` and pretending Bash was covered would be a
  guarantee this file cannot keep.
- **Unclaimed paths are allowed by default.** The hook enforces "not across someone
  else's fence", not "everything must be claimed", unless strict mode is on.
- **The hook cannot verify the store side.** An agent can still write any label into the
  store via `bm_store.py claim --session X`. It gains nothing at write time (see above),
  but it can occupy a name or a path set under a label that is not its own.
- **A filename containing a literal `*`, `?` or `[`** is read as a glob by
  `paths_overlap`, so its fence coverage is widened. It errs toward refusing rather than
  allowing, and such filenames are illegal on Windows anyway, but it is a real edge.
- **Per-process cost is roughly 45 ms**, almost entirely Python interpreter startup plus
  importing `bm_store.py`. The decision itself is about 0.5 ms. If that ever matters, the
  fix is a resident helper, not a thinner check.

## What a follow-up change to bm_store.py would need to add

`tools/bm_store.py` was **not** modified by this work: it is owned by another record, and
a needed store change is reported, never edited across the fence. The hook therefore works
entirely within today's schema, by reusing the existing free-text `records.session_id`
column to hold the derived label. That works, but it leaves three things a store change
could improve:

1. **A first-class `owner_token_hash` column on `records`**, written at claim time and
   never rendered into any view. Today the label doubles as both the human-visible handle
   and the ownership proof; splitting them would let the label be a short friendly name
   ("api-work-3") while the proof stays a full hash, instead of the label having to be a
   hash for the proof to work.
2. **Refusing a claim whose `--session` is a well-formed label the caller cannot prove.**
   The store currently accepts any string. If it verified the token at claim time, the
   forger could not even record a stolen label, which is the one thing the hook cannot
   prevent from where it sits.
3. **A shared `owns(record, path)` primitive exported from the store**, so the hook's
   check and the store's `_find_overlap` are literally the same function rather than two
   callers of `paths_overlap` that could drift.

None of the three is required for the hook to enforce the fence today.
