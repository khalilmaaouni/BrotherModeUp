# Packaging and publishing BrotherMode

Everything below was run on this machine on 2026-07-29 unless a line says
otherwise. Commands that were not run are marked, because a publishing
runbook that mixes what was proven with what was assumed is how a bad
release happens.

Nothing has been published. There is no `brothermode` package on PyPI put
there by this project, and publishing is a founder decision, not something
any agent or CI job does on its own.

## What a package install gives you, and what it does not

`pipx install brothermode` puts six commands on your PATH and nothing else:

    bm-store  bm-threads  bm-telemetry  bm-learn  bm-runtimes  bm-score

That is the toolchain. It is not the skill. `SKILL.md`, the docs, the
templates, and the hook wiring do not come with it, because a Python package
installs Python and a Claude Code skill is a directory the runtime reads.

So there are two different things a person might want:

- **The whole skill.** Clone the repository and run
  `sh scripts/bootstrap.sh`. That is the normal path for a founder.
- **The commands only.** `pipx install brothermode`. Useful for CI, for a
  server that only needs to read or write a store, or for a second machine
  where you want `bm-store` on PATH without a checkout.

`bm_autosave` and `bm_fence_hook` ship inside the package as modules but get
no command on PATH. Claude Code hooks are wired by explicit command path in
`settings.json`, so what a hook needs is a file location, not a name on
PATH. See `docs/HOOKS.md`.

## Building locally

    uv build --out-dir dist .

Verified. `uv 0.11.28` produced `brothermode-2.0.0rc3-py3-none-any.whl`
(241718 bytes) and `brothermode-2.0.0rc3.tar.gz` (242451 bytes), containing
all nine `bm_*` modules and the six console scripts.

Then install the built wheel into a throwaway environment and actually run
something, rather than trusting that a build which succeeded also works:

    python3 -m venv /tmp/probe
    /tmp/probe/bin/python -m pip install dist/brothermode-2.0.0rc3-py3-none-any.whl
    cd /tmp/some-empty-git-repo && /tmp/probe/bin/bm-store init

Verified, on both the wheel and the sdist. `bm-store init` created the
store, `bm-threads dashboard` rendered, `bm-learn rules`, `bm-runtimes list`
and `bm-score` all ran. That last check matters more than it looks: the
tools load each other by absolute path off their own directory rather than
by import name, and this is the proof that still resolves correctly when
they live in a site-packages directory instead of `tools/`.

### One build command on this machine is broken, and it fails quietly

Do not build with the macOS system pip.

    python3 -m pip wheel --no-deps -w dist .     # pip 21.2.4, Xcode Python 3.9.6

exits 0, says "Successfully built UNKNOWN", and writes
`UNKNOWN-0.0.0-py3-none-any.whl` at 1795 bytes: a wheel with no name, no
version, and none of the code. Nothing warns you. The same command under
`pip 26.0.1` produces the correct 241718 byte wheel, so the cause is the pip
version, not this configuration. Use `uv build`, or a pip new enough to read
PEP 621 metadata.

### Clean up after a build

`uv build` leaves `build/`, `dist/`, and `tools/brothermode.egg-info/`
behind. They are in `.gitignore`, but ignoring is not deleting, and
`scripts/verify-install.sh` walks the tree and counts every entry the
manifest does not name as EXTRA. A forgotten `build/` directory makes a
clean checkout look tampered with. Delete them before verifying or before
generating checksums.

## Publishing. Founder only.

These steps are written out so they can be followed, not so they can be
automated. Each one needs a credential or a decision that belongs to the
founder.

1. **Confirm the name is free.** `brothermode` has NOT been checked against
   PyPI (unverified: no lookup was performed). Check
   `https://pypi.org/project/brothermode/` before anything else. If it is
   taken, the name in `pyproject.toml` changes and so does every install
   line in the docs.

2. **Create the PyPI account and enable two-factor authentication.** PyPI
   requires 2FA for anything that can publish. Do this yourself; no agent
   handles the credential.

3. **Get an API token.** PyPI account settings, scoped to this project once
   it exists (a first upload needs an account-wide token, which you should
   then replace with a project-scoped one). Never paste the token into a
   file in this repository, a commit, or a chat.

4. **Upload to TestPyPI first.** This is not optional politeness. A version
   number on real PyPI can never be reused, so a mistake there is permanent.

       uv publish --publish-url https://test.pypi.org/legacy/ dist/*

   or, with twine:

       python3 -m pip install --user twine
       python3 -m twine upload --repository testpypi dist/*

5. **Install from TestPyPI into a clean environment and run it.**

       pipx install --index-url https://test.pypi.org/simple/ brothermode
       bm-store --help

6. **Upload to PyPI.** `uv publish dist/*` or
   `python3 -m twine upload dist/*`.

7. **Tag the release** to match the version that was published, and follow
   `docs/RELEASE.md` for the manifest and checksum steps.

Neither `twine` nor `pipx` is installed on this machine (checked
2026-07-29), so steps 4 through 6 have never been run and are written from
the tools' documented interfaces rather than from an observed run here.

## Version numbers

`VERSION` says `2.0.0-rc.3`. PEP 440, which every Python packaging tool
enforces, does not accept that spelling, so `pyproject.toml` publishes
`2.0.0rc3`. They are the same release written two ways, and a test in
`tools/test_bm.py` fails if they ever stop matching, because a wheel
labelled with a version that is not this release is a supply-chain problem
rather than a typo.

## Known limitations of this packaging

- **The modules install at the top level.** `bm_store`, `bm_threads` and
  seven siblings land directly in the environment's site-packages rather
  than inside a `brothermode` package. Anything else in that environment
  importing a name starting with `bm_` could collide. This is deliberate:
  the tools load each other by absolute file path specifically so a hostile
  `sys.path` cannot shadow `bm_store`, and wrapping them in a package would
  mean rewriting that loader in every file for a namespace benefit. The
  `bm_` prefix is the only thing keeping them apart from someone else's
  code, and it is a convention rather than a guarantee.
- **`scripts/bootstrap.sh` has nothing to hand off to yet.** It looks for
  `scripts/install.py`, which does not exist in this checkout. Until the
  installer lands, bootstrap prints the manual install path and exits 3
  rather than exiting 0 on work it did not do.
- **A package install wires no hooks.** It cannot: hooks live in the user's
  `settings.json` and point at file paths. `pipx install brothermode` gives
  you commands, not a configured session. Concretely, only `*.py` modules
  ship: `tools/bm_sessionstart.sh`, the SessionStart command `docs/SETUP.md`
  publishes, is not in the wheel or the sdist, and it would not work from
  `site-packages` anyway because it resolves its siblings from its own
  location. Wire SessionStart from a skill checkout, not from a package.
  `tools/test_bm.py` now forces a ship-or-not decision, in writing, on every
  non-`.py` file in `tools/`, so the next runtime asset cannot be dropped
  without someone saying so.
- **No CI builds this.** The build was run by hand on one machine, macOS on
  Apple silicon with Python 3.9.6. The wheel is pure Python and marked
  `py3-none-any`, so it should install anywhere, but "should" is the correct
  word: no other platform has been tested.
