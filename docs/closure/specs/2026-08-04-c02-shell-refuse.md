# Implementation spec: c02-shell-refuse

Status: CURRENT. Produced 2026-08-04 by a read-only designer agent
against main at 5d9d0ea. The orchestrator applies these by hand; the
agent wrote nothing into the repository itself. Where the agent ran
probes, it did so in a throwaway /tmp copy with its own HOME.

## Summary

C-02 refuse-and-alert, designed and RUN. I copied tools/, scripts/, hooks/, brotherme/, commands/ to /tmp/c02probe/repo with its own HOME, applied every change there, ran the suites. Real repo and real ~/.brotherme untouched.

WHY IT WAS SILENT: .brothermode/store.sqlite3 is not a CLAIMED path, so bm_bash_audit.py never looked at it. Pre snapshots only fh.active_claims() rows passing os.path.isfile; post compares only those. Deleting the store passed through with zero findings and zero stderr, and the snapshot was tidied up afterwards.

(1) NON-SILENT. The snapshot gains a control block: store present, non-empty, still starting with b"SQLite format 3\x00", plus fence token filenames. Post reports every LOSS, one stderr sentence and one high-severity fence-control-loss alert each, before ownership is derived. Coarse on purpose: growth and ordinary mutation stay invisible, since a Bash call running bm_store.py is normal work. When the store is gone the row cannot be written and the hook says so. Also, _raise_breach_alert printed its sentence AFTER the database write, so an unrecordable detection was announced by nothing specific; it now announces first.

(2) REFUSE, ENFORCED ONLY. cmd_pre refuses first, before the consent gate (reads only the payload already handed to it, writes nothing). Rule A: the text contains .brothermode or store.sqlite3 (from bs constants) AND matches one of 19 destructive forms. Rule B: two whole-directory forms naming nothing (git clean -x, rm -r at . or *). refusal_for's docstring lists the misses and the over-refusals. Deny reasons LITERAL, no path, no command text, like _FAIL_REASONS. _enforced and deny_payload are local copies so a refusal survives bm_fence_hook.py failing; a test pins them.

(3) DOCS: exact prose for SECURITY.md (x2), KNOWN-LIMITS.md, HOOKS.md (x2, one now FALSE: "it never writes to stdout at all"), one SKILL.md sentence.

VERIFIED after the last edit: test_bm_bash_audit.py -> "Ran 29 tests in 3.267s / OK" (12 old green, 17 new); test_bm_fence_hook.py -> 62 OK; test_bm_consent.py -> 40, one error, a missing DIGEST.md my partial copy never had. Register chain end to end: with a proven DENY, rm -f .brothermode/store.sqlite3 under enforced is REFUSED (deny on stdout, store still present); under the default it runs and now prints "was present before this shell command and is gone after it" plus "could NOT be recorded as an alert". Before, nothing printed.

Apply in order; 3-5 chain, 14-16 chain.

## Risks

ENFORCED MODE ONLY; the default is unchanged and every new test asserts both directions. 1) `git clean -xfd` and `rm -rf .` or `*` are refused anywhere in a project; the escape is one command with BM_FENCE_MODE=advisory. 2) Over-refusal by design: any command naming .brothermode or store.sqlite3 next to a destructive form is refused, including `cat .brothermode/store.sqlite3 > /tmp/backup`. 3) The form words can match inside a quoted string or a commit message; refusing there is the intended direction but will surprise once.
STRUCTURAL. 4) The pre phase now reads stdin before the consent gate (it still writes nothing and opens no file; test_bm_consent.py's every-wired-command probe passed) and loads bm_store.py pre-consent when enforced, to read STORE_DIRNAME.
COUNTS AND DOCS. 5) This suite goes 12 to 29, so anything pinning a total test count needs the number the run prints. 6) SECURITY.md's 61,668-line claim is gated at 15 percent drift; tools are 66,795 today and this adds about 620, roughly 8.5 percent, inside the gate. 7) KNOWN-LIMITS.md and HOOKS.md are in ACTIVE_DOCS, so no em or en dashes; the prose has none.
NOT DONE ON PURPOSE. 8) A refusal raises no alert row: nothing changed, the harness records the denied call, and a store write in front of every refused Bash call would land on the pre-consent path. Cost: refusals are not queryable later. 9) A zero-claims project writes no snapshot, so control loss is undetected there; enforced mode still refuses.

## Uncertain, stated rather than implied

VERIFIED, not uncertain: every symbol named exists and ran. bs.STORE_DIRNAME (bm_store.py:77), STORE_FILENAME (:78), store_path (:383), now_iso (:250), redact_text (:887), mask_absolute_paths (:3126), Store.raise_alert (:10294); fh.enforced_mode (bm_fence_hook.py:465), deny_payload (:557), fence_dir (:156), TOKEN_SUFFIX (:141), token_path (:175), session_label (:275). Alert.ENUMS allows 'high' (brotherme/core/schema.py:328), category is free text, so fence-control-loss needs no schema change.
NOT RUN: only the three suites in the summary. test_all.py, test_bm.py, test_bm_docs.py and test_install.py were NOT run against these changes; run test_bm_docs.py first, for the dash rule and the doc-claim checks.
JUDGEMENT CALLS to override if you disagree: severity high not critical (critical needs a receipt to resolve; I matched the existing breach alert); refusing before the consent gate; no alert row for a refusal; bumping the snapshot schema 1 to 2 when nothing validates it.
NOT LOOKED AT: bm_shell.py needs no change as scoped, but its WRITE_SIGNALS and the new _DESTRUCTIVE_FORMS are near-duplicates and will drift; doctor.py could report unresolved fence-control-loss alerts; I did not read bm_sentinel.py.
STILL OPEN by the founder's decision: operating-system containment. A determined agent still disables the boundary by building the path at runtime, so C-02 should close as 'partly, refuse-and-alert only'.

## Changes, in the order the agent says to apply them

### 1. tools/bm_bash_audit.py

Anchor: module docstring, the numbered rules block, rules 1 and 2

Why: Rule 2 as written becomes false the moment the refusal exists. A file whose own docstring promises it never writes to stdout while writing a deny object there is the exact class of overclaim C-03 was opened for.

Current:

```
THE RULES THIS FILE OBEYS (same three bm_fence_hook.py states, plus one)
  1. FAIL OPEN, LOUDLY. Nothing here ever blocks a Bash call: both
     entrypoints below always return 0, whatever went wrong. A hook that
     failed closed on its own bug would brick every shell command the
     founder runs. Every failure path prints its reason to stderr, same
     policy as bm_fence_hook.py's own stated one.
  2. STDOUT IS RESERVED. A PreToolUse hook's stdout is the permission
     decision channel; this hook never has a decision to make, so it never
     writes to stdout at all, on either entrypoint, so a future reader
     cannot mistake output here for something Claude Code will parse.
     Every diagnostic, including the one required sentence naming a breach,
     goes to stderr.
```

Replacement:

```
THE RULES THIS FILE OBEYS (same three bm_fence_hook.py states, plus one)
  1. FAIL OPEN, LOUDLY, IN THE DEFAULT MODE. Both entrypoints always return
     0, whatever went wrong, and by default nothing here ever blocks a Bash
     call. A hook that failed closed on its own bug would brick every shell
     command the founder runs. Every failure path prints its reason to
     stderr, same policy as bm_fence_hook.py's own stated one.
     ONE EXCEPTION, added for C-02 (2026-08-03) and opt-in only: when
     BM_FENCE_MODE=enforced, the pre phase REFUSES a Bash command that
     matches an obvious destructive form aimed at BrotherMode's own
     enforcement state (the store file, the fence token directory). See
     refusal_for() for exactly what that can and cannot catch, in its own
     words. The default mode is byte-for-byte unchanged.
  2. STDOUT IS THE DECISION CHANNEL AND NOTHING ELSE. A PreToolUse hook's
     stdout is the permission decision channel. This hook writes to it in
     exactly one situation, the enforced-mode refusal in rule 1, and it
     writes the deny object and nothing else; the post phase never writes to
     stdout at all. Every diagnostic, including the sentences naming a
     breach or a lost store, goes to stderr.
```

