# Integration Plan

This zip is designed as an engineering-documentation overlay for the BrotherMode repository.

## Recommended Change

1. Replace the current root `README.md` with the README in this pack.
2. Add the new `docs/tutorials`, `docs/how-to`, `docs/reference`, `docs/explanation`, and `docs/team` pages.
3. Keep the existing official booklet under `docs/book/`.
4. Keep deep evidence, benchmark, security, architecture, release, and known-limit documents. Link to them from deeper pages rather than loading them into the first screen.
5. Run BrotherMode's documentation checks after integration.

## Do Not Delete

The new structure does not replace engineering source material such as:

- `docs/KNOWN-LIMITS.md`;
- `docs/CONTINUITY.md`;
- `docs/HOOKS.md`;
- `docs/PERFORMANCE.md`;
- release evidence;
- benchmark evidence;
- security documentation.

It changes navigation and reader order.

## Documentation Ownership Rule

Use one authority for each reader question:

| Question | Authority |
| --- | --- |
| How do I start? | `docs/tutorials/getting-started.md` |
| What command should I run? | `docs/reference/commands.md` |
| What comes next? | `docs/reference/workflow-map.md` |
| How do I know it worked? | `docs/reference/verification.md` |
| How do I install/update? | `docs/how-to/install-brothermode.md` |
| What if it breaks/refuses? | `docs/how-to/troubleshooting.md` |
| Why is it designed this way? | `docs/explanation/*` and existing architecture docs |
| What is the product story? | official booklet |

Do not duplicate long command instructions across multiple pages unless the duplication is a short quick path.

## Suggested Review Before Merge

Ask the Head of Development to review only these four files first:

```text
README.md
docs/tutorials/getting-started.md
docs/reference/workflow-map.md
docs/reference/verification.md
```

If those four answer the basic workflow question, the documentation architecture is doing its job.
