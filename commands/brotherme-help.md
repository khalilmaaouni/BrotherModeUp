---
description: Explain what BrotherME does and how to use it, in plain language
---

Outcome to produce: a short, plain-language orientation. No setup steps that involve editing files, and no internal machinery.

Tell the user, briefly and in this order:

1. What BrotherME does: it turns an idea into a verified result, with a guided start, honest time and cost ranges, clear status, and a checked delivery.
2. The six things they can say: /brotherme-start (begin a project), /brotherme-status (where things stand), /brotherme-next (best next step), /brotherme-review (check the work), /brotherme-deliver (package the result), /brotherme-help (this message). Normal use rarely needs any command after start; plain conversation works.
3. What is verified: BrotherME is verified on Claude Code. This plugin install path is new and has been installed exactly once, on the author's machine from a local copy of the repository; the git-clone install described in the repository README is the verified path. The honest list of what is and is not proven is docs/KNOWN-LIMITS.md inside the installed BrotherME folder, readable right here without visiting the repository.

Then offer one more thing, as the single recommended next action for a user who wants to see where everything stands: a deep tour, one page laying out project progress, decisions taken, process diagrams, the data model, and the code map, with a section for developers who want to help build. Ask a plain yes or no. On yes, enter the deep tour flow in the brotherme skill. Honest limit either way: a project with no BrotherME record yet gets a static tour of the product instead of the live view, and the page it builds says plainly which one it is showing.

Then ask one question: what would they like to accomplish?
