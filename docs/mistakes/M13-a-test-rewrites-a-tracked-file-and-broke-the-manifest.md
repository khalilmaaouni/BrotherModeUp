# M13: a test rewrites a tracked file, so the signed manifest goes stale every run

## WHAT HAPPENED

Plain language: BrotherMe ships a signed list of every file and its fingerprint
(`CHECKSUMS.sha256`), so a user can prove their install is untampered. One test in
the suite regenerates a tracked evidence file every time it runs, by design, because
that file is meant to be the latest run's transcript rather than a fixed golden
copy.

The consequence nobody had priced in: running the test suite changes a tracked file,
which invalidates the signed manifest. So the sequence "commit, then run the gate"
leaves the tree with a manifest that no longer matches, and the commit has to be
amended.

That happened three times in one night. Three of the five commits of the run were
amended before being pushed, and two of those amends existed only to re-bake
checksums.

## HOW IT WAS FOUND

By the orchestrator running the manifest check after the gate and finding it stale.
Every catch happened before the push, so the pushed history is clean.

## THE EVIDENCE

The amend history, from `git reflog` run in this task:

```
c1d7a47 HEAD@{0}: commit (amend): Stop a rendered project page from failing ...
964ca84 HEAD@{1}: commit (amend): Stop a rendered project page from failing ...
af375ee HEAD@{2}: commit: Stop a rendered project page from failing ...
04d3133 HEAD@{3}: commit: Open the 2.1 development line ...
ac7ef87 HEAD@{4}: commit (amend): Make the fence bite Codex writes ...
fe45985 HEAD@{5}: commit: Make the fence bite Codex writes ...
745e2d7 HEAD@{6}: commit (amend): Freeze the comparative benchmark ...
ef097ae HEAD@{7}: commit: Freeze the comparative benchmark ...
```

What each amend had to carry, verified with `git diff --stat`:

```
$ git diff --stat ef097ae 745e2d7
 CHECKSUMS.sha256                                   | 70 +++++++++++++-------
 .../absolute-lead/evidence/L03/E4-endtoend.json    |  8 +--

$ git diff --stat fe45985 ac7ef87
 CHECKSUMS.sha256 | 6 ++++++      (the six new L06 and L09 evidence files,
                                   committed before the manifest was rebuilt)

$ git diff --stat 964ca84 c1d7a47
 CHECKSUMS.sha256 | 2 +-          (the E4 evidence file again)
```

The cause is documented in the test itself, at
`/Users/khalil.maaouni/Documents/BrotherModeUp/tools/test_bm_controller.py:3427`,
verbatim:

```
THE ARTIFACT IS REGENERATED ON EVERY RUN, BY DESIGN, so
docs/program/absolute-lead/evidence/L03/E4-endtoend.json shows as
modified after any run of this file. It is the LATEST run's evidence,
not a golden file: every value in it is read back out of the live
store this test just drove, which is what makes it evidence at all.
The only bytes that differ run to run are the four checkpoint_ref
values, which are uuid4 ids the store mints per checkpoint.
```

The path is defined at tools/test_bm_controller.py:3414 and the class is
`TestEndToEndE4` at tools/test_bm_controller.py:3419.

Current state of the manifest at HEAD, verified in this task, three consecutive
runs:

```
$ shasum -a 256 -c CHECKSUMS.sha256 | grep -c ": OK$"
367
$ for i in 1 2 3; do shasum -a 256 -c CHECKSUMS.sha256 | grep -c "FAILED"; done
0
0
0
$ git status --porcelain | wc -l
0
```

AND THEN IT HAPPENED AGAIN, LIVE, WHILE I WAS WRITING THIS FILE. The first time I
ran the manifest check in this task it reported
`docs/program/absolute-lead/evidence/L03/E4-endtoend.json: FAILED`. Three runs
later it was clean, and I nearly wrote that up as unexplained. Twenty minutes
after that, with the same file and no action of mine, the working tree went dirty
again:

```
$ git status --porcelain
 M docs/program/absolute-lead/evidence/L03/E4-endtoend.json

$ git diff docs/program/absolute-lead/evidence/L03/E4-endtoend.json
-      "checkpoint_ref": "0ad11e7068904943a3c59c036e671744",
+      "checkpoint_ref": "014b412ed21849fc96040791bbd89e9a",
-      "checkpoint_ref": "3fbb40aa2dae425aaa55d605a7c7091b",
+      "checkpoint_ref": "fd748ea214f74ba7b7b485a8e241371e",
-      "checkpoint_ref": "3c64edf2b4174ac98ebd0e68bedbb3b9",
+      "checkpoint_ref": "398e3ae565674cdbbce465da8e36dcd8",
-      "checkpoint_ref": "0893a9cf7ddb4ddc92328ac745d882a8",
+      "checkpoint_ref": "cb8a8f78899647209ecf19403aae88a8",
```

Exactly the four checkpoint ids the docstring names, and nothing else. I ran no
test in this task and edited nothing in the repository, so another process on this
machine ran `tools/test_bm_controller.py` at 09:31 while I worked. That is the
mechanism, demonstrated rather than argued: any run of that suite, by anyone, at
any time, silently invalidates the signed manifest.

STATE FOR THE NEXT SESSION: at the time this file was written, the working tree at
`/Users/khalil.maaouni/Documents/BrotherModeUp` was DIRTY for exactly this file and
this reason. HEAD (c1d7a47) is pushed and its committed manifest is correct for its
committed content; the local checkout is not. Run
`git checkout docs/program/absolute-lead/evidence/L03/E4-endtoend.json` or rebuild
the manifest, and check `git status` before you conclude anything about tampering.

## HOW IT WAS FIXED

Per instance: rebuild the manifest and amend the commit. The class was NOT fixed.
There is no ordering rule written down anywhere, no pre-commit check that the
manifest matches, and no change to how the E4 artifact is stored.

The open choice for the next session is between three options, none of them taken
tonight: (a) always rebuild checksums as the last step before committing, written
into the release checklist; (b) exclude the regenerated artifact from the manifest
the way the generated project pages are excluded (see M05 and M06), which costs the
artifact its tamper protection; (c) write the artifact somewhere untracked and copy
it in deliberately when it is meant to be evidence.

## THE RULE THIS PRODUCES

A test that writes into the repository makes the signed manifest a moving target:
rebuild the manifest after the last test run and before the commit, never the other
way round, and never trust a manifest that was built before the gate.

## WAS IT CAUGHT BEFORE OR AFTER IT COULD HURT A USER

Before, every time, but by hand rather than by a guard, and the class is live right
now: the working tree drifted again during the writing of this file. A user who cloned a version
where this had been missed would run `verify-install` and be told their download
was tampered with, which is the same user-facing failure as M05 and M06 arriving
through a different door. Nothing prevents the next session from missing it: the
only defence tonight was somebody remembering to look.
