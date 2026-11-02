# 4. Layout results are frozen dataclasses keyed by node path

## Status

Accepted

## Context

Layout turns a spec into positioned rectangles without drawing anything. The renderer
needs a rectangle for every box, spacer and container, and edge routing needs to find a
box's rectangle from the `id` an edge refers to. Boxes do not need an `id`, so ids alone
cannot address every node. Specs are frozen Pydantic models (ADR 0002), so equal specs
can sit at different places in a tree and object identity cannot be a key either.

The result is computed by flowgram, never written by users, and it is rebuilt on every
render.

## Decision

The layout result types are frozen standard-library dataclasses, not `Spec` models.
`Rect` holds `x`, `y`, `width` and `height` in units, with the origin at the top left and
y increasing downward. Its helpers give the right and bottom edges, the centre and side
midpoints. `Layout` holds the content size and two read-only mappings:

- `rects`, from node path to `Rect`, for every node in the tree. A node path is the
  tuple of child indices from the root, so the root is `()` and the first child of the
  root's second child is `(1, 0)`.
- `ids`, from box `id` to node path, for boxes that have an `id`.

`Layout.rect(path)` and `Layout.box(id)` raise a `KeyError` that names the missing key
and, for ids, lists the valid ones.

## Consequences

`Spec` keeps its meaning of "validated user input that loads from dicts and JSON", and
layout results skip Pydantic validation, which they do not need. Paths are stable for a
given spec, cheap to compute while walking the tree, and work for boxes without an id.
Paths change when a container's children are reordered, so they are not meant to be
stored by users; ids are the stable public handle. A layout is immutable once built, and
its mappings are copied so callers cannot change it through the dicts they passed in.
