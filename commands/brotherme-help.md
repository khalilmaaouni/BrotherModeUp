---
description: Explain what BrotherME does and how to use it, in plain language
---

Outcome to produce: a short, plain-language orientation. No setup steps that involve editing files, and no internal machinery.

Tell the user, briefly and in this order:

1. What BrotherME does: it turns an idea into a verified result, with a guided start, honest time and cost ranges, clear status, and a checked delivery.
2. The seven things they can say: /brotherme-start (begin a project), /brotherme-status (where things stand), /brotherme-next (best next step), /brotherme-review (check the work), /brotherme-deliver (package the result), /brotherme-update (get the latest version), /brotherme-help (this message). Normal use rarely needs any command after start; plain conversation works.
3. What is verified: BrotherME is verified on Claude Code. This plugin install path is new and has been installed exactly once, on the author's machine from a local copy of the repository; the git-clone install described in the repository README is the verified path. The honest list of what is and is not proven is docs/KNOWN-LIMITS.md inside the installed BrotherME folder, readable right here without visiting the repository.
4. What is true: your project's records are the one place a project's real status lives; CANVAS.md and the delivery packet are pages generated from those records for reading, never edited by hand and never the source of truth themselves.
5. Your data is yours: ask for an export and BrotherME writes everything it has recorded about your project to one file you can keep. Ask for a purge and BrotherME permanently erases the project's data, keeping only the record that a purge happened, so a deletion can never hide itself.

Then close with exactly one question that folds both paths into a single ask: mention the deep tour as the recommended option for a user who wants to see where everything stands (one page laying out project progress, decisions taken, process diagrams, the data model, and the code map, with a section for developers who want to help build), then ask whether they would like that tour or would rather just say what they want to accomplish. On the deep-tour answer, enter the deep tour flow in the brotherme skill. Honest limit either way: a project with no BrotherME record yet gets a static tour of the product instead of the live view, and the page it builds says plainly which one it is showing.
