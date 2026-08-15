# First day: one edit, one conflict, one resume

Status: CURRENT

About forty minutes on a throwaway repository. Do not do this on real work;
the point is to cause a conflict deliberately, which you do not want to do on
something that matters.

Passing all three is the exit test for the first adoption phase.

---

## Before you start

Make a scratch repository and put one file in it:

```bash
mkdir ~/scratch-pilot && cd ~/scratch-pilot && git init && echo "hello" > notes.md && git add -A && git commit -m "first"
```

Open a Claude Code session in that folder.

---

## Exercise 1: one edit

**What you are proving:** the tool holds your goal and refuses to call work
done without a check.

1. Type `/brothermode:start` and describe a small change to `notes.md`.
2. Let it agree the shape of the work with you before it touches anything.
3. Make the change.
4. Ask it whether the work is done.

**What good looks like:** it does not say done on the strength of having made
the edit. It names a check, runs it after the last change, and quotes the
output. If you have no test, the check can be as small as showing the file's
new contents, but it must run *after* the edit and its output must be shown.

**What to write down:** how long this took, and whether anything about it
surprised you.

---

## Exercise 2: one conflict

**What you are proving:** one writer per file is structural, not advice.

1. In your session, claim ownership of `notes.md` as part of some work: paste
   this and ask it to run the command as written, filling in nothing itself.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/tools/bm_store.py" claim notes-edit --lifetime ephemeral --objective "small change to notes.md" --files notes.md
   ```

   On a clone install, where that variable is unset, drop the
   `${CLAUDE_PLUGIN_ROOT}/` part and run it from the BrotherMode root instead
   (`~/.claude/skills/brothermode`). Good output names the work you claimed
   and a version number: `claimed 'notes-edit' as lifecycle ... (version 1,
   session ...)`.
2. Open a **second** Claude Code session in the same folder.
3. From that second session, try to edit `notes.md`.

**What good looks like:** the second session is refused, and the refusal names
the file, the work that owns it, which session owns it, and the exact command
to take ownership deliberately if that is really what you want.

**The thing to notice:** it does not warn and continue. It stops. That is the
whole point, and it is what stops two agents quietly overwriting each other.

**A known sharp edge you may hit.** The session identity the write hook uses
is not always the same string the tools hand you. If you claim a fence with an
identifier that the hook does not recognise as yours, you can lock *yourself*
out of your own file. The refusal message prints the identifier the hook
actually sees; use that one. If it happens, you have found the documented
issue rather than broken anything, and the way out is in the refusal message.

**What to write down:** whether the refusal message told you enough to act, or
whether you had to ask somebody.

---

## Exercise 3: one resume

**What you are proving:** context survives a session ending.

1. Close the session from Exercise 1 entirely.
2. Open a fresh Claude Code session in the same folder.
3. Type `/brothermode:status`.

**What good looks like:** the new session tells you what the project is, what
was being worked on, what is still owned by whom, and what the next step is,
without you re-explaining any of it.

**What to write down:** anything it could not tell you that you expected it
to. That gap is the most useful thing you will find today.

---

## When all three pass

Write in your team channel: both version numbers, the date, and one sentence
on what surprised you. That sentence is the first entry of the adoption
record, and it is worth more than a green tick.

Then write your first daily note. Four lines, two minutes.

---

## If something fails

Do not work around it silently. Write it in your daily note with the command,
the message, and the minutes lost. A failure that gets worked around quietly
is a failure the weekly review never gets to fix.
