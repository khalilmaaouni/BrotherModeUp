# M07: the packaging test's copy of the exclusion list was left behind

## WHAT HAPPENED

Plain language: two files hold the same list of "things never to copy when
installing BrotherMe". The real one lives in the installer. The second one lives
in the plugin packaging test suite, which needs its own copy to decide what a
plugin install should contain.

The fix in M06 grew the installer's list by two names (`PROJECT-VIEW.html` and
`Handover`). The test suite's mirror was not updated in the same edit. There is a
test whose entire job is to catch that, and it was about to catch it.

## HOW IT WAS FOUND

By the guard that exists for exactly this,
`test_the_copy_exclusion_list_covers_everything_the_clone_installer_excludes` at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_plugin_install.py:245`.
The orchestrator ran the suite after committing, caught the failure and amended the
commit rather than pushing it.

## THE EVIDENCE

The commit was written three times before it was pushed. From `git reflog`, run in
this task:

```
c1d7a47 HEAD@{0}: commit (amend): Stop a rendered project page from failing ...
964ca84 HEAD@{1}: commit (amend): Stop a rendered project page from failing ...
af375ee HEAD@{2}: commit: Stop a rendered project page from failing ...
```

`af375ee` is the first version. What the first amend had to add,
`git diff --stat af375ee 964ca84`:

```
 CHECKSUMS.sha256                | 4 ++--
 tools/test_bm_plugin_install.py | 3 ++-
 2 files changed, 4 insertions(+), 3 deletions(-)
```

and the content of that change, `git diff af375ee 964ca84`:

```
-COPY_EXCLUDE = (".git", ".brothermode", "__pycache__", "threads",
-                ".superpowers", ".DS_Store", "STATE.md",
-                "build", "dist", "*.egg-info", "STATE.md.bak-*")
+COPY_EXCLUDE = (".git", ".brothermode", "__pycache__", "threads",
+                ".superpowers", ".DS_Store", "STATE.md",
+                "build", "dist", "*.egg-info", "STATE.md.bak-*",
+                "PROJECT-VIEW.html", "Handover")
```

The assertion that would have failed, verbatim from
tools/test_bm_plugin_install.py:245:

```python
missing = [n for n in installer.COPY_EXCLUDE_NAMES
          if n not in COPY_EXCLUDE]
self.assertEqual(
    [], missing,
    "scripts/install.py COPY_EXCLUDE_NAMES grew a name this suite's "
    "own COPY_EXCLUDE does not cover: %s" % missing)
```

## HOW IT WAS FIXED

The mirror at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_plugin_install.py:82`
gained the two names, and `CHECKSUMS.sha256` was rebuilt for the changed test file.
The commit was amended rather than followed by a second commit, so the pushed
history carries one clean change.

Note the comment above that mirror, at tools/test_bm_plugin_install.py:77 to 81,
already warned that the installer list is the source of truth and that this list
must follow it. The warning was there and was still missed.

## THE RULE THIS PRODUCES

When you add a name to a list that another file mirrors, grep for the other copies
in the same edit and run their suite before you commit, because a comment saying
"keep these in sync" has never once kept anything in sync.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before. It never left the machine: the guard fired, the commit was amended, and
`af375ee` is now an unreachable object in the local repository only. The cost was
one amend cycle, which is what a guard is for. The deeper problem (four hand
written copies of one piece of hook wiring, plus this mirror) was consciously
deferred tonight and is still open.
