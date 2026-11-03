# MVP spec

flowgram lets a Python user describe a presentation-quality diagram as a typed,
immutable spec and render it with matplotlib, without hand-placing every shape.

- **Primary user:** data scientists and analysts who need clean flowcharts and pipeline
  figures for slides and reports.
- **Core idea:** components are validated Pydantic models. A theme supplies colours and
  type. Edges connect boxes by ID and side, never by coordinates.
- **Not a goal:** general graph layout, replacing Graphviz or D2, interactive editing.
- **Output:** static figures (PNG, SVG, PDF), or a drawing onto a caller's `Axes`.

## Decisions

| Topic | Decision | Consequence |
| --- | --- | --- |
| Units | Abstract units with a `scale` setting | `scale` converts units to inches when the figure is built. |
| Containers | Row and Column are layout-only | No fill, border or title. A `Panel` comes after the MVP. |
| Licence | MIT | |
| Name | `flowgram` | Package and import name. Re-check PyPI availability at release. |
| Spacer | In the MVP | Used for uneven alignment. It has no gap on either side and adds exactly its `size`. |
| Uniform sizing | `uniform` option on Row and Column | Equal sizing of direct `Box` children without a fixed size. Fixed-size boxes keep their size and do not count towards the group's largest size. |
| Font sizes | Fixed, in points | They do not follow `scale`. Revisit if a need appears. |
| Edge spreading | Not in 0.1 | Several edges on one side share an anchor until release 0.4. |
| Box text | Eyebrow, label and subtitle tiers, with alignment and font weights | Cards like the reference diagram's are possible in 0.1. Group panels wait for 0.2. |
| Title alignment | Left-aligned by default, configurable | `Theme.title_align`, beside the other text styling. A title wider than the content widens the figure. |
| Jupyter display | PNG by default, SVG on request | Colleagues work in Jupyter and paste into PowerPoint. |
| Loading | Explicit `from_dict`, `from_json`, `from_yaml` and file variants | No format guessing from file extensions. |
| Dependency floors | CI tests the lowest versions `pyproject.toml` allows | A stale floor fails CI rather than a user's install. |
| Styling | Users control the look through their own `Theme` | No house style is built in beyond the presets. |

## Scope of 0.1

In: `Diagram`, `Theme`, `Box`, `Edge`, `Row`, `Column`, `Spacer`; validation with
readable errors; auto-sized boxes with eyebrow, label and subtitle text, alignment and
font weights; automatic side choice with straight and elbow
routing; `Figure`, `draw(ax)` and `save()` to PNG, SVG and PDF; Jupyter display;
loading from dict or JSON, and YAML as an optional extra.

Out: `Grid`, `Panel`, other shapes, legends, curved edges, routing around boxes, edge
spreading, auto-layout, a CLI, other backends.

## Public API

Importable from the top-level package: `Diagram`, `Theme`, `RoleStyle`, `Box`, `Edge`,
`Row`, `Column`, `Spacer`, `Side`. The spec is a tree for layout plus a flat list of
edges that refer to boxes by ID.

```python
from flowgram import Diagram, Row, Column, Box, Edge

spec = Diagram(
    title="Model training pipeline",
    root=Row(
        gap=2,
        children=[
            Box(id="data", label="Raw data", role="muted"),
            Column(
                gap=1,
                children=[
                    Box(id="clean", label="Clean", subtitle="impute, clip"),
                    Box(id="feats", label="Features"),
                ],
            ),
            Box(id="model", label="Model", role="accent"),
        ],
    ),
    edges=[
        Edge(src="data", dst="clean"),
        Edge(src="data", dst="feats"),
        Edge(src="clean", dst="model", label="train"),
        Edge(src="feats", dst="model", style="dashed"),
    ],
)

fig = spec.render()  # a new matplotlib Figure
spec.draw(ax)  # or draw into an Axes you already have
spec.save("pipeline.svg")  # not built yet: milestone 5
```

Models are frozen. Build variants with `model_copy(update=...)`. Loading uses explicit
constructors: `Diagram.from_dict(data)`, `from_json(text)` and `from_yaml(text)`, plus
`from_json_file(path)` and `from_yaml_file(path)` (YAML needs the `yaml` extra). They
wrap `model_validate` and `model_validate_json`. Dict input needs a `kind` marker on
every component.

## Components

- **Diagram:** `root` (Row or Column), `edges`, `theme`, `title`, `subtitle`,
  `footnote` (a note under the content, aligned like the title),
  `scale` (inches per unit, default 1.0), `padding` (units, default 0.5).
- **Theme:** `roles` (role name to fill, stroke and text colours, plus optional
  eyebrow and subtitle colours that fall back to the text colour; must include
  `default`),
  typography (sizes in points; `label_weight`, `subtitle_weight` and `eyebrow_weight`
  as `normal` or `bold`, defaulting to bold, normal and bold; `text_align` defaulting
  to `center`; `text_valign` (`top` or `center`) defaulting to `center`;
  `title_subtitle_size` and `title_subtitle_color` for the diagram subtitle,
  falling back to `subtitle_size` and the title's colour; `footnote_size` and
  `footnote_color` for the footnote, falling back to the diagram subtitle's;
  `line_spacing` (in font sizes, default 1.2) and `tier_gap` (in label sizes,
  default 0.3); the diagram title's `title_weight`, `title_align` and
  `title_color`, defaulting to bold, `left` and the default role's text
  colour), geometry in
  units, an optional `shadow` (a `Shadow` with offset, colour, opacity and
  softness, `None` by default), edge defaults, `background`. Presets: `Theme.light()` (default) and
  `Theme.mono()`.
