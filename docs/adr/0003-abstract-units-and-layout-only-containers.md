# 3. Abstract layout units and layout-only containers

## Status

Accepted

## Context

Diagrams are placed on slides and in reports at different sizes. Specs should not
depend on a resolution, and the way boxes group should be simple enough to test without
drawing anything.

## Decision

Sizes, gaps and padding are in abstract units, with the origin at the top left and y
increasing downward. `Diagram.scale` converts units to inches when the figure is built.
Font sizes are in points and do not follow `scale`.

`Row` and `Column` only arrange their children. They have no fill, border or title.
A separate `Panel` with a background is planned for a later release.

## Consequences

Specs are resolution-independent and layout can be tested as pure arithmetic. Changing
`scale` mainly changes spacing and fixed-size boxes, because text stays at a fixed point
size. To shrink a finished figure uniformly, resize the exported SVG or PDF. Grouping
with a visible background has to wait for `Panel`.
