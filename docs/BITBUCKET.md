Status: CURRENT.

# Using BrotherMode with Bitbucket

BrotherMode's engine never talks to GitHub. The store, the fences, the
handover ceremony, the gates and every verification command speak plain git,
so a project whose remote lives on Bitbucket Cloud gets the same enforcement
a GitHub project gets. This page states exactly what that means, what was
executed to prove it, and what remains unproven. Every claim below names its
source; a claim nobody has executed is labeled UNVERIFIED rather than left
looking checked.

## What already works, with the proving command

The release-truth checks and remote verification use `git ls-remote`, which
is host agnostic. Executed against a public Bitbucket repository on
2026-08-15 from this machine:

    GIT_TERMINAL_PROMPT=0 git ls-remote https://bitbucket.org/tutorials/tutorials.git.bitbucket.org.git HEAD
    59d3c2c4c3e2682f0800f1fb85d45a776f4f19dd  HEAD

Nothing in `tools/` or `hooks/` shells out to `gh` or calls a GitHub API.
The only GitHub references in executable code are documentation strings and
the issue link `scripts/doctor.py` prints. The gate, the fences, the store
and the baton ceremony run identically whatever host the remote lives on.

## Remote formats

Bitbucket Cloud accepts both standard git transports:

- https: `https://bitbucket.org/<workspace>/<repository>.git`
- ssh: `git@bitbucket.org:<workspace>/<repository>.git`

The https form was exercised anonymously against a public repository this
session (command above). The ssh form follows Bitbucket's own documentation
and standard git behavior; it was not exercised here because it needs a key
registered to an account, and is labeled UNVERIFIED for that reason.

## Installing BrotherMode from a Bitbucket mirror

