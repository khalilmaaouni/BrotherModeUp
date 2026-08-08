# Documentation Structure and Rationale

This pack follows the documentation structure used by mature open-source developer tools: a README that gets to a runnable command fast, one runnable first-project tutorial, a workflow map, a command reference, and a dedicated verification page. Product explanation is kept out of the operating path.

## Documentation Behaviors This Pack Enforces

| Documentation behavior | BrotherMode implementation in this pack |
| --- | --- |
| README gets to action quickly | install + Doctor + core workflow near the top |
| First-run tutorial is runnable | small real development task from Start to Deliver |
| Workflow has a map | Doctor/Start/Status/Next/Work/Review/Deliver plus optional paths |
| Commands have a reference | exact public BrotherMode commands, side effects, outputs, verification |
| Install is its own how-to | stable plugin, development checkout, update, uninstall, Doctor gate |
| Existing projects get a separate guide | bounded-change workflow without replacing repo engineering rules |
| Verification is explicit | dedicated verification reference for every BrotherMode stage |
| Docs have distinct types | tutorial, how-to, reference, explanation (the Diataxis split) |
| Product explanation is not the operating tutorial | booklet and architecture remain separate from Getting Started |

## Key Change From the Previous BrotherMode README

The old BrotherMode README led with category, capability claims, evidence language, and product architecture before a developer had completed the basic loop.

This pack changes the entry order to:

```text
INSTALL
  -> DOCTOR
  -> START
  -> STATUS
  -> NEXT
  -> WORK
  -> REVIEW
  -> DELIVER
```

Only after that does the documentation introduce deeper concepts such as fences, continuity, recovery, runtime boundaries, and proof semantics.

## Engineering Feedback Coverage

The requested gaps were:

> what command to run

Covered by README, Getting Started, Workflow Map, and Command Reference.

> the order of the command

Covered by the explicit normal flow and Mermaid workflow map.

> when to run

Every command table contains a "when to use" column and each detailed section starts with the trigger condition.

> how to verify

Covered by a dedicated Verification Reference plus verification blocks inside the tutorial and install guide.

> simple guide

The root README contains the minimum five-command operating loop. Deeper material is linked rather than embedded into the first-run path.

## What Should Stay Outside the README

Keep these as deeper documentation:

- benchmark methodology and comparative scores;
- long-term autonomy vision;
- detailed hook internals;
- full known-limits history;
- product positioning and category narrative;
- visual booklet;
- adversarial review ledgers;
- architectural refutations;
- internal adapter details.

They are useful. They are not onboarding.

## Repository Navigation

```text
README.md

docs/
├── index.md
├── _STYLE_GUIDE.md
├── tutorials/
│   └── getting-started.md
├── how-to/
│   ├── install-brothermode.md
│   ├── existing-projects.md
│   └── troubleshooting.md
├── reference/
│   ├── workflow-map.md
│   ├── commands.md
│   ├── verification.md
│   └── generated-artifacts.md
├── explanation/
│   ├── how-brothermode-works.md
│   └── reliability-model.md
├── team/
│   └── adoption-checklist.md
└── book/
    └── brothermode-solo-builder-booklet.html   # existing artifact
```

## Acceptance Test for the Documentation

Give only the new README and docs folder to a developer who has never used BrotherMode.

They pass if they can, without asking the author:

1. install BrotherMode;
2. verify the install;
3. start a bounded task;
4. read status;
5. find the next action;
6. understand a review failure;
7. produce a successful delivery packet;
8. explain what generated files should not be hand-edited.

If they cannot do those eight things, the docs are still too conceptual.