### 2. tools/bm_bash_audit.py

Anchor: the import block, immediately after 'import os'

Why: refusal_for uses re.search. Standard library only, so the dependency surface is unchanged.

Current:

```
import hashlib
import io
import json
import os
import sys
import time
import uuid
```

Replacement:

```
import hashlib
import io
import json
import os
import re
import sys
import time
import uuid
```

### 3. tools/bm_bash_audit.py

Anchor: insert immediately BEFORE the '# Snapshot storage.' banner comment (block 1 of 3; changes 4 and 5 chain onto this one)

Why: The two primitives a refusal needs plus its literal copy tables. _enforced and deny_payload are local copies on purpose: bm_fence_hook.py being unimportable is one of the states enforcement exists for, and a refusal that depended on it would evaporate exactly then. Change 12 pins the copies to the originals.

Current:

```
# ---------------------------------------------------------------------------
# Snapshot storage. Lives beside the fence token directory, inside the same
```

Replacement:

```
# ---------------------------------------------------------------------------
# C-02: the REFUSE half. Enforced mode only.
# ---------------------------------------------------------------------------

def _enforced(env=None):
    """True when BM_FENCE_MODE is 'enforced'.

    Read here rather than through bm_fence_hook.enforced_mode() because this
    check has to work even when that module cannot be imported, which is one
    of the states enforcement exists for. tools/test_bm_bash_audit.py asserts
    this function and fh.enforced_mode() agree on every value they are given,
    so the duplication cannot drift."""
    env = os.environ if env is None else env
    return (env.get("BM_FENCE_MODE", "") or "").strip().lower() == "enforced"


def deny_payload(reason):
    """The PreToolUse deny object, the same four-key shape
    tools/bm_fence_hook.py's own deny_payload builds, restated here for the
    same reason _enforced is: a refusal must not depend on an import that may
    itself be the thing that failed. A test asserts the two are identical."""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


_DESTRUCTIVE_FORMS = (
    (r"(^|[^<>&])>{1,2}([^&]|$)", "output redirection (> or >>)"),
    (r"\btee\b", "tee"),
    (r"\bsed\b[^|;]*\s-i", "sed -i"),
    (r"\bperl\b[^|;]*\s-i", "perl -i"),
    (r"\brm\b", "rm"),
    (r"\bunlink\b", "unlink"),
    (r"\bshred\b", "shred"),
    (r"\btruncate\b", "truncate"),
    (r"\bdd\b", "dd"),
    (r"\bmv\b", "mv"),
    (r"\bcp\b", "cp"),
    (r"\bln\b", "ln"),
    (r"\bchmod\b", "chmod"),
    (r"\bchown\b", "chown"),
    (r"\bpatch\b", "patch"),
    (r"\bgit\s+(checkout|restore|reset|clean|stash|apply|rm)\b",
     "a git command that rewrites files"),
    (r"\b(python3?|node|ruby|perl)\b[^|;]*\s-(c|e)\b",
     "an inline interpreter script"),
    (r"\bfind\b[^|;]*\s-delete\b", "find -delete"),
    (r"\bmkdir\b", "mkdir"),
)

_TREE_WIDE_FORMS = (
    (r"\bgit\s+clean\b[^|;]*\s-{1,2}[A-Za-z]*[xX]",
     "git clean with -x, which deletes ignored files"),
    (r"\brm\b[^|;]*\s-[A-Za-z]*[rR][A-Za-z]*\s+(\.|\./|\*|\./\*)(\s|;|$)",
     "rm -r aimed at the whole working directory"),
)

_REFUSE_REASONS = {
    "store-destruction": (
        "the command matched a shell form that deletes or overwrites files, "
        "and it named BrotherMode's own enforcement state, which is the "
        "record of who owns which file",
        "make the change with Edit or Write so the fence can check it, or, "
        "if this store really has to be rebuilt, re-run that one command "
        "with BM_FENCE_MODE=advisory and say in the session that you did"),
    "tree-wide-destruction": (
        "the command matched a shell form that empties or rewrites the whole "
        "working directory, which would take BrotherMode's own enforcement "
        "state with it",
        "name the paths the command should touch instead of the whole "
        "directory, or re-run that one command with BM_FENCE_MODE=advisory "
        "and say in the session that you did"),
}


# ---------------------------------------------------------------------------
# Snapshot storage. Lives beside the fence token directory, inside the same
```

### 4. tools/bm_bash_audit.py

Anchor: insert immediately AFTER the closing brace of _REFUSE_REASONS added by change 3 (block 2 of 3)

Why: The detector itself, with the honest statement of coverage in its own docstring rather than only in a document a reader may never open. Names come from bs.STORE_DIRNAME / STORE_FILENAME so a rename cannot leave the matcher hunting a file that no longer exists.

Current:

```
        "directory, or re-run that one command with BM_FENCE_MODE=advisory "
        "and say in the session that you did"),
}
```

Replacement:

```
        "directory, or re-run that one command with BM_FENCE_MODE=advisory "
        "and say in the session that you did"),
}


def protected_names(bs):
    """The literal names of this project's own enforcement state on disk.
    Taken from bm_store's constants rather than retyped, so a rename there
    cannot leave this list matching a name that no longer exists."""
    store_dirname = bs.STORE_DIRNAME if bs is not None else ".brothermode"
    store_filename = bs.STORE_FILENAME if bs is not None else "store.sqlite3"
    return (store_dirname, store_filename)


def refusal_for(command_text, bs):
    """(code, labels, names) when this command text matches a destructive
    form aimed at BrotherMode's own enforcement state, else (None, [], []).

    WHAT THIS CAN AND CANNOT DO, STATED RATHER THAN IMPLIED. This is not a
    shell parser and cannot become one here, for the reason bm_fence_hook.py
    already gives for leaving Bash out of WRITE_TOOLS. It matches two things
    and only two:

      A. the command TEXT contains one of this project's own state names as
         a literal substring (bm_store.STORE_DIRNAME or STORE_FILENAME) AND
         it matches one of the destructive shell forms above.
      B. the command TEXT matches one of a very small set of forms that
         empty or rewrite the whole working directory without naming
         anything at all.

    It therefore catches every form the C-02 reproduction used (rm,
    redirection, sed -i, tee, an inline python3 -c, git checkout). It MISSES,
    by construction and not by oversight:
      - a name assembled at runtime ('d=.brother; rm -f ${d}mode/...'),
      - a name reached through a variable, an alias, a shell function, or a
        script FILE whose contents this hook never sees,
      - any program that removes the file without the name appearing in the
        command at all (an editor, a runtime reading the path from a config,
        a second process this command merely starts),
      - every destructive form not in the two lists above.
    And it OVER-refuses on purpose: a read-only command that merely mentions
    the directory next to any redirection ('ls .brothermode > /tmp/x') is
    refused too, and so is 'git clean -x' anywhere in the tree. Erring toward
    refusal is the deliberate choice, because the alternative inside a
    fail-closed mode is a false ALLOW on exactly the class of command this
    exists for."""
    if not isinstance(command_text, str) or not command_text.strip():
        return None, [], []
    names = [n for n in protected_names(bs) if n in command_text]
    if names:
        labels = [lab for pat, lab in _DESTRUCTIVE_FORMS
                  if re.search(pat, command_text)]
        if labels:
            return "store-destruction", labels, names
    labels = [lab for pat, lab in _TREE_WIDE_FORMS
              if re.search(pat, command_text)]
    if labels:
        return "tree-wide-destruction", labels, []
    return None, [], []
```