Claude Code's plugin system accepts full git URLs, not only GitHub
shorthand. Per the marketplace reference at
https://code.claude.com/docs/en/plugin-marketplaces, `claude plugin
marketplace add` accepts local paths, GitHub `owner/repo` shorthand, and
full git URLs including Bitbucket https and ssh URLs. So against a mirror:

```bash
claude plugin marketplace add https://bitbucket.org/<workspace>/BrotherModeUp.git
```

Two honest caveats, both from the same documentation page:

- Ref pinning. The docs state git-based marketplace sources support a
  branch or tag ref, but the exact `@ref` command syntax is only shown in
  examples for GitHub shorthand. Whether `<url>@v3.3.1` parses is
  UNVERIFIED until somebody runs it.
- Private mirrors. Background marketplace auto-updates disable credential
  helpers for https, so a private Bitbucket mirror may fail to auto-update.
  Keys held in ssh-agent work. The docs page carries the workarounds.

The tagged git clone install, the most proven path on GitHub, translates
directly:

```bash
git clone --branch v3.3.1 --depth 1 https://bitbucket.org/<workspace>/BrotherModeUp.git ~/.claude/skills/brothermode
```

UNVERIFIED end to end: no public Bitbucket mirror of this repository exists
yet, so neither command above has ever been executed against one. Creating
the mirror is an account-holding step the founder runs; the moment one
exists, executing these two commands and recording their output closes this
label.

## Reporting a gate verdict when the origin is not the canonical GitHub repo

`scripts/local-gates.sh` runs the real battery locally and then REPORTS the
verdict as a commit status. Until 2026-08-17 the reporting arm was `gh api`
against a hardcoded GitHub repository, so a checkout whose origin lives on
Bitbucket Cloud got a reporting refusal on top of a battery that had just
passed. Two ways to avoid that, and the first needs nothing from you:

1. Host routing, automatic. The runner reads the ORIGIN REMOTE, classifies
   it with `python3 tools/bm_bbstatus.py classify <url>` (github, bitbucket
   or unknown), and posts through the matching arm. On Bitbucket it POSTs a
   build status through the REST API; on an unrecognized host it posts
   nothing and says so. The GitHub arm is unchanged, including its nonzero
   return when a POST fails.
2. `scripts/local-gates.sh --no-post`. Runs the gate, prints the verdict,
   writes and signs the receipt, sends nothing anywhere. This is the right
   choice for a GitHub FORK as well: `$REPO` in that script is the canonical
   repository, so a fork's run would try to post its verdict onto the
   canonical repository rather than its own.

A reporting failure on the Bitbucket arm NEVER changes the gate's exit
status, and that difference from the GitHub arm is deliberate. On GitHub the
nonzero return is long-standing behavior in this repository and sessions
read it. On Bitbucket there is no such habit to preserve, and turning a
green battery red because a credential was absent would teach the adopter
team to distrust the gate.

Credentials come from the environment, never from a file in the repository,
and the names are identical to the sibling repository's so one team can hold
one set:

- `BITBUCKET_TOKEN`, sent as a Bearer token, or
- `BITBUCKET_USERNAME` plus `BITBUCKET_APP_PASSWORD`, sent as HTTP Basic.
  The second variable's NAME is historical: Atlassian removed classic app
  passwords on 2026-07-28 (see the authentication note below), so what it
  carries today is a scoped API token. The name is kept because both
  siblings use it and a rename would break the parity for no gain.

What is proven, and what is not, stated separately:

| Claim | Status | Evidence |
| --- | --- | --- |
| Routing picks the right arm from an origin URL, both transports, and refuses to guess on an unknown host | VERIFIED | `python3 tools/test_bm_bbstatus.py`, quoted in the run record below |
| A missing credential, an unreadable URL, or a refusing API is REPORTED and never changes the gate's exit | VERIFIED | same suite: the no-credential, bad-URL, HTTP 401 and dead-network cases each assert the message and that no request was even attempted |
| The GitHub arm still behaves exactly as before | VERIFIED | same suite reads `scripts/local-gates.sh` itself and pins the historical command and its refusal |
| A real POST reaching api.bitbucket.org and appearing on a commit | UNVERIFIED | no session in this estate holds a Bitbucket API credential, and no mirror exists to post against. Closing this needs both, and it is one command once they exist. |

## Pushing, and the pull request flow

Pushing is git, so nothing changes: the push policy in CLAUDE.md (direct to
main, secret scan, dash scan, green gate, command verification) applies
verbatim to a Bitbucket remote.

Pull requests differ from GitHub in tooling, not in shape. Bitbucket Cloud
has no equivalent of `gh pr create` from Atlassian: Atlassian's official
CLI (acli, https://developer.atlassian.com/cloud/acli/) is Jira-first as of
2026-08-15 and does not cover Bitbucket pull requests. The working paths:

1. The REST API. One POST creates a pull request, per
   https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
   (endpoint shape cross-checked against Atlassian community examples):

       curl -X POST \
         -u "<atlassian-account-email>:$BITBUCKET_API_TOKEN" \
         -H "Content-Type: application/json" \
         https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pullrequests \
         -d '{"title": "<title>", "source": {"branch": {"name": "<branch>"}}}'

   `title` and `source.branch.name` are the only required fields; the
   destination defaults to the repository's main branch. The token comes
   from the environment, never from a file in the repository, per the
   credential rules in CLAUDE.md.

2. Authentication is an Atlassian API token created at id.atlassian.com.
   App passwords are gone: Atlassian ran a brownout from 2026-06-09 to
   2026-07-27 and removed app password support on 2026-07-28 (verified
   against two independent Atlassian sources during the research pass for
   this page). Documentation elsewhere that still says app password is
   stale.

3. MCP. Atlassian's official Rovo MCP server covers Bitbucket, so a Claude
   Code session can be granted pull request tools directly. Verified
   against the server's own repository and Atlassian's announcement during
   the research pass for this page. Not exercised from this project:
   UNVERIFIED here.

## Continuous integration

`bitbucket-pipelines.yml` at the repository root mirrors the GitHub
workflow's intent: the documented full gate, `BROTHERMODE_SESSION_CAP=99
python3 tools/test_all.py`, on Python 3.9 and the newest Python 3, with a
full-depth clone because the release-truth suite needs tags to resolve.

The gate invocation in that file is not allowed to drift from the one
PROJECT.md documents: `tools/test_bm_docs.py` reads both and compares the
command and the `BROTHERMODE_SESSION_CAP` value, so a change to either side
alone fails the documentation suite by name. The GitHub side has had this
since the CI inventory check landed in `tools/test_all.py`; the Bitbucket
side had nothing until 2026-08-17.

Stated limitation, not hidden: Bitbucket Cloud's hosted runners are Linux
containers only. The macOS and Windows evidence this project publishes
still comes from `.github/workflows/tests.yml`, and a Bitbucket-only
deployment of this repository would be running with Linux evidence alone
unless somebody attaches a self-hosted macOS or Windows runner. Note what
that means for the workflow file today: it fires on `workflow_dispatch`
only, on ubuntu only, by the founder's cost law of 2026-08-16, so neither
host is producing macOS or Windows evidence automatically right now.

UNVERIFIED: the pipelines file parses (checked locally with a YAML parser
on 2026-08-15) but has never executed on Bitbucket Cloud, because no mirror
with Pipelines enabled exists yet. First green run closes this label.

## The 2026-08-18 audit, item by item

An external review produced a Bitbucket remediation plan covering both
siblings. Its claims were checked against THIS repository one at a time
rather than accepted, because a plan written about two products names
things that are true of one, of the other, or of neither. The result, with
the check that decided each:

| Claim | Verdict here | What was done |
| --- | --- | --- |
| The pipeline lives only at `ci/bitbucket-pipelines.yml`, where Bitbucket never looks | FALSE for this repository | There is no `ci/` directory at all and `bitbucket-pipelines.yml` is at the repository root, which is where Bitbucket Cloud discovers it. Nothing to fix. |
| The pipeline never runs on a pull request | TRUE, and fixed | The file defined `default` alone. Bitbucket runs a pull request pipeline only when a `pull-requests:` section matches, so merge-time enforcement did not run at the moment it exists for. A `pull-requests:` section now runs the same documented gate. |
| A run cannot say which revision it tested, so a verdict can describe an unknown tree | TRUE, and fixed | `scripts/bm_ci_context.py` captures the source, destination and tested identities, states whether the tested HEAD matched the source commit rather than assuming it, and REFUSES a pull request run missing any of them. It runs before the gate, so a build with no usable context stops rather than publishing. |
| Clone depth must be full for merge-base work | ALREADY TRUE | `clone: depth: full` was already set. The capture additionally proves the destination commit is present in the clone, because a full-depth setting is a request and its effect on pull request builds is documented by Atlassian as differing from branch builds. |
| Host-specific code inside the shared engine creates false compatibility | TRUE as a risk, now enforced | CLAUDE.md's two-host law existed only as prose. `tools/test_bm_hooks.py` now refuses a host API import, a `gh` invocation, a host API endpoint or a host CI variable read inside `tools/` or `hooks/`, with one named exemption carrying its reason. It matches CALLS, never mentions, so a documentation URL is not an offence. |
| Provider contract, Code Insights, reviewer, approval and task reads, evidence and approval freshness | OUT OF SCOPE HERE | Every one of these is an assurance-kernel concern and this repository holds no assurance kernel: it has no requirements, evidence, risk or readiness model to bind a revision to. They belong to the sibling, BrotherSBE, and building a half version here would create exactly the false compatibility the plan warns about. |
| Real end-to-end certification in a Bitbucket workspace | BLOCKED, not done | Needs a workspace and a least-privilege credential, both explicitly human steps. Neither exists. |

Release label, following the plan's own rule: this repository is
**Bitbucket Cloud compatible, preview**. It is not certified, and nothing
here should be described as full Bitbucket support until a real pull
request has run the flow end to end.

Fork pull requests: Bitbucket restricts pipelines for fork-based pull
requests, and nothing here changes that. For a single shared workspace with
branch-based development, which is the adopter team's shape, it does not
bite. It is named rather than discovered later, and the safe rule stands:
never run untrusted fork code with a privileged credential.

## What full support still needs, in order

1. Founder creates the Bitbucket workspace and mirror, and enables
   Pipelines on it. Account-holding step, nobody else can run it.
2. One session pushes the current release to the mirror, runs the two
   install commands above against it, and quotes their output here.
3. One green Pipelines run on the mirror, its URL quoted here.
4. Optional, when a Bitbucket-hosted team actually asks for it: a
   `--bitbucket` leg for `scripts/release-smoke-install.sh` mirroring the
   `--github` flag. Not built now, because it would test a mirror that does
   not yet exist. Re-checked 2026-08-17 and still correct: that script's
   `--github` arm passes `khalilmaaouni/BrotherModeUp` to `claude plugin
   marketplace add`, so a `--bitbucket` arm would need a real mirror URL to
   pass instead, and a flag that can only ever fail is worse than an absent
   one. It is sequenced after step 1 above, not forgotten.

## What this repository's two-host law already covers

Both siblings now hold the same three properties, which is what the founder
asked for when the target was constrained to GitHub and Bitbucket:

| Property | BrotherMode | BrotherSBE |
| --- | --- | --- |
| Hooks are python3 only, no POSIX shell in any wired command | yes, since 2026-08-17 (`tools/test_bm_hooks.py` refuses any other interpreter) | yes, ported first; this repository followed its shape |
| Gate reporting routes on the origin host | yes, `tools/bm_bbstatus.py` plus the routing case in `scripts/local-gates.sh` | yes |
| Bitbucket credential names | `BITBUCKET_TOKEN`, or `BITBUCKET_USERNAME` plus `BITBUCKET_APP_PASSWORD` | identical, deliberately |

The sibling's own `PARITY.md` carries the other half of this table. It was
NOT updated in the same change, and that is a real gap rather than an
oversight: the sibling repository is not present in the environment this
change was made in, so editing it was impossible here. Whoever next holds a
checkout with both repositories should copy the three rows above into
`PARITY.md` and say so in that change.

Windows, stated plainly: the hooks are now runnable in principle on a
machine with python3 and no POSIX shell. NOTHING here has executed on a real
Windows machine. That is UNVERIFIED until one does, and
`docs/WINDOWS-CHECK.md` is the written protocol for closing it.

## Sources

- https://code.claude.com/docs/en/plugin-marketplaces (marketplace source
  forms, ref support, private repo caveats), read 2026-08-15.
- https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
  (pull request endpoint), read 2026-08-15; endpoint shape cross-checked
  against Atlassian community documentation the same day.
- Atlassian app password removal dates: verified against two independent
  Atlassian sources, 2026-08-15.
- `git ls-remote` proof executed on this machine, 2026-08-15, quoted above.
