# BrotherMode identity contract

Status: CURRENT as of 2026-08-04.

This page fixes the names this project uses, says which of them may appear in
a page a user reads today, and says what a future rename would have to touch.
It exists because the same idea currently has five written forms in the tree,
and until now nothing said which form was correct where.

The machine-readable copy of section 1 is `product.identity.json` at the
repository root. The two must agree, and a test in `tools/test_bm_docs.py`
refuses a disagreement between that file, `.claude-plugin/plugin.json` and
`pyproject.toml`.

## 1. Canonical forms

| Surface | Canonical form | Where the string actually lives |
|---|---|---|
| Product name, everything a user reads | `BrotherMode` | README.md, the pages under docs/, the launch drafts, project-template prose |
| Persona voice | `BrotherME` | `skills/brotherme/SKILL.md` and the seven `/brotherme-*` commands, nowhere else as a current name |
| Plugin id | `brotherme` | `.claude-plugin/plugin.json`, field `name` |
| Marketplace id | `brotherme-marketplace` | `.claude-plugin/marketplace.json`, field `name` |
| pip distribution name | `brothermode` | `pyproject.toml`, `[project] name` |
| Python import package | `brotherme` | `brotherme/__init__.py`, `packages` in `pyproject.toml` |
| Console script prefix | `bm-` | the console scripts in `pyproject.toml` |
| Module file prefix | `bm_` | `tools/bm_*.py`, `mcp/bm_mcp_server.py` |
| Slash commands | `/brothermode` for the expert skill, `/brotherme-*` for the seven guided commands | root `SKILL.md`, `commands/` |
| Durable-state environment prefix | `BROTHERMODE_` | 15 distinct names across `scripts/` and `tools/` |
| Code-identity environment variable | `BROTHERME_CONFIG` | `scripts/setup.py` |
| Skill root on disk | `~/.claude/skills/brothermode` | `scripts/install.py` |
| Vault on disk | `~/BrotherModeVault` | the default behind `BROTHERMODE_VAULT` |
| Per-project store | `.brothermode/` | the root of every project the tool has run against |
| Git ref namespace | `refs/brothermode` | the autosave refs written by the installer |
| Consent config | `~/.brotherme/config.json` | `scripts/setup.py` |
| Repository slug | `BrotherModeUp` | `github.com/khalilmaaouni/BrotherModeUp` |

## 2. The two-namespace rule

There are two spellings in the code and on disk, `brothermode` and
`brotherme`, and the split between them is permanent and intentional. It is
not drift waiting to be tidied up.

`brothermode` owns durable state, meaning anything a user already has written
to their disk: the skill root `~/.claude/skills/brothermode`, the vault
`~/BrotherModeVault`, the per-project store `.brothermode/`, the git refs
under `refs/brothermode`, and the `BROTHERMODE_` environment variables.

`brotherme` owns code identity, meaning the names a package registry or an
import statement keys off: the plugin id `brotherme`, the marketplace id
`brotherme-marketplace`, the Python import package `brotherme`, the consent
config `~/.brotherme/config.json`, and `BROTHERME_CONFIG`.

The two namespaces do not collide, each is internally consistent, and
unifying either direction would break real state on the disk of every person
who has already installed the tool. So neither is unified.

The pip distribution name stays `brothermode`, the console prefix stays
`bm-`, and the module prefix stays `bm_`. None of the three changes.

## 3. Where BrotherME may be written

`BrotherME` is a persona voice, not a product name. It is allowed in exactly
two places: inside the guided beginner skill at `skills/brotherme/`, and in
the `/brotherme-*` commands that skill drives. In those places it is the name
the guided flow speaks under.

Everywhere else that a reader treats as current state, the product is called
`BrotherMode`. That includes README.md, every page under docs/ that is not a
dated record, the launch drafts, and any new copy.

Two uses of the string stay legal outside that scope because they are not the
product name at all: a path or filename that contains it, such as the dated
source plan under `docs/evidence/`, and a quotation of the persona's own
speech.