### 5. tools/bm_bash_audit.py

Anchor: insert immediately AFTER the final 'return None, [], []' of refusal_for added by change 4 (block 3 of 3)

Why: One funnel for the refusal, so the literal-copy rule is structural rather than a habit. Even the operator line refuses to echo the command, because a Bash command can carry a pasted secret and this line prints before anything has been verified.

Current:

```
    labels = [lab for pat, lab in _TREE_WIDE_FORMS
              if re.search(pat, command_text)]
    if labels:
        return "tree-wide-destruction", labels, []
    return None, [], []
```

Replacement:

```
    labels = [lab for pat, lab in _TREE_WIDE_FORMS
              if re.search(pat, command_text)]
    if labels:
        return "tree-wide-destruction", labels, []
    return None, [], []


def _refuse(code, labels, names):
    """Emit the refusal: one operator sentence on stderr, one deny object on
    stdout. The deny REASON is LITERAL, drawn from _REFUSE_REASONS, and names
    no path and no payload content, matching the rule bm_fence_hook.py's
    _FAIL_REASONS already follows: that string is read by the model and lands
    in a transcript. The stderr line is allowed to be specific, and is, but
    even it never repeats the command text: it names only the FORM LABELS and
    the PROTECTED NAMES, both of which are this file's own constants."""
    summary, remedy = _REFUSE_REASONS[code]
    detail = " and ".join(labels) or "a destructive shell form"
    named = ", ".join(names)
    _warn("bm_bash_audit: REFUSING this Bash call. BM_FENCE_MODE=enforced, "
          "and the command matched %s%s. Nothing was run and nothing was "
          "changed. The command text is not repeated here."
          % (detail, (" while naming %s" % named) if named else ""))
    try:
        sys.stdout.write(json.dumps(deny_payload(
            "BrotherMode is in enforced mode and refused this shell command "
            "because %s. To fix it, %s. To go back to warning only, set "
            "BM_FENCE_MODE=advisory." % (summary, remedy))))
        sys.stdout.flush()
    except Exception as e:
        _warn("bm_bash_audit: the refusal above could not be written to "
              "stdout (%s: %s), so Claude Code will not see it; treat the "
              "line above as the only record." % (type(e).__name__, e))
```

### 6. tools/bm_bash_audit.py

Anchor: insert immediately BEFORE 'def _remove_snapshot_best_effort(path):'

Why: The ALERT half, the code that ends the measured silence: the store and the fence tokens were the one part of the tree the detector never looked at, precisely because they are not claimed paths. severity stays 'high' and actor stays 'bm_bash_audit', matching the existing breach alert, so nothing downstream has to learn a new shape.

Current:

```
def _remove_snapshot_best_effort(path):
```

Replacement:

```
#: The first sixteen bytes of every SQLite database file. Read from the
#: on-disk format documentation and confirmed against this project's own
#: store; used only to notice that a file that WAS a database no longer is.
SQLITE_MAGIC = b"SQLite format 3\x00"

ALERT_CATEGORY_CONTROL = "fence-control-loss"

#: The control findings, keyed by code, each a LITERAL sentence. C-02: a
#: shell command that destroys the enforcement state used to produce no
#: output at all, because the store is not itself a claimed path and nothing
#: in this file looked at it.
CONTROL_FINDINGS = {
    "store-removed": (
        "the BrotherMode store file was present before this shell command "
        "and is gone after it"),
    "store-emptied": (
        "the BrotherMode store file held a non-empty database before this "
        "shell command and is zero bytes after it"),
    "store-overwritten": (
        "the BrotherMode store file no longer begins with the SQLite file "
        "header, so what is there now is not a database"),
    "fence-dir-removed": (
        "the fence directory that holds session ownership tokens was present "
        "before this shell command and is gone after it"),
    "fence-token-removed": (
        "one or more session ownership tokens that existed before this shell "
        "command are gone after it"),
}


def _control_state(root, bs, fh):
    """A deliberately COARSE picture of BrotherMode's own enforcement state.

    Coarse on purpose. The store legitimately CHANGES during a Bash call (any
    bm_store.py command run through a shell writes to it), so a content hash
    here would alarm on ordinary work and be trained away within a day. This
    records only enough to notice the three destructive outcomes: the store
    gone, emptied, or replaced by something that is not a database, plus the
    fence token directory or individual tokens disappearing. Never raises: an
    unreadable state is recorded as absent, not as a crash in front of a Bash
    call."""
    state = {"store_present": False, "store_size": 0, "store_header_ok": False,
             "fence_dir_present": False, "token_files": []}
    try:
        p = bs.store_path(root)
        if os.path.isfile(p):
            state["store_present"] = True
            state["store_size"] = os.stat(p).st_size
            with io.open(p, "rb") as f:
                state["store_header_ok"] = (
                    f.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC)
    except OSError:
        pass
    try:
        d = fh.fence_dir(root)
        if os.path.isdir(d):
            state["fence_dir_present"] = True
            state["token_files"] = sorted(
                n for n in os.listdir(d) if n.endswith(fh.TOKEN_SUFFIX))
    except OSError:
        pass
    return state


def _control_findings(root, bs, fh, before):
    """Codes for every destructive change between the pre-phase state and
    now. Growth, ordinary mutation, and NEW token files are invisible here on
    purpose: this reports loss, not change."""
    if not isinstance(before, dict):
        return []
    now = _control_state(root, bs, fh)
    out = []
    if before.get("store_present"):
        if not now["store_present"]:
            out.append("store-removed")
        elif before.get("store_size", 0) > 0 and now["store_size"] == 0:
            out.append("store-emptied")
        elif before.get("store_header_ok") and not now["store_header_ok"]:
            out.append("store-overwritten")
    if before.get("fence_dir_present") and not now["fence_dir_present"]:
        out.append("fence-dir-removed")
    elif before.get("fence_dir_present"):
        gone = [t for t in (before.get("token_files") or [])
                if t not in (now["token_files"] or [])]
        if gone:
            out.append("fence-token-removed")
    return out


def _raise_control_alert(bs, root, code, offending_session_id):
    """One alert row for one control finding. Same shape, severity and actor
    as _raise_breach_alert, different category, and a message built entirely
    from CONTROL_FINDINGS, so no founder text and no absolute path can reach
    it at all."""
    alert = {
        "alert_id": uuid.uuid4().hex,
        "severity": ALERT_SEVERITY,
        "category": ALERT_CATEGORY_CONTROL,
        "message": (
            "a Bash command run by session %s changed BrotherMode's own "
            "enforcement state: %s. Enforcement state is not a fenced file, "
            "so no hook refused this."
            % (offending_session_id, CONTROL_FINDINGS[code])),
        "why_it_matters": (
            "the fence decides who may write which file by reading this "
            "state, so a shell command that removes or empties it turns "
            "every later refusal into an allow, silently, and that is the "
            "defect this check exists for."),
        "recommended_action": (
            "restore the store and the fence directory (git, or an autosave "
            "snapshot through `python3 tools/bm_autosave.py recover`), then "
            "run `python3 scripts/doctor.py` and confirm the claims you "
            "expect are still there."),
        "requires_human": True,
        "created_at": bs.now_iso(),
        "resolved_at": None,
    }
    actor = {
        "actor_type": "hook",
        "actor_name": "bm_bash_audit",
        "session_id": offending_session_id,
    }
    store = bs.Store(root, create=False)
    try:
        store.raise_alert(alert, ALERT_PROJECT_ID, actor)
    finally:
        store.close()


def _remove_snapshot_best_effort(path):
```

