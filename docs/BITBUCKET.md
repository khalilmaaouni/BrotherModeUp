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
  examples for GitHub shorthand. Whether `<url>@v3.2.1` parses is
  UNVERIFIED until somebody runs it.
- Private mirrors. Background marketplace auto-updates disable credential
  helpers for https, so a private Bitbucket mirror may fail to auto-update.
  Keys held in ssh-agent work. The docs page carries the workarounds.

The tagged git clone install, the most proven path on GitHub, translates
directly:

```bash
git clone --branch v3.2.1 --depth 1 https://bitbucket.org/<workspace>/BrotherModeUp.git ~/.claude/skills/brothermode
```

UNVERIFIED end to end: no public Bitbucket mirror of this repository exists
yet, so neither command above has ever been executed against one. Creating
the mirror is an account-holding step the founder runs; the moment one
exists, executing these two commands and recording their output closes this
label.

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

Stated limitation, not hidden: Bitbucket Cloud's hosted runners are Linux
containers only. The macOS and Windows evidence this project publishes
still comes from `.github/workflows/tests.yml`, and a Bitbucket-only
deployment of this repository would be running with Linux evidence alone
unless somebody attaches a self-hosted macOS or Windows runner.

UNVERIFIED: the pipelines file parses (checked locally with a YAML parser
on 2026-08-15) but has never executed on Bitbucket Cloud, because no mirror
with Pipelines enabled exists yet. First green run closes this label.

## What full support still needs, in order

1. Founder creates the Bitbucket workspace and mirror, and enables
   Pipelines on it. Account-holding step, nobody else can run it.
2. One session pushes the current release to the mirror, runs the two
   install commands above against it, and quotes their output here.
3. One green Pipelines run on the mirror, its URL quoted here.
4. Optional, when a Bitbucket-hosted team actually asks for it: a
   `--bitbucket` leg for `scripts/release-smoke-install.sh` mirroring the
   `--github` flag. Not built now, because it would test a mirror that does
   not yet exist.

## Sources

- https://code.claude.com/docs/en/plugin-marketplaces (marketplace source
  forms, ref support, private repo caveats), read 2026-08-15.
- https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
  (pull request endpoint), read 2026-08-15; endpoint shape cross-checked
  against Atlassian community documentation the same day.
- Atlassian app password removal dates: verified against two independent
  Atlassian sources, 2026-08-15.
- `git ls-remote` proof executed on this machine, 2026-08-15, quoted above.