## 4. Where BrotherModeUp may be written

`BrotherModeUp` is the repository slug. It is never the name of the product.
It is legal in a URL, in a clone or plugin-install command that a user is
told to type, and in a code fence. It is not legal in prose that presents it
as the thing itself.

The install commands keep the literal slug because it is the real path on
GitHub and a command that does not work is worse than a name that is not
preferred.

## 5. What a rename would have to touch

If a future decision changes any canonical form, the change is not a
find-and-replace. The 2026-08-04 identity survey counted, with `git grep`
over the tracked tree: `BrotherModeUp` 165 times in 44 files, `BrotherMode`
excluding that slug 641 times in 130 files, `BrotherME` 131 times in 19
files, lowercase `brothermode` 700 times in 110 files, lowercase `brotherme`
466 times in 70 files, `BROTHERMODE_*` 357 times across 15 distinct names,
and `BROTHERME_CONFIG` 53 times.

The survey's break list, meaning the surfaces where a rename breaks something
a user already has, is:

1. The pip distribution name `brothermode`, already in installed-package
   lists and requirements files.
2. The Python import package `brotherme`, a second and separate break from
   the one above.
3. The plugin id `brotherme` and the marketplace id `brotherme-marketplace`,
   which the documented install forms hardcode.
4. The clone-install directory `~/.claude/skills/brothermode`, which exists
   on disk today.
5. The consent config `~/.brotherme/config.json` and `BROTHERME_CONFIG`.
6. The vault `~/BrotherModeVault` and `BROTHERMODE_VAULT`, which hold a
   user's own written memory, not display text.
7. The per-project store `.brothermode/` in every project the tool has run
   against.
8. The git ref namespace `refs/brothermode` and the `.git/info/exclude` line
   the installer writes.
9. The settings backup name `settings.json.brothermode-backup-<timestamp>`
   and the hook-ownership marker `brothermode-install.json`, which is how the
   installer recognizes its own entries.
10. The 15 `BROTHERMODE_*` environment variables, which stop being read
    silently if the prefix moves.
11. The console prefix `bm-` and the `tools/bm_*.py` filenames, if code
    identity is being changed as well as the product name.
12. The repo slug in `tools/bm_project_facts.py` (`REPO_URL`) and the tests
    that assert against it, which need updating in the same change even
    though GitHub redirects an old repository name.

Any such change updates the canonical-forms table, `product.identity.json`,
and every call site in the same commit, and says in the release notes what an
existing install has to do.

## 6. Historical records are never rewritten

Dated records under `docs/closure/` and `docs/evidence/`, and the entries
already written in `CHANGELOG.md`, are evidence of what was done and said on
a date. They keep whatever names they were written with. A rename pass
excludes them, and so does the naming test described below. Rewriting a name
inside a dated record would falsify the record, which costs more than the
inconsistency it removes.

The same applies to the review records under `docs/craft/` and the design
specs under `docs/superpowers/`.

## 7. Enforcement

`tools/test_bm_docs.py` holds the checks:

- A naming test walks the pages a reader treats as current state and refuses
  `BrotherModeUp` or `BrotherME` used as a current product name there.
- A manifest test refuses a disagreement between `product.identity.json`,
  `capabilities.status.json`, `.claude-plugin/plugin.json` and
  `pyproject.toml`.
- A capability test refuses a capability entry with an unknown state or an
  empty evidence field.
- A banned-absolutes test refuses the words `fully supported`,
  `production-ready`, `works everywhere` and the bare `all platforms` on a
  current page unless the line points at a file that carries the evidence.

Run them with `python3 tools/test_bm_docs.py`.

Two current pages do not comply yet, and the naming test names them as
exclusions with the reason in a comment rather than pretending they pass:
`docs/brotherme-explained.html`, which presents the persona as the product
alongside legitimate persona speech, and
`docs/specs/canonical-project-protocol.md`, which cites the dated source plan
by the title it was written under. Both are copy changes, and both are open.
