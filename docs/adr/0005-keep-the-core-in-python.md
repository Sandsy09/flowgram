# 5. Keep the core in Python and plan an SVG backend before considering Rust

## Status

Accepted

## Context

The question came up whether flowgram should be written in Rust for faster output, fewer
dependencies and a smaller install. Today the package is pure Python on top of Pydantic
and matplotlib, and matplotlib is also used to measure text for box sizes.

Indicative measurements, taken in a cloud sandbox on 3 November 2026 with Python 3.13,
matplotlib 3.11 and Pydantic 2.14. They are single runs, not averages.

| What | Measured |
| --- | --- |
| Validate a spec of 15 boxes and 14 edges (milestone 1 build) | about 0.1 ms |
| Import matplotlib, warm | about 450 ms |
| Import matplotlib, first run, building its font cache | about 3.9 s |
| Build a hand-made matplotlib figure of 15 boxes and 14 arrows | about 80 ms |
| Save that figure as PNG at 200 dpi | about 100 ms |
| Save that figure as SVG | about 360 ms |
| Installed size of matplotlib, numpy, fontTools, Pillow, kiwisolver, Pydantic | about 105 MB |

The figure was built by hand with matplotlib, not by flowgram's own `render()`, and the
layout, routing and rendering added after milestone 1 were not timed. Validation is
already fast because Pydantic's core is written in Rust. Layout and routing for a
diagram of tens of boxes is simple arithmetic. The costs that matter are drawing and
importing matplotlib, and the install size of matplotlib and its dependencies.

A Rust rewrite would have to replace matplotlib as the renderer. That loses
`draw(ax)`, which puts a diagram next to a user's charts. It also means measuring text
and handling fonts without matplotlib, publishing wheels for each platform, and
rebuilding the Python-facing API on top.

## Decision

The core stays in Python and matplotlib stays the renderer for the 0.x releases.

If render time or install size becomes a problem, respond in this order:

1. An SVG-native backend written in Python, already planned for release 0.5. It avoids
   drawing through matplotlib.
2. A compiled renderer behind the same Python spec, for example a PyO3 extension. This
   needs a new ADR.
3. A standalone Rust command-line tool that renders a JSON or YAML spec, only once the
   spec format has stabilised.

No compiled extension is added without a new ADR that supersedes this one. Revisit this
decision when any of these happens: a real gallery diagram takes long enough to matter
in a notebook or a CI job, the install size blocks a target environment, or the
SVG-native backend ships and still falls short. Re-measure with flowgram's own
`render()` on the gallery after milestone 6.

## Consequences

The package keeps its Python-native spec, `draw(ax)` and notebook workflow, with no
Rust toolchain or platform wheel matrix for contributors. It accepts an install of about
105 MB and an import of about half a second for now, and a much slower first import
while matplotlib builds its font cache.

An SVG-native backend alone would not remove matplotlib from the install, because text
measuring still depends on it. Dropping matplotlib from that path needs a replacement for
text measuring, which should get its own decision.

Because specs load from plain dicts and JSON, a future Rust renderer or command-line
tool could read the same spec without changing user code. Rust stays an option behind a
stable spec rather than a rewrite.