### 7. tools/bm_bash_audit.py

Anchor: inside _run_pre, the snapshot dict literal

Why: Records the before picture in the same file the pair already writes and reaps, so there is no second lifetime to manage. Nothing validates the schema number, so the bump is honest bookkeeping and a schema-1 leftover degrades to no finding rather than a crash.

Current:

```
    snapshot = {
        "schema": 1,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "root": root,
        "created_at": bs.now_iso(),
        "entries": entries,
    }
```

Replacement:

```
    snapshot = {
        "schema": 2,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "root": root,
        "created_at": bs.now_iso(),
        "entries": entries,
        # C-02: the enforcement state itself, which is not a claimed path and
        # so was never looked at before. schema goes 1 to 2 for this; a
        # schema-1 snapshot written by an older copy simply carries no
        # "control" key, and _control_findings returns nothing for it.
        "control": _control_state(root, bs, fh),
    }
```

### 8. tools/bm_bash_audit.py

Anchor: the whole head of cmd_pre, down to and including the '_run_pre(payload)' line

Why: The refusal must precede the consent gate or a machine that never finished setup gets no protection, and must precede the snapshot or a refused call leaves an orphan. _read_stdin_json moves above the gate: stdin is data the harness already pushed, not a disk read, so the pre-consent property holds. test_bm_consent.py's every-wired-command probe still passes.

Current:

```
def cmd_pre(argv):
    if not _consented():
        _warn(_CONSENT_REQUIRED_LINE)
        return 0
    payload, err = _read_stdin_json()
    try:
        if err is not None:
            raise _FailOpen(err)
        _run_pre(payload)
```

Replacement:

```
def cmd_pre(argv):
    # C-02, the REFUSE half, and it runs FIRST, before the consent gate, on
    # purpose. It reads nothing but the payload the harness already handed
    # us, opens no file, and writes nothing, so it does not weaken rule 4
    # above (pre-consent, nothing is read from disk and nothing is written).
    # And an operator who set BM_FENCE_MODE=enforced asked to be refused, not
    # to be refused once setup happens to have been run.
    payload, err = _read_stdin_json()
    if err is None and _enforced() and isinstance(payload, dict):
        try:
            tool_input = payload.get("tool_input")
            command_text = (tool_input or {}).get("command") \
                if isinstance(tool_input, dict) else None
            code, labels, names = refusal_for(
                command_text, _load_store_module())
            if code is not None:
                _refuse(code, labels, names)
                return 0
        except Exception as e:
            # Enforced mode inverts the usual judgement, the same way
            # bm_fence_hook.py's blanket catch does: somebody who asked for
            # fail-closed would rather be stopped by a bug here than have a
            # store-destroying command waved through unexamined.
            _refuse("store-destruction",
                    ["an internal error in the refusal check (%s)"
                     % type(e).__name__], [])
            return 0
    if not _consented():
        _warn(_CONSENT_REQUIRED_LINE)
        return 0
    try:
        if err is not None:
            raise _FailOpen(err)
        _run_pre(payload)
```

### 9. tools/bm_bash_audit.py

Anchor: the first two lines of the body of _raise_breach_alert

Why: Second half of non-silent. A detection whose only announcement came after a successful database write was silent in exactly the scenario C-02 describes, where the database is what the attacker removed. The existing 'alert was raised' sentence stays and stays true, so test_a is untouched.

Current:

```
    message = _breach_message(bs, rel_path, entry, offending_session_id)
    alert = {
```

Replacement:

```
    # C-02: SAY IT FIRST, then try to record it. This line used to be printed
    # only AFTER store.raise_alert returned, so a detection that could not be
    # recorded (a store that has just been deleted, a disk that is full) was
    # announced by nothing at all except a generic FAILING OPEN line further
    # up the stack. Detection must be audible even when recording fails.
    _warn("bm_bash_audit: DETECTED a Bash write across a fence: %s changed "
          "and the session that ran the command does not own that fence."
          % bs.mask_absolute_paths(bs.redact_text(rel_path)))
    message = _breach_message(bs, rel_path, entry, offending_session_id)
    alert = {
```

### 10. tools/bm_bash_audit.py

Anchor: inside _run_post, between _load_snapshot and the session_label derivation

Why: Placed before session_label so a destroyed store is reported even when identity derivation then fails, and wrapped so a failed alert write degrades to a printed line instead of an exception that swallows the finding into a generic FAILING OPEN. Snapshot lifetime is untouched, so A3 (remove only after a completed comparison) still holds.

Current:

```
    spath = snapshot_path(root, bs, session_id, tool_use_id)
    snapshot = _load_snapshot(spath)

    try:
        my_label = fh.session_label(root, session_id)
```

Replacement:

```
    spath = snapshot_path(root, bs, session_id, tool_use_id)
    snapshot = _load_snapshot(spath)

    # C-02: the enforcement state is checked FIRST, before ownership is even
    # derived, because a command that destroyed the store is exactly the
    # command after which deriving anything from the store is pointless, and
    # because this half must be audible whatever else fails below.
    for code in _control_findings(root, bs, fh, snapshot.get("control")):
        _warn("bm_bash_audit: DETECTED a change to BrotherMode's own "
              "enforcement state during a Bash call: %s. Enforcement state "
              "is not a fenced file, so no hook refused this. Set "
              "BM_FENCE_MODE=enforced to have the obvious destructive shell "
              "forms refused before they run." % CONTROL_FINDINGS[code])
        if os.path.isfile(bs.store_path(root)):
            try:
                _raise_control_alert(bs, root, code, session_id)
                _warn("bm_bash_audit: a high-severity fence-control-loss "
                      "alert was raised and needs a human.")
            except Exception as e:
                _warn("bm_bash_audit: that finding could NOT be recorded as "
                      "an alert (%s: %s); the line above is the only record."
                      % (type(e).__name__, e))
        else:
            _warn("bm_bash_audit: that finding could NOT be recorded as an "
                  "alert, because the store that would hold it is the thing "
                  "that went missing; the line above is the only record. "
                  "Restore it from git or from an autosave snapshot, then "
                  "run `python3 scripts/doctor.py`.")

    try:
        my_label = fh.session_label(root, session_id)
```

### 11. tools/test_bm_bash_audit.py

Anchor: module docstring, after the (e) item of the D-4 list

Why: This file's docstring is its own index; two new classes not named there would be invisible to the next reader.

Current:

```
  (e) a corrupt or a missing snapshot file fails open, prints a reason,
      exits 0, and raises no alert.
"""
```

Replacement:

```
  (e) a corrupt or a missing snapshot file fails open, prints a reason,
      exits 0, and raises no alert.

C-02 (2026-08-03) adds two classes below D-4's spine:
  EnforcedModeRefusesStoreDestruction, one test per mutation form the
  closure register's reproduction used, each asserting BOTH directions on
  that form (refused under BM_FENCE_MODE=enforced, allowed under the
  default), and ControlStateLossIsDetected, which covers the silence itself:
  a shell command that removes the store or a session token used to produce
  no output and no alert row at all, because the store is not a claimed path
  and nothing in the hook looked at it.
"""
```

### 12. tools/test_bm_bash_audit.py

Anchor: BashAuditBase.setUp, the env-scrub loop

