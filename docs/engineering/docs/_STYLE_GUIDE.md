# BrotherMode Documentation Style Guide

BrotherMode engineering documentation follows a standard four-type documentation architecture, the same split the Diataxis model describes: separate tutorials, how-to guides, reference material, and explanations.

The goal is simple: a developer should know what to run, when to run it, what the output means, and how to verify success without reading product positioning first.

## Plain Engineering English

Every page should:

- state its purpose in the first two sentences;
- put the runnable path before architectural detail;
- use exact command names and file names;
- explain success and failure states;
- prefer short sentences and concrete words;
- avoid marketing claims in tutorials, how-to pages, and reference pages;
- link to deeper explanation instead of embedding long architecture sections inside a procedure;
- distinguish verified behavior from intended behavior;
- never call a generated view the source of truth.

## Documentation Types

| Type | Reader question | BrotherMode example |
| --- | --- | --- |
| Tutorial | "Can you walk me through it once?" | `tutorials/getting-started.md` |
| How-to | "How do I do this specific job?" | install, existing project, troubleshooting |
| Reference | "What exactly does this command/state mean?" | workflow map, commands, verification |
| Explanation | "Why is BrotherMode designed this way?" | state, fences, evidence, continuity |

Do not mix all four types into one README.

## Tutorial Structure

A BrotherMode tutorial should contain:

1. outcome;
2. prerequisites;
3. quick path;
4. numbered actions;
5. exact commands;
6. verification after each important step;
7. expected generated files;
8. common failure branches;
9. quick reference at the end.

The tutorial should be runnable by a developer who has never used BrotherMode.

## How-To Structure

A how-to page should contain:

1. what the procedure accomplishes;
2. when to use it;
3. prerequisites;
4. numbered steps with action verbs;
5. verification;
6. outputs/artifacts;
7. rollback or failure handling where relevant.

## Reference Structure

A reference page should optimize for lookup rather than narrative.

Use tables for:

- command;
- when to use it;
- required arguments;
- side effects;
- generated output;
- success condition;
- refusal/failure meaning.

## Explanation Structure

Explanation pages may describe architecture and rationale, but should still begin with a concrete definition.

Recommended sections:

- what it is;
- why it exists;
- components;
- boundaries;
- what is mechanical versus behavioral;
- known limits;
- links back to procedures.

## Command Examples

Use fenced blocks for commands:

```text
/brothermode:status
```

Use `bash` only for shell commands:

```bash
claude plugin install brothermode@brothermode-marketplace
```

Do not invent exact output strings when the product does not guarantee them. Instead document stable invariants, such as "Doctor reports no FAIL checks" or "delivery writes DELIVERY-PACKET.md or refuses."

## Verification Rule

Every procedural page must answer this question after each important action:

> How do I know this step worked?

A step without a verification rule is incomplete documentation.
