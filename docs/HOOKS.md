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

The supported way is `python3 scripts/install.py`, which writes this entry along with
the other four hooks and does not report success until the fence has executed once. See
docs/QUICKSTART.md step 3.

However you install it, check it with:

```
python3 scripts/doctor.py            # add --settings PATH for a non-default file
```

Doctor answers a narrower question than the installer's smoke test, and the narrow
question is the one that matters. The smoke test runs the hook from an empty directory,
where it takes its fail-open path, so it proves the hook executes. Doctor runs a
**blocked-write simulation**: a throwaway project under a temporary directory, its own
store, one file claimed under one session's label, then a write to that file requested
by a different session, judged by the exact command string in your settings file. A
healthy fence denies that, and then allows the same write when the owner asks, because a
hook that denies everything passes half the check and is a brick rather than a fence.
Each of `Edit`, `Write`, `MultiEdit` and `NotebookEdit` is simulated in its own real
input shape (the path key differs per tool), so a fence that gates one of them and not
the other three cannot report itself healthy. The owner half checks the hook's EXIT CODE
as well as its output, because a `PreToolUse` hook blocks a call by exiting non-zero,
not only by printing a deny. The temporary directory is deleted at the end; your
project, your store and your STATE.md are never touched.

Exit 1 names the specific defect: no `PreToolUse` entry naming `bm_fence_hook.py`, an
entry whose command points at a file that is not there, a matcher that leaves some write
tools ungated or is not a valid regular expression, a hook that refuses nothing, or a
hook that refuses everything (by deny JSON or by exit code). The matcher check treats
the matcher as a REGEX tested against each tool name, the way Claude Code does, and not
as a substring search: `Edit` is a substring of both `MultiEdit` and `NotebookEdit`, so
a substring test silently passed a matcher that left `Edit` ungated. Doctor still
cannot tell you whether Claude Code has LOADED that settings file: hooks are read at
session start, so a file corrected mid-session is live at the next one, not this one.

### By hand

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
   spans. On macOS and Windows that comparison folds CASE and UNICODE NORMALIZATION,
   because those filesystems do: `src/café.py` written NFC and the same name written NFD
   are one inode and two different strings, and before 2026-07-29 a claim in one spelling
   did not cover a write in the other, so a foreign session went straight through the
   default (non-strict) path. Linux is normalization sensitive, where the two really are
   different files, so nothing is folded there.
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
  guarantee this file cannot keep. The policy that goes with that limit is in the next
  section.
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

## The Bash boundary, and the policy that replaces a guarantee

Three strategies were on the table for shell writes. Only one of them is a mechanism,
and none of them is a guarantee, so all three are stated rather than the strongest one
being implied.

**1. Use Edit or Write for ordinary file changes.** These pass through the hook above.
This is a rule in the constitution (SKILL.md), not a mechanism: nothing stops a session
from reaching for Bash instead. It is first because it is the only one of the three that
makes the fence cover the common case.

**2. Use `scripts/bm_shell.py` for an unavoidable generated write.**

```
python3 scripts/bm_shell.py --record my-work --path src/generated.py \
  --session-id "$CLAUDE_SESSION_ID" -- 'python3 codegen.py > src/generated.py'
```

The wrapper makes the caller name the paths before the command runs, and hands each one
to `bm_fence_hook.decide()`, the imported function, so the wrapper and the hook cannot
drift. It refuses when a declared path is inside another session's fence, and, because a
deliberate shell write is a stronger act than an ordinary edit, it also refuses when the
path is inside nobody's fence (it checks in strict mode) and when the fence FAILS OPEN
at all. That last one is the deliberate inversion: the hook fails open because failing
closed would brick editing, and the wrapper fails closed because "could not be checked"
and "was approved" must not produce the same outcome for a command you invoked on
purpose.

A declared path that resolves OUTSIDE the project root is a third answer, not a pass.
The fence declines to judge anything outside the root on purpose (BrotherMode fences a
project, not the machine), so `decide()` returns nothing for it, which is the same value
as approval. The wrapper therefore refuses such a path by default and names it. Add
`--allow-outside-root` when the write really does belong outside the project: the command
runs and the summary reports those paths as NOT CHECKED rather than as claimed. Until
2026-07-29 the wrapper printed "N declared path(s) are inside this session's own claim"
for a path that was in no claim and not even in the project.

`--declare-none` runs a command that writes nothing. It is checked against a short,
explicit list of obvious write forms (`>`, `>>`, file-descriptor redirection such as `1>`
and `2>>`, `tee`, `sed -i`, `rm`, `mv`, `cp`, `patch`, a rewriting `git` subcommand, an
inline interpreter script, and a few more), and refuses if one matches. That list is not
a shell parser and the refusal says so. Passing it is not evidence that a command writes
nothing.

What the wrapper does NOT do: confine the command. It is a declaration channel, not a
sandbox. A command that writes a path the caller did not declare writes it, and nothing
here stops that.

**3. Everything else is outside mechanical protection, and the next best evidence is the
ledger.** A bare `Bash` write, a write from a subprocess the wrapper launched, a write by
any other program on the machine: none of these reach a PreToolUse hook, because Claude
Code only offers the hook the tool call it is about to make, and `Bash` carries a command
string rather than a path set. What remains in that case is not nothing: the store still
records who claimed what, `bm_store.py verify` still reports the state, and git still
shows the diff. It is a ledger and an audit trail, not a refusal. That is the exact
limit of the one-writer promise, and it is stated here, in SKILL.md, and in the doctor's
own output rather than left for someone to discover.

Closing that last gap would need a capability this project does not have: a PreToolUse
payload for `Bash` that names the files a command will touch (the harness does not
provide one), or an OS-level write mediator such as a sandbox profile or a FUSE layer,
both of which are far outside "Python 3.9, standard library only".

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