Why: Without this, a developer who exported BM_FENCE_MODE=enforced in their own shell would flip the default-mode half of every both-ways test, and the suite would pass or fail on the operator's environment rather than on the code.

Current:

```
        for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID"):
            os.environ.pop(k, None)
```

Replacement:

```
        for k in ("BROTHERMODE_ROOT", "BM_FENCE_STRICT", "BM_FENCE_SESSION_ID",
                  "BM_FENCE_MODE"):
            os.environ.pop(k, None)
```

### 13. tools/test_bm_bash_audit.py

Anchor: BashAuditBase.run_hook signature and payload construction

Why: Both new parameters default to today's behaviour, so all twelve existing tests are byte-identical in effect. The refusal is a function of the command text, which this fixture previously hardcoded.

Current:

```
    def run_hook(self, phase, session_id, tool_use_id="toolu_01TEST",
                consented=True):
        """Run bm_bash_audit.py exactly as Claude Code would: a bare
        subcommand (pre or post) with a JSON hook payload on stdin."""
        payload = json.dumps({
            "session_id": session_id,
            "transcript_path": os.path.join(self.root, "transcript.jsonl"),
            "cwd": self.root,
            "permission_mode": "default",
            "hook_event_name": "PreToolUse" if phase == "pre" else "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_use_id": tool_use_id,
        })
        env = dict(os.environ)
        if not consented:
```

Replacement:

```
    def run_hook(self, phase, session_id, tool_use_id="toolu_01TEST",
                consented=True, command="echo hi", env_extra=None):
        """Run bm_bash_audit.py exactly as Claude Code would: a bare
        subcommand (pre or post) with a JSON hook payload on stdin.

        `command` is the shell command the payload carries, which every test
        before C-02 left at the harmless default; `env_extra` sets variables
        for that one run (BM_FENCE_MODE, for the enforced-mode half)."""
        payload = json.dumps({
            "session_id": session_id,
            "transcript_path": os.path.join(self.root, "transcript.jsonl"),
            "cwd": self.root,
            "permission_mode": "default",
            "hook_event_name": "PreToolUse" if phase == "pre" else "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_use_id": tool_use_id,
        })
        env = dict(os.environ)
        env.update(env_extra or {})
        if not consented:
```

### 14. tools/test_bm_bash_audit.py

Anchor: insert immediately BEFORE the '# A2 (loop6 refuter finding)' banner comment (block 1 of 3; changes 15 and 16 chain onto this)

Why: One test per detection form the register names, each asserting refuse-under-enforced AND allow-under-default, in the shape EnforcedModeFailsClosed already established. The snapshot assertion catches a refusal that left an orphan behind.

Current:

```
# ---------------------------------------------------------------------------
# A2 (loop6 refuter finding): nothing tied this hook to its OWN wiring.
```

Replacement:

```
# ---------------------------------------------------------------------------
# C-02 (2026-08-03), the REFUSE half. One test per mutation form the closure
# register's reproduction used, each asserting BOTH directions on that form:
# refused under BM_FENCE_MODE=enforced, allowed under the default. The second
# half is the important one, exactly as in test_bm_fence_hook.py's
# EnforcedModeFailsClosed: it is what stops a later change from quietly
# making fail-closed the default for people who never asked for it.
# ---------------------------------------------------------------------------

class EnforcedModeRefusesStoreDestruction(BashAuditBase):

    def _both_ways(self, command, slug):
        """Refused under enforced, allowed by default, on ONE command."""
        owner = self.label(self.OWNER)
        self.claim("mine-" + slug, ["src/mine.txt"], owner)

        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_enf_" + slug,
                          command=command,
                          env_extra={"BM_FENCE_MODE": "enforced"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip(),
                        "enforced mode wrote no decision to stdout, so "
                        "Claude Code would have run the command")
        decision = json.loads(r.stdout)
        out = decision["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        reason = out["permissionDecisionReason"]
        self.assertIn("enforced mode", reason)
        self.assertIn("REFUSING", r.stderr)
        # No snapshot was written for a call that will never run.
        self.assertFalse(
            os.path.isfile(self.snapshot_path(self.OTHER,
                                              "toolu_enf_" + slug)),
            "a refused Bash call still left a snapshot behind")

        r2 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_def_" + slug,
                           command=command)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "",
                         "the DEFAULT mode refused a Bash call; fail-closed "
                         "must stay opt-in")
        self.assertNotIn("REFUSING", r2.stderr)

    def test_rm_of_the_store_is_refused_when_enforced(self):
        """The closure register's own reproduction command, verbatim."""
        self._both_ways("rm -f .brothermode/store.sqlite3", "rm")

    def test_redirection_onto_the_store_is_refused_when_enforced(self):
        self._both_ways(": > .brothermode/store.sqlite3", "redir")

    def test_sed_i_on_the_store_is_refused_when_enforced(self):
        self._both_ways("sed -i.bak -e 's/a/b/' .brothermode/store.sqlite3",
                        "sed")

    def test_tee_onto_the_store_is_refused_when_enforced(self):
        self._both_ways("echo x | tee .brothermode/store.sqlite3", "tee")

    def test_inline_python_removing_the_store_is_refused_when_enforced(self):
        self._both_ways(
            "python3 -c \"import os; os.remove('.brothermode/store.sqlite3')\"",
            "python")

    def test_git_checkout_of_the_store_is_refused_when_enforced(self):
        self._both_ways("git checkout -- .brothermode/store.sqlite3", "git")

    def test_removing_the_fence_directory_is_refused_when_enforced(self):
        """Not the store, the other half of the enforcement state: the tokens
        that decide which session owns which record."""
        self._both_ways("rm -rf .brothermode/fence", "fencedir")

    def test_a_tree_wide_wipe_that_names_nothing_is_refused_when_enforced(self):
        """`git clean -xfd` names no BrotherMode path at all and deletes it
        anyway, because .brothermode is excluded from git. It is caught by
        the second, deliberately tiny rule rather than by name."""
        self._both_ways("git clean -xfd", "gitclean")


# ---------------------------------------------------------------------------
# A2 (loop6 refuter finding): nothing tied this hook to its OWN wiring.
```

### 15. tools/test_bm_bash_audit.py

Anchor: insert immediately AFTER the git-clean test added by change 14 (block 2 of 3)

Why: The four properties that keep the refusal honest: it does not stop ordinary work, its reason is literal, a typo does not refuse, and the two local copies cannot drift. The last test pins the STATED miss so a future widening must update the documentation rather than quietly outgrow it.

Current:

```
        self._both_ways("git clean -xfd", "gitclean")
```

Replacement:

