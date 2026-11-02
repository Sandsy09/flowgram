# Contributing

## Setup

```bash
uv sync --all-groups --locked
```

After an intentional dependency change, run `uv lock`, review the result, and
commit the updated `uv.lock`.

## Branching and pull requests

`main` is never committed to directly. Every change gets its own branch and a
pull request.

Branch names are `<type>/<short-slug>`, kebab-case, where `<type>` is a
Conventional Commits type (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`,
`ci`, `build`) -- pick the type the branch's eventual squash commit will
carry, e.g. `fix/retry-timeout` or `docs/update-readme`.

```bash
git switch -c <type>/<short-slug>
# ... commit(s) ...
git push -u origin <type>/<short-slug>
```

Open a pull request and wait for CI to pass, then **squash merge**: it keeps
one commit per change on `main`, and the squash commit's subject is what
`git log` shows afterwards, so edit it into a proper Conventional Commits
subject rather than leaving the default title.

## Before opening a pull request

```bash
uv run --locked poe check
```

Rejects lock drift, then runs formatting, lint, type checking, and tests --
the same gate automation runs.

## Image snapshot tests

Rendered output is checked against baseline PNGs in `tests/snapshots/`. These
tests are marked `snapshot`, are left out of `poe test` and `poe check`, and
run only on Linux. Baselines are rendered there with the bundled DejaVu Sans,
and text rasterises slightly differently on other platforms. The Snapshots
workflow runs them on every pull request.

```bash
uv run poe test:snapshots     # compare with the baselines (Linux)
uv run poe snapshots:update   # write the current images as new baselines (Linux)
```

When a snapshot fails, the expected, actual and diff images are written to
`build/snapshot-failures/<name>/`. In CI they are uploaded as the
`snapshot-failures` artifact on the failed run.

To add or change a baseline without a Linux machine, you have two options:

- Download `actual.png` from that artifact, review it, and commit it as
  `tests/snapshots/<name>.png`.
- Run the Snapshots workflow by hand with **update** ticked and commit the
  images from its `snapshot-baselines` artifact.

Review every baseline change as you would a code change. To check the harness
itself on another platform, set `FLOWGRAM_SNAPSHOTS_ANY_OS=1`; differences
against the Linux baselines are then expected.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `chore:`, ...); a `commit-msg` hook enforces this.

## Repository

Clone with
`git clone https://github.com/Sandsy09/flowgram.git`.

Pull requests are routed for review to
`@Sandsy09/flowgram-maintainers`
through [`.github/CODEOWNERS`](.github/CODEOWNERS). Remote GitHub Actions under
`.github/workflows/` are pinned to full commit SHAs with the release tag in a
same-line comment -- keep that form when updating them.