- **Box:** `label`, `subtitle`, `eyebrow`, `role`, `id`, `width`, `height`,
  `text_align` (`left`, `center`, `right`, or `None` for the theme's),
  `text_valign` (`top`, `center`, or `None` for the theme's), and style
  overrides `fill`, `stroke`, `text_color`, `eyebrow_color`, `subtitle_color`,
  `line_width`, `corner_radius`, and `shadow` (`True`, `False`, or `None` for
  the theme's). Text stacks top to bottom: eyebrow, label, subtitle. `id` is only
  needed if an edge refers to the box.
- **Edge:** `src`, `dst`, `exit`, `entry` (a `Side`, or `None` for automatic),
  `routing` (`auto`, `straight`, `elbow`), `label`, `style` (`solid`, `dashed`,
  `dotted`), `arrow` (`end`, `both`, `none`), `color`, `line_width`.
- **Row and Column:** `children`, `gap`, `align` (`start`, `center`, `end`), `padding`,
  `uniform`.
- **Spacer:** `size`.

### Validation

Construction reports every problem at once.

| Problem | Result |
| --- | --- |
| Two boxes share an `id` | Error naming the ID |
| Edge `src` or `dst` matches no box | Error with the missing ID and the closest valid IDs |
| Edge from a box to itself | Error; self-loops are not supported in 0.1 |
| Unknown `role` | Error listing the valid roles |
| Colour matplotlib cannot parse | Error naming the field |
| Negative size, gap or padding | Error |
| Empty Row or Column | Error |
| Unknown or misspelt field | Error |

## Layout and rendering model

Layout is computed in abstract units with the origin at the top left and y increasing
downward. The renderer flips y for matplotlib and multiplies by `scale` to get inches.

1. Validate the spec before touching matplotlib.
2. Measure each box: text extent plus padding, clamped to the minimum size, unless
   width and height are fixed.
3. Size containers bottom-up. A Row's width is its children's widths plus gaps plus
   padding; its height is the tallest child. A Column is the transpose.
4. Position everything top-down, aligning children on the cross axis.
5. Resolve anchors: four per box, at the midpoints of its sides.
6. Route edges between anchors.
7. Draw boxes, edges, then edge labels, and fit the figure to content plus padding.

Edge routing: when `exit` or `entry` is not given, use the dominant axis of the vector
between box centres. A straight line when anchors line up within a small tolerance,
otherwise an orthogonal elbow with one midpoint bend. Labels are centred on the longest
segment with a background-coloured pad.

Known limits in 0.1: edges do not avoid boxes; text does not wrap (use `\n`); edges that
share a side of a box share one anchor; font size does not change with `scale`.

## Export and compatibility

- `render()` builds a `Figure` directly, with no pyplot global state.
- `draw(ax)` draws into a caller's `Axes`: sets limits and equal aspect, axis off.
- `save(path, dpi, transparent)` writes PNG, SVG or PDF by file extension. PNGs default
  to 300 dpi, sharp on a full-width 16:9 slide on a 4K screen.
- SVG text stays as text (`svg.fonttype = "none"`) so it can be edited downstream. An
  `embed_fonts` option converts text to paths.
- A `Diagram` shows itself in Jupyter, as a PNG drawn at twice its shown size.
  `display_format="svg"` shows it as SVG. `to_png()` and `to_svg()` return the bytes or
  text that `save()` would write.
- Output is deterministic: fixed SVG hash salt, no timestamps in metadata. Files name
  `flowgram` as their creator, without the matplotlib version, so two saves of one spec
  give the same bytes on the same matplotlib and FreeType versions.
- Default font is DejaVu Sans, which ships with matplotlib.
- Python 3.11 or newer. Hard dependencies: `pydantic` (v2) and `matplotlib`. Optional
  extra: `yaml`. Fully typed.

## Definition of done for 0.1

- The existing ML flowchart is rebuilt in about 30 lines, with the same layout and card
  text (eyebrow, title, body, alignment, weights). Its titled group panels wait for
  `Panel` in 0.2.
- Three gallery examples render from the README: linear pipeline, branching model flow,
  nested row-and-column layout.
- Every validation rule produces a readable error.
- Unit tests cover validation, layout arithmetic and anchor and routing geometry.
- Image snapshot tests cover the gallery, on Linux with the bundled font.
- mypy strict and pyright pass; linting passes; `py.typed` ships.
- CI covers the supported Python versions, the lowest allowed dependency versions, and
  a smoke test on macOS and Windows.
- README covers install, quick start and gallery; API reference is generated from
  docstrings.
- `LICENSE`, `CHANGELOG` and a pre-1.0 stability note are in the repo.
- The name `flowgram` is confirmed still free on PyPI, and 0.1.0 is published from CI.