```
        self._both_ways("git clean -xfd", "gitclean")

    def test_ordinary_commands_are_untouched_even_when_enforced(self):
        """The false-positive guard. Enforcement that stopped ordinary work
        would be removed within a day, so the refusal has to be narrow enough
        to live with: reading the directory, querying the store, and editing
        a source file all still run."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        for i, command in enumerate((
                "echo hi",
                "git status --short",
                "ls -la .brothermode",
                "python3 tools/bm_store.py verify",
                "rm -rf build",
                "make test 2>&1 | tail -5",
                "git checkout -- src/other.py")):
            r = self.run_hook("pre", self.OTHER,
                              tool_use_id="toolu_benign_%d" % i,
                              command=command,
                              env_extra={"BM_FENCE_MODE": "enforced"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "",
                             "enforced mode refused %r, which writes nothing "
                             "BrotherMode owns" % command)

    def test_the_deny_reason_names_no_path_and_no_command_text(self):
        """Same rule bm_fence_hook.py's _FAIL_REASONS follows: the operator
        gets the detail on stderr, the model gets a category and a remedy.
        Nothing has been verified at the moment this is produced, so nothing
        justifies quoting a path or the command."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        command = "rm -f .brothermode/store.sqlite3 && echo SECRETMARKER"
        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_literal",
                          command=command,
                          env_extra={"BM_FENCE_MODE": "enforced"})
        reason = json.loads(r.stdout)["hookSpecificOutput"][
            "permissionDecisionReason"]
        self.assertNotIn("SECRETMARKER", reason)
        self.assertNotIn(".brothermode/store.sqlite3", reason)
        self.assertNotIn(self.root, reason)
        self.assertNotIn("SECRETMARKER", r.stderr,
                         "even the operator line must not repeat the command")

    def test_an_unrecognized_mode_value_does_not_refuse(self):
        """Byte-identical to fence_mode's rule: a typo runs advisory rather
        than refusing over a missing letter."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        r = self.run_hook("pre", self.OTHER, tool_use_id="toolu_typo",
                          command="rm -f .brothermode/store.sqlite3",
                          env_extra={"BM_FENCE_MODE": "enfoced"})
        self.assertEqual(r.stdout, "")

    def test_this_files_two_borrowed_primitives_match_the_fence_hooks(self):
        """`_enforced` and `deny_payload` are restated here rather than
        imported, so that a refusal still works when bm_fence_hook.py is the
        thing that failed. This is the test that stops the copies drifting."""
        for value in ("enforced", "ENFORCED", " enforced ", "advisory",
                      "enfoced", "", "1"):
            self.assertEqual(ba._enforced({"BM_FENCE_MODE": value}),
                             fh.enforced_mode({"BM_FENCE_MODE": value}),
                             "the two readings of BM_FENCE_MODE=%r "
                             "disagree" % value)
        self.assertEqual(ba._enforced({}), fh.enforced_mode({}))
        self.assertEqual(ba.deny_payload("because"),
                         fh.deny_payload("because"))

    def test_the_refusal_check_is_documented_as_partial(self):
        """The register's own wording: this cannot pretend to catch
        everything. A name built at runtime is the honest miss, asserted here
        so nobody later reads the feature as complete containment."""
        code, _labels, _names = ba.refusal_for(
            "d=.brother; rm -f ${d}mode/store.sqlite3", bs)
        self.assertEqual(code, "store-destruction",
                         "the literal store filename is still in that text")
        code2, _l2, _n2 = ba.refusal_for("d=.brother; rm -f ${d}mode/s*", bs)
        self.assertIsNone(code2,
                          "a name assembled at runtime is a STATED miss; if "
                          "this ever starts matching, update refusal_for's "
                          "docstring and docs/KNOWN-LIMITS.md rather than "
                          "deleting this test")
```

### 16. tools/test_bm_bash_audit.py

Anchor: insert immediately AFTER the runtime-miss test added by change 15 (block 3 of 3)

Why: The alert-row test the brief asks for, plus its two boundaries: the case where the row is impossible (so the stderr line is the whole record), and the case where nothing should fire. The last test pins the announce-before-record ordering, which a later refactor would otherwise silently reverse.

Current:

```
                          "docstring and docs/KNOWN-LIMITS.md rather than "
                          "deleting this test")
```

Replacement:

```
                          "docstring and docs/KNOWN-LIMITS.md rather than "
                          "deleting this test")


# ---------------------------------------------------------------------------
# C-02, the ALERT half: a shell command that destroys the enforcement state
# itself used to produce no output and no row at all, because the store is
# not a claimed path and nothing here looked at it.
# ---------------------------------------------------------------------------

class ControlStateLossIsDetected(BashAuditBase):

    def test_a_removed_session_token_raises_an_alert_row(self):
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        token = fh.token_path(self.root, self.OWNER)
        self.assertTrue(os.path.isfile(token), "no owner token to remove")

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_token")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        os.remove(token)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_token")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "", "the post phase must never print to "
                                        "stdout")
        self.assertIn("DETECTED a change to BrotherMode's own enforcement "
                      "state", r2.stderr)
        self.assertIn("fence-control-loss alert was raised", r2.stderr)

        rows = self.alerts(raw=True)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["category"], "fence-control-loss")
        self.assertEqual(rows[0]["severity"], "high")
        self.assertTrue(rows[0]["requires_human"])
        self.assertNotIn(self.root, rows[0]["message"])

        raised = [e for e in self.bash_audit_attribution()
                  if e.get("event_type") == "alert.raised"]
        self.assertEqual(len(raised), 1, raised)
        self.assertEqual(raised[0]["actor_name"], "bm_bash_audit")

    def test_a_deleted_store_is_still_announced_even_though_unrecordable(self):
        """The C-02 reproduction's first command. The alert row cannot exist,
        because the thing that would hold it is what was destroyed, so the
        stderr line is the whole record and it has to be there."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_delstore")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        for suffix in ("", "-wal", "-shm"):
            p = bs.store_path(self.root) + suffix
            if os.path.exists(p):
                os.remove(p)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_delstore")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("is gone after it", r2.stderr)
        self.assertIn("could NOT be recorded as an alert", r2.stderr)

    def test_ordinary_store_growth_between_the_phases_is_not_an_alert(self):
        """The coarseness is deliberate: a Bash call that runs bm_store.py is
        ordinary work, and a check that alarmed on it would be turned off."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)

        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_growth")
        self.assertEqual(r1.returncode, 0, r1.stderr)

        self.claim("second", ["src/other.py"], owner)

        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_growth")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertNotIn("enforcement state", r2.stderr)
        self.assertEqual(self.alerts(), [])

    def test_a_breach_is_announced_before_it_is_recorded(self):
        """Ordering, not decoration: the detection sentence used to be
        printed only after the alert row was written, so a detection that
        could not be recorded was announced by nothing specific at all."""
        owner = self.label(self.OWNER)
        self.claim("mine", ["src/mine.txt"], owner)
        r1 = self.run_hook("pre", self.OTHER, tool_use_id="toolu_order")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.write_file("src/mine.txt", "tampered\n")
        r2 = self.run_hook("post", self.OTHER, tool_use_id="toolu_order")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        detected = r2.stderr.index("DETECTED a Bash write across a fence")
        recorded = r2.stderr.index("fence-breach alert was raised")
        self.assertLess(detected, recorded)
```

### 17. SECURITY.md

Anchor: end of the bullet 'The same kind of cross-fence write, but through Bash.', the line naming docs/HOOKS.md's install section

Why: States the new capability and, in the same breath, every way around it. The register's acceptance is 'a recorded refusal or a recorded alert', not containment, and this paragraph must not read as more than that.

Current:

```
  docs/HOOKS.md's "Installing the Bash audit hook").
```

Replacement:

```
  docs/HOOKS.md's "Installing the Bash audit hook").
  EXTENDED 2026-08-03 (closure item C-02). Two things above were incomplete
  until that date. FIRST, a shell command that destroyed BrotherMode's OWN
  enforcement state produced no alert and no stderr line at all. The measured
  case was `rm -f .brothermode/store.sqlite3`: the store is not itself a
  claimed path, so nothing in the detection pair ever looked at it, and with
  the store gone a write the fence had just refused became an allow. That is
  now DETECTED on the same pair. The pre phase records whether the store
  exists, is non-empty and still begins with the SQLite file header, and
  which session tokens exist; the post phase reports every one of those that
  was lost, on stderr and as a high-severity `fence-control-loss` alert row.
  Growth and ordinary mutation are ignored on purpose, because a shell call
  that runs `bm_store.py` is normal work. When the store itself is what went
  missing the row cannot be written, and the hook says exactly that instead
  of falling silent.
  SECOND, and only if you opt in with `BM_FENCE_MODE=enforced`, that command
  is now REFUSED before it runs. Read what that refusal is, and is not,
  before relying on it: it is a literal match, a small list of destructive
  shell forms combined with the literal names `.brothermode` and
  `store.sqlite3`, plus two forms that wipe a whole directory without naming
  anything (`git clean` with `-x`, and `rm -r` aimed at `.` or `*`). It is
  not a shell parser and will not become one here. A name assembled at
  runtime, held in a variable, or sitting inside a script file the hook never
  reads is NOT caught, and neither is any program that deletes the file
  without the name appearing in the command. It also over-refuses on purpose:
  a read-only command that merely mentions the directory next to a
  redirection is refused too. What enforced mode adds beyond the refusal is
  the aftermath: if the store does go missing by a route the refusal misses,
  the fence hook in that same mode then DENIES rather than allowing (C-01),
  so the one-command bypass needs both halves to fail rather than one.
```

