Status: HISTORICAL record of one incident, 2026-08-15. PO-6 was quoted,
followed once, and reported as honoured while three of the four registries
the change actually joined went unchecked. No em or en dashes.

# M21: one registry checked, and PO-6 reported as done

## What happened

A new shipping tool, tools/bm_passport.py, was added with its suite. The
session applied PO-6 ("before adding an entry to any registry, open the file
that READS that registry first") to the two registries it was thinking
about: the SUITES list in tools/test_all.py and the matching step in
.github/workflows/tests.yml. Both were correct. The session then treated
PO-6 as satisfied.

Four other registries govern a shipping tool in this repository, and the new
tool had joined none of them:

- pyproject.toml `py-modules`, which alone decides whether a pipx or pip
  install contains the file at all.
- tools/write_sites.json, the reviewed write-site inventory, which demands
  a site by site REVIEW of what the tool writes, not just a count.
- the per-file no-network allowlist in tools/test_bm.py, which bans
  `import subprocess` in shipping tools unless the file is named.
- SECURITY.md's paragraph beside that allowlist, which states the count of
  named exceptions in prose a reader is expected to trust.

A fifth constraint, not a registry but the same class, also bit: a sweep in
tools/test_bm_store.py refuses any user-facing string containing
"python3 tools/bm_", because a packaged install has no tools/ directory.

Every one of these was caught by the gate rather than by anyone remembering,
which is the system working. But the cost was a full gate cycle, roughly
twenty two minutes, spent discovering something a five minute grep would
have answered before the first line was written.

## Why the existing rule did not stop it

PO-6 is written in the singular: "any registry". Read literally it is
satisfied by checking the registry you are already thinking about. The rule
names the ACTION (open the reader first) and not the SEARCH (find every
registry that governs this class of file). A session that adds a tool while
thinking about tests will find the test registries, because those are the
ones in its head. The registries it misses are exactly the ones it is not
thinking about, and no amount of care applied to the first list surfaces the
second.

The failure is therefore structural rather than careless, and it will repeat
for the next person who adds a tool, unless the question changes shape.

## What is true, therefore

- PO-6's real question is not "did I update the registry" but "what is the
  complete set of registries that govern a file of this KIND". Those are
  different questions and only the second is answerable up front.
- The answer is discoverable mechanically today, with no new tooling: an
  existing sibling tool is the index. Pick any file in tools/ that ships,
  grep the repository for its basename, and every hit that is not its own
  source or its own suite is a registry it had to join.
- A count stated in prose (SECURITY.md's "four shipping tools import
  subprocess") is a registry with no machine behind it. It drifts silently
  unless a test reads it, and this one is only held in place by a human
  noticing the number beside the allowlist it describes.

## The check that would have caught it in five minutes

Run before writing a new tool, not after. Substitute any existing shipping
tool for bm_idle:

    grep -rln "bm_idle" --include=*.py --include=*.json --include=*.toml \
        --include=*.yml .

Every hit other than the tool's own source and its own suite is a registry
the new tool will also have to join. Run in this repository on 2026-08-15 it
returns, among the queue files:

    .github/workflows/tests.yml
    pyproject.toml
    tools/test_all.py
    tools/write_sites.json

which is precisely the set this incident missed three quarters of.

TWO WAYS THIS COMMAND WAS WRONG WHEN FIRST WRITTEN, kept because the
correction is the lesson twice over. It was drafted as
`grep -rn ... | grep -v "tools/bm_idle.py"`, filtering by CONTENT. That
silently removed the write_sites.json hit, because the key in that registry
IS the string "tools/bm_idle.py", so the one registry demanding a human
review was the one the check hid. Filter by path, or do not filter and read
the two obvious lines. And picking the sibling matters: bm_idle imports no
subprocess, so it never surfaces the no-network allowlist in
tools/test_bm.py or its SECURITY.md paragraph. A tool that writes files AND
shells out, such as bm_autosave.py, surfaces those too, at the cost of many
documentation hits when *.md is included.

It is not a control, it is a five minute reconnaissance, and it is written
here as such rather than as a gate nobody built.

## Status of a control

NOT ENFORCED, stated plainly. Nothing computes the set of registries a new
file must join, and nothing fails a change for missing one before the gate
runs. The gate DOES catch every case listed above, at the cost of a full
cycle. A candidate control, not built: a test that takes each entry in
pyproject.toml py-modules and asserts it also appears in write_sites.json
when it writes, so the two inventories cannot disagree. It is written down
here rather than built because the gate already refuses the change, and the
cost is time rather than a defect reaching a user.
