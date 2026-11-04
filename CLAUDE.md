# flowgram: brief for Claude Code

flowgram is a Python library for presentation-quality diagrams. A user describes a
diagram as a typed, immutable spec (Pydantic models) and flowgram renders it with
matplotlib. Components are `Box`, `Edge`, `Row`, `Column`, `Spacer`, driven by a
`Theme` of semantic colour roles. It is not a general graph-layout engine.

Read `docs/design/spec.md` for the full MVP spec and `docs/design/roadmap.md` for
milestones and release gates. Decisions are recorded in `docs/adr/`.

## Status

**0.1.0 is released** on PyPI: milestones 1 to 6 are done. **Next: 0.2 Grouping.**
`Diagram.render()` and `Diagram.draw(ax)` draw a diagram, `Diagram.save()` writes
byte-identical PNG, SVG and PDF, a diagram shows itself in Jupyter,
`Diagram.from_dict`, `from_json` and `from_yaml` (with file variants) load specs, and
`to_dict`, `to_json` and `to_yaml` write them back out without defaults.

| # | Milestone | State |
| --- | --- | --- |
| 1 | Foundation: models and validation | Done |
| 2 | Layout engine: text measuring, Row, Column, Spacer, `uniform`, positions | Done |
| 3 | First render: boxes, `render()`, `draw(ax)` | Done |
| 4 | Edges: anchors, side choice, straight and elbow routing, labels | Done |
| 5 | Export and loading: `save()`, Jupyter display, YAML extra | Done |
| 6 | Release 0.1.0: gallery, README, API docs, PyPI | Done |

Update this table when a milestone lands.

## Layout of the code

```text
src/flowgram/_base.py       Spec base model, Colour / Positive / NonNegative types
src/flowgram/theme.py       RoleStyle, Theme and the light / mono presets
src/flowgram/components.py  Side, Box, Spacer, Row, Column, Edge, iter_boxes
src/flowgram/diagram.py     Diagram root and cross-component validation
src/flowgram/_text.py       Measure box text in units on an off-screen Agg canvas
src/flowgram/layout.py      Rect, Layout, box and container sizing, positions, layout()
src/flowgram/edges.py       Anchors, side choice, straight and elbow routing, label point
src/flowgram/render.py      Render settings, frame and title band, boxes, edges, render(), draw()
src/flowgram/export.py      save() to PNG, SVG and PDF, fixed metadata, to_png/to_svg, Jupyter display
src/flowgram/loading.py     from_dict, from_json, from_yaml and file variants; PyYAML imported on use
tests/                      One test module per source module
docs/design/                Spec and roadmap
docs/adr/                   Architecture decision records
```

## Commands

```bash
uv sync --all-groups --locked      # set up
uv run --locked poe check          # the full gate: lock, format, lint, mypy, tests, coverage, pyright
uv run poe test                    # tests only
uv run poe docs:build              # docs, warnings are errors
```

## Rules to keep

- Every spec model extends `Spec`: frozen, `extra="forbid"`. Variants come from
  `model_copy(update=...)`, which `Spec` overrides to validate the result. Never add
  mutable state to a spec.
- Union members carry a `kind` literal and unions use `Field(discriminator="kind")`, so
  specs load from dicts and JSON. Dict input must include `kind`.
- Validation reports every problem in one error, with the offending IDs and the valid
  choices. Keep messages readable by someone who has not seen the code.
- Layout is in abstract units, origin top left, y down. `Diagram.scale` converts units to
  inches. Font sizes are in points and do not scale. Row and Column are layout-only:
  no fill, border or title.
- Keep layout as pure functions over the spec, separate from drawing, so it can be
  tested without matplotlib figures.
- Build `Figure` objects directly. Do not use `pyplot` global state.
- Output must be deterministic so snapshot tests are stable. Snapshot tests run on
  Linux with the bundled DejaVu Sans font.
- Python 3.11 or newer. Runtime dependencies are `pydantic` and `matplotlib` only.
  PyYAML is an optional extra, not a hard dependency.
- The core stays in Python (ADR 0005). Do not add a compiled extension or a Rust
  renderer without a new ADR that supersedes it.
- Each test has a 60 second limit (`pytest-timeout`, thread method). A hang dumps the
  stack of every thread and fails the run. Fix a slow test rather than raising the limit.

## Workflow

- `main` is never committed to directly. Branch as `<type>/<slug>` (for example
  `feat/layout-engine`), open a PR, squash merge with a Conventional Commits subject.
  The PR title becomes that subject, and the PR title check enforces it.
- Every piece of work has a GitHub issue in its milestone. The PR body says
  `Closes #N`. Respect the "blocked by" links: do not start an issue whose blockers are
  open.
- Labels are defined in `.github/labels.yml` and synced by a workflow. Edit that file
  rather than the labels on GitHub. Every issue gets one type label (bare, such as
  `enhancement`), plus `area:`, `priority:` and `size:` labels.
- Releases: bump `version` in `pyproject.toml`, merge, then push tag `vX.Y.Z`. The
  Release workflow publishes to TestPyPI, then to PyPI after approval of the `pypi`
  environment, and creates a GitHub Release. Pre-release tags (`rc`, `a`, `b`) stop at
  TestPyPI.
- New workflows go in their own files under `.github/workflows/`, because `ci.yml` is
  forge-owned.
- Google-style docstrings on all public names. mypy strict and pyright must pass.
  Coverage must stay at or above 90 percent.
- Files listed in `.forge/generation.json` with regeneration `replace` are overwritten
  if the project is regenerated by forge. Edit them only when needed, such as adding
  dependencies.

## Out of scope for 0.2

Extra shapes, legends, curved edges, routing around boxes, spreading several edges
along one side, auto-layout, a CLI, non-matplotlib backends. These are planned for
later releases in the roadmap. Do not start them early. `Grid` and `Panel` are 0.2's
work.

## Next task: 0.2 Grouping

`Panel` (a titled, filled group of components) and `Grid` layout, tracked by the epic
#32 in the "0.2 Grouping" milestone. Done when three titled stages and a grid render
from the gallery with snapshot tests (see `docs/design/roadmap.md`). Break the epic
into issues before starting, and settle the `Panel` API with the user first. `Panel` is
the component that draws a group, so Row and Column stay layout-only. #96 (size a
diagram to a target width) is in the same milestone.

Before 1.0: check SVG "Convert to Shape" in desktop PowerPoint (#98).

`examples/card_flow.py` is the committed API check: a neutral rebuild of the user's
reference slide. The reference itself is the user's work material: keep it and its text
out of the repo, issues and PRs.