### 18. SECURITY.md

Anchor: the 'Attacks this design explicitly does NOT answer' list, immediately before the supply-chain bullet

Why: The threat-model section listed what the design answers and never named the biggest thing it does not. With this bullet, the refuse-and-alert half cannot be mistaken for containment by a reader who only reads this page.

Current:

```
- **A supply-chain compromise of Python or git themselves.** This project
```

Replacement:

```
- **A shell command that writes or deletes files, in the general case.**
  Claude Code hands a `Bash` PreToolUse hook a command STRING, not the set of
  files that command will touch, and nothing inside "Python 3.9, standard
  library only" turns one into the other, so there is no honest way to gate
  shell writes the way Edit and Write are gated. What exists instead is
  stated above: after-the-fact detection for fenced files and for
  BrotherMode's own state, and, in enforced mode, a literal-match refusal for
  the obvious destructive forms aimed at that state. Real containment would
  need an operating-system write mediator (a sandbox profile, a container, a
  FUSE layer). That is out of scope for this project, deliberately and not
  for now, and docs/KNOWN-LIMITS.md carries the same statement.
- **A supply-chain compromise of Python or git themselves.** This project
```

### 19. docs/KNOWN-LIMITS.md

Anchor: end of the bullet 'The fence covers Edit, Write, MultiEdit and NotebookEdit for PREVENTION...'

Why: The founder's decision was refuse-and-alert now, the rest documented honestly. This is that document, written as four labelled answers (contained, refused, detected, not caught) so no reader takes one for another, naming the zero-claims hole and the over-refusals rather than leaving them to be discovered. No em or en dashes, since this file is in test_bm_docs.py's ACTIVE_DOCS dash check.

Current:

```
  What is still true either way: the snapshot only covers a claimed path that
  resolves to a REAL, EXISTING FILE at the moment the Bash call starts, not a
  directory or glob-shaped claim expanded into the files it would cover.
```

Replacement:

```
  What is still true either way: the snapshot only covers a claimed path that
  resolves to a REAL, EXISTING FILE at the moment the Bash call starts, not a
  directory or glob-shaped claim expanded into the files it would cover.
  EXTENDED 2026-08-03 (closure item C-02), and this is the honest shape of
  what is and is not contained.
  WHAT IS CONTAINED: nothing, in the operating-system sense. No file this
  project writes is protected from a shell command by anything except a hook
  that Claude Code chooses to run.
  WHAT IS NOW REFUSED: with `BM_FENCE_MODE=enforced` set, and only then, a
  `Bash` command whose TEXT matches a small literal list of destructive forms
  (`rm`, `>`, `>>`, `tee`, `sed -i`, `truncate`, `mv`, `cp`, `chmod`, an
  inline `python3 -c`, a rewriting `git` subcommand, `find -delete`, and a
  few more) while also containing the literal string `.brothermode` or
  `store.sqlite3`, plus exactly two whole-directory forms that name nothing
  (`git clean` with `-x`, and `rm -r` aimed at `.` or `*`).
  WHAT IS NOW DETECTED, in both modes: the store file disappearing, becoming
  zero bytes, or ceasing to begin with the SQLite file header, and any
  session token file disappearing, between the start and the end of a Bash
  call. Each one prints a sentence on stderr and raises a high-severity
  `fence-control-loss` alert; when the store is the thing that went missing
  the alert cannot be written and the hook says so rather than falling
  silent.
  WHAT IS NOT CAUGHT, stated in full because a partial check presented as a
  complete one is the failure this file exists to prevent: a path assembled
  at runtime or held in a variable; a destructive command inside a script
  file, a Makefile target, or any program the command merely starts; any form
  not on the list; a write that returns a fenced file to its original bytes
  before the check runs; a Bash call that deletes its own snapshot; and every
  write by a process that never passed through a hook at all (a second
  terminal, an editor, a background job). A project with NO active claim is
  not snapshotted at all, so nothing is detected there either, though
  enforced mode still refuses. And the refusal over-refuses by design:
  `ls .brothermode > /tmp/x` is refused, and so is `git clean -xfd` anywhere
  in the tree. Full operating-system containment (a sandbox profile, a
  container, a FUSE write mediator) was considered and is explicitly OUT of
  scope: it sits outside "Python 3.9, standard library only" and would be a
  second product rather than a fix.
```

### 20. docs/HOOKS.md

Anchor: the paragraph beginning 'This hook is **detection, not prevention, on purpose**'

Why: Two sentences here become false the moment the refusal exists: 'it never writes to stdout at all' and 'both entrypoints check first, before reading stdin'. Leaving either would recreate C-03 (documentation describing the intended design rather than the shipped one) in the file that closed it.

Current:

```
This hook is **detection, not prevention, on purpose** (D-1's own words): by the time
the alert exists, the write already happened. It never has a decision to make, so
unlike `bm_fence_hook.py` it never writes to stdout at all; every diagnostic goes to
stderr, and both entrypoints always exit 0, whatever went wrong. It is consent-gated
exactly like `tools/bm_autosave.py`: pre-consent, both entrypoints check first, before
reading stdin, and write nothing at all.
```

Replacement:

```
This hook is **detection, not prevention, for every ordinary write** (D-1's own words):
by the time the alert exists, the write already happened. It has a decision to make in
exactly one situation, added by C-02 and described below, and in that one situation the
`pre` phase writes a deny object to stdout; otherwise it never writes to stdout at all,
on either entrypoint, and every diagnostic goes to stderr. Both entrypoints always exit
0, whatever went wrong. It is consent-gated like `tools/bm_autosave.py`: pre-consent,
nothing is read from disk and nothing is written, not a snapshot file and not an alert
row. The one thing that runs ahead of that gate is the enforced-mode refusal check,
which reads only the payload the harness already handed the hook and writes nothing at
all.
```

### 21. docs/HOOKS.md

Anchor: insert a new subsection immediately BEFORE the '### Installing the Bash audit hook' heading

Why: HOOKS.md is where an operator goes to learn what the hooks do. Without this section the refusal is undocumented behaviour, and the aftermath paragraph is the honest way to state what enforced mode buys as a whole rather than overclaiming for either half.

Current:

```
### Installing the Bash audit hook
```

Replacement:

