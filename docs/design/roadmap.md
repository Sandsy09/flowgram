# Roadmap

The MVP is built in six milestones that each end with something that runs and can be
tested. Every later release has a gate to pass before the next one starts. Sizes are
rough estimates (S, M, L), not dates.

## MVP build

Build order is validation, then pure layout, then drawing, then edges, because each step
can be tested without the next.

| # | Milestone | What gets built | Done when | Size |
| --- | --- | --- | --- | --- |
| 1 | Foundation | Repo, CI, `Theme` and all component models with validation errors | Specs build, bad input gives readable errors, CI is green | S |
| 2 | Layout engine | Text measuring, `Row`, `Column`, `Spacer`, `uniform`, positions in units | Layout unit tests pass for nested rows and columns, with no drawing | M |
| 3 | First render | Boxes with theme roles and labels; `render()` and `draw(ax)` | A one-row diagram matches its stored snapshot | M |
| 4 | Edges | Anchors, automatic sides, straight and elbow routing, labels, dashed style, arrowheads | A branching diagram renders with every edge attached to the right sides | L |
| 5 | Export and loading | `save()` to PNG, SVG, PDF; Jupyter display; load from dict, JSON, YAML; deterministic output | Exports open correctly and re-render identically | M |
| 6 | Release | Gallery, README, API docs, changelog, name check, CI publish | The definition of done in the spec is ticked and 0.1.0 is on PyPI | S |

After milestone 4, rebuild the existing ML flowchart as an early check against the
30-line target. If it falls short, fix the API before adding export and loading.

## Releases after 0.1

Each release has one theme and one gate. Version numbers are provisional.

| Release | Theme | Scope | Gate |
| --- | --- | --- | --- |
| 0.2 | Grouping | `Panel` with title and background, `Grid` layout | Three titled stages and a grid render from the gallery with snapshot tests |
| 0.3 | More shapes | Decision diamond, cylinder, callout and annotation, legend | Each new shape has an anchor test and a gallery example |
| 0.4 | Better edges | Edge spreading along a side, label placement options, curved edges, routing around boxes | A dense branching example renders with no overlapping arrows and none crossing boxes |
| 0.5 | Reach | Graphviz or networkx auto-layout adapter, CLI that renders a YAML file, SVG-native backend | A YAML file renders from the command line |
| 0.6 | Domain kits | ML components such as layer stacks and tensor shapes, extra theme presets | A typical neural network diagram can be built from kit components alone |
| 1.0 | Stable API | No new features required | Public API reviewed and documented, no breaking changes across two minor releases |

## Success measures

For 0.x, success means the author and a few colleagues can produce a presentable diagram
quickly without fighting the API. Targets are proposals.

| Measure | How to check | Proposed target |
| --- | --- | --- |
| Real use | Real diagrams in reports or slides made with flowgram | Three by the end of 0.2 |
| Time to first diagram | A colleague follows the README | Under 10 minutes |
| Spec size | Lines to rebuild the existing ML flowchart | About 30 |
| Escape hatches | Times a real diagram needs manual sides, fixed sizes or a raw `Axes` | Falls from release to release |
| Render reliability | Open issues about wrong or broken output | None open at each release |

## Risks

| Risk | Handling |
| --- | --- |
| Edge routing looks poor | Milestone 4 is sized largest; 0.1 documents its limits and keeps manual sides as the escape |
| Text measuring differs by platform | Bundled DejaVu Sans; snapshots run on Linux only |
| Scope creep before 0.1 | The MVP cut line; anything outside the definition of done waits |
| API changes before 1.0 | Pre-1.0 stability note and a changelog entry for every breaking change |
| Name becomes unavailable | Re-check at release; publish a minimal first release early if the risk grows |
| Momentum stalls | Every milestone ends with something that runs; ship 0.1 when the checklist is ticked |
