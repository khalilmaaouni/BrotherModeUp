Status: HISTORICAL record of one measurement, made 2026-08-07. It replaces
an UNVERIFIED claim with a negative result. No em or en dashes.

# M19: the write fence does not fire under Codex exec, measured

## What was claimed

docs/RUNTIMES.md carried, from 2026-08-05 to 2026-08-07, that the fence's
Codex half was UNVERIFIED: the matcher had been widened to Bash and proven
in process against a captured apply_patch payload, but no live Codex
session had ever been blocked.

## What was measured

On 2026-08-07, with credits available on the founder's Codex workspace, the
rehearsal ran for real in a throwaway tree with its own HOME and CODEX_HOME:

1. The store initialized under Codex conditions (root resolved via git,
   with -s workspace-write as docs/RUNTIMES.md already required).
2. A file was claimed by session-A through bm_store.py.
3. The fence hook was wired in ~/.codex/config.toml as an inline [hooks]
   table with a PreToolUse entry matching Edit|Write|MultiEdit|
   NotebookEdit|Bash and an absolute path to bm_fence_hook.py.
4. In process, fed a Codex-shaped apply_patch payload from a different
   session id, the hook returned permissionDecision deny and named the
   file, the owner, and the takeover command. That half works.
5. LIVE, codex exec was asked to rewrite the claimed file. IT SUCCEEDED.
   The file was overwritten. Repeated with
   --dangerously-bypass-hook-trust: it succeeded again.
6. The diagnostic that settles it: the hook command was replaced with a
   shell line that appends to a marker file. After a live codex exec run
   that wrote the file, THE MARKER DID NOT EXIST. The hook never executed.

Ruled out along the way: the config is syntactically accepted (codex exec
--strict-config, which errors on unrecognized fields, ran fine), the
project carries trust_level = "trusted", the claim was still active in the
store (bm_store.py dashboard showed it), and hook trust was additionally
bypassed by flag.

## What is true, therefore

Under OpenAI Codex CLI 0.146.0, in the non-interactive exec path,
BrotherMode is an instruction file plus a working command line. It is NOT
an enforcement layer. The one writer per file promise does not hold there.

## The rule

No page, register row or generated surface may claim fence enforcement on
any runtime other than Claude Code. Where a runtime is offered at all, the
page says what it gives (the law in writing, the store, the retrieval
commands) and what it does not (a hook that can refuse a write). A capability
whose enforcement half is unmeasured is not shipped as certified; a
capability measured NOT to work is written down as not working, which is
what this record does.

## What would flip it

An interactive Codex session (not exec) where the marker file appears, or a
future Codex version whose exec path runs PreToolUse hooks. Either one is a
re-measurement, not an argument.