```
### Refusing the obvious destructive forms (C-02, 2026-08-03, enforced mode only)

The gap closure item C-02 measured was narrower and worse than "Bash is not gated". With
a proven DENY in place, `rm -f .brothermode/store.sqlite3` through Bash turned that DENY
into an ALLOW, and produced no alert row and no stderr line at all, because the store is
not itself a claimed path and nothing in this pair looked at it. Enforcement state that
the ungated channel can delete is not enforcement.

Two halves landed, and only one of them is a refusal.

**Always on, in both modes: the enforcement state is watched.** The `pre` phase now
records, alongside the fenced files, whether the store exists, whether it is non-empty,
whether it still begins with the SQLite file header, and which session token files are
present. The `post` phase reports every one of those that was LOST during the call: one
sentence on stderr and one high-severity `fence-control-loss` alert row per finding,
checked before ownership is even derived. Growth and ordinary mutation are invisible on
purpose, because a Bash call that runs `bm_store.py` is normal work and a check that
alarmed on it would be switched off within a day. When the store itself is what went
missing, the row cannot be written at all, and the hook says exactly that.

**Opt in, enforced mode only: the obvious forms are refused before they run.** With
`BM_FENCE_MODE=enforced`, the `pre` phase writes a deny object to stdout and the command
does not run, when the command TEXT matches a small literal list of destructive shell
forms while also containing the literal string `.brothermode` or `store.sqlite3`, or when
it matches one of exactly two whole-directory forms that name nothing (`git clean` with
`-x`, and `rm -r` aimed at `.` or `*`). The deny reason comes from a literal table and
names no path and no part of the command, for the same reason `bm_fence_hook.py`'s
`_FAIL_REASONS` are literal.

**This is not containment, and the difference is the whole point.** It is a substring
match plus a regex list, not a shell parser, and `refusal_for`'s own docstring lists what
it misses: a path assembled at runtime or held in a variable, a destructive command
inside a script file or a Makefile target, any form not on the list, and any program that
deletes the file without the name appearing in the command. It also over-refuses,
deliberately: `ls .brothermode > /tmp/x` is refused, and so is `git clean -xfd` anywhere
in the tree. Real containment needs an operating-system write mediator (a sandbox
profile, a container, a FUSE layer), which is out of scope here and recorded as such in
docs/KNOWN-LIMITS.md.

What enforced mode adds beyond the refusal is the aftermath. If the store does go missing
by a route the refusal misses, `bm_fence_hook.py` in the same mode then DENIES instead of
allowing (C-01), so the one-command bypass the register recorded now needs both halves to
fail rather than one.

### Installing the Bash audit hook
```

### 22. SKILL.md

Anchor: the one-writer-per-file bullet, the sentence about Bash

Why: The existing sentence stays true for fenced files, so it is kept rather than rewritten. Without the addition a reader of the constitution would conclude no Bash command is ever refused, and would be surprised by a refusal in enforced mode.

Current:

```
  requires a claim before editing any project path. It does NOT gate Bash, so
  a shell write crosses a fence unrefused and is only detected afterwards.
```

Replacement:

```
  requires a claim before editing any project path. It does NOT gate Bash, so
  a shell write crosses a fence unrefused and is only detected afterwards. One
  narrow class is the exception, and only in enforced mode: an obvious
  destructive command aimed at BrotherMode's own store or fence directory is
  refused, matched literally rather than parsed. docs/KNOWN-LIMITS.md states
  what that misses.
```

## Tests

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_rm_of_the_store_is_refused_when_enforced

The register's reproduction command, verbatim. Under BM_FENCE_MODE=enforced the pre phase exits 0, writes a deny object with permissionDecision 'deny' and 'enforced mode' in the reason, prints REFUSING on stderr, and leaves no snapshot. Under the default, empty stdout and no REFUSING line.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_redirection_onto_the_store_is_refused_when_enforced

Same both-ways assertion on ': > .brothermode/store.sqlite3', the redirection form.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_sed_i_on_the_store_is_refused_when_enforced

Same both-ways assertion on "sed -i.bak -e 's/a/b/' .brothermode/store.sqlite3".

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_tee_onto_the_store_is_refused_when_enforced

Same both-ways assertion on 'echo x | tee .brothermode/store.sqlite3'.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_inline_python_removing_the_store_is_refused_when_enforced

Same both-ways assertion on python3 -c "import os; os.remove('.brothermode/store.sqlite3')", the inline interpreter form.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_git_checkout_of_the_store_is_refused_when_enforced

Same both-ways assertion on 'git checkout -- .brothermode/store.sqlite3', the fifth form.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_removing_the_fence_directory_is_refused_when_enforced

Same both-ways assertion on 'rm -rf .brothermode/fence': the ownership tokens are the other half of the enforcement state, not just the store.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_a_tree_wide_wipe_that_names_nothing_is_refused_when_enforced

Same both-ways assertion on 'git clean -xfd', which names no BrotherMode path yet deletes .brothermode because it is excluded from git. Exercises the name-free rule.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_ordinary_commands_are_untouched_even_when_enforced

Seven ordinary commands (echo, git status, ls -la .brothermode, bm_store.py verify, rm -rf build, make test 2>&1 | tail -5, git checkout -- src/other.py) all produce empty stdout under enforced mode. Without this guard the refusal could tighten until enforcement gets switched off.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_the_deny_reason_names_no_path_and_no_command_text

With 'rm -f .brothermode/store.sqlite3 && echo SECRETMARKER', the deny reason contains neither SECRETMARKER, nor the store path, nor the project root, and the stderr line does not repeat the command. Mirrors test_deny_reason_never_leaks_a_path_or_payload_content in the fence suite.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_an_unrecognized_mode_value_does_not_refuse

BM_FENCE_MODE=enfoced (a typo) does not refuse the store-deleting command: empty stdout. Same judgement fence_mode() already records, so a missing letter cannot brick a shell.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_this_files_two_borrowed_primitives_match_the_fence_hooks

ba._enforced and fh.enforced_mode agree on seven inputs including case and whitespace variants and the empty environment, and ba.deny_payload('because') equals fh.deny_payload('because'). Pins the deliberate local copies to their originals.

### tools/test_bm_bash_audit.py :: EnforcedModeRefusesStoreDestruction.test_the_refusal_check_is_documented_as_partial

refusal_for still matches when the literal filename survives interpolation, and returns None for 'd=.brother; rm -f ${d}mode/s*', the runtime-assembled name. The stated miss is asserted so a future widening must update refusal_for's docstring and docs/KNOWN-LIMITS.md rather than quietly outgrow them.

### tools/test_bm_bash_audit.py :: ControlStateLossIsDetected.test_a_removed_session_token_raises_an_alert_row

Deleting the owner's fence token between pre and post yields exit 0, empty stdout, 'DETECTED a change to BrotherMode's own enforcement state' and 'fence-control-loss alert was raised' on stderr, and exactly one alert row: category fence-control-loss, severity high, requires_human true, no absolute root in the message, attributed to actor_name bm_bash_audit. This is the alert-row test.

### tools/test_bm_bash_audit.py :: ControlStateLossIsDetected.test_a_deleted_store_is_still_announced_even_though_unrecordable

Removing store.sqlite3 (plus -wal and -shm) between pre and post yields exit 0, 'is gone after it' and 'could NOT be recorded as an alert' on stderr. The register's exact command, in the state where the alert row is impossible, proving the stderr half does not depend on the database surviving.

### tools/test_bm_bash_audit.py :: ControlStateLossIsDetected.test_ordinary_store_growth_between_the_phases_is_not_an_alert

A second claim written between pre and post produces no 'enforcement state' line and no alert row. Pins the deliberate coarseness, so a later tightening to a content hash goes red here rather than in the founder's terminal.

### tools/test_bm_bash_audit.py :: ControlStateLossIsDetected.test_a_breach_is_announced_before_it_is_recorded

On an ordinary foreign-session breach, the index of 'DETECTED a Bash write across a fence' in stderr is less than the index of 'fence-breach alert was raised'. Pins the announce-before-record ordering that makes detection audible when the alert write fails.
