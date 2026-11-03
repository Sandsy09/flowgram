# Edges

An `Edge` joins two boxes by `id`, with an arrowhead at the destination.

## Which sides

Each box has four anchors, one at the middle of each side. An edge leaves from
the side of its source that faces the destination, and arrives at the side of
the destination that faces the source. The direction between the two box centres
decides. Mostly sideways goes left or right, mostly up or down goes top or bottom,
and an exact diagonal goes sideways, because diagrams usually read left to right.

Set `exit` or `entry` to choose a side yourself. A side you leave unset is still
chosen automatically.

## Routes

`routing` picks the path:

- **`"auto"`** (the default) is a straight line when the two anchors face each
  other and line up, and an elbow otherwise.
- **`"straight"`** is always one line, even a diagonal one.
- **`"elbow"`** uses only horizontal and vertical segments. It is an L with one
  corner between a sideways and an up-down side, a Z between two sideways or two
  up-down sides, and a loop out to the side when both sides face the same way.

```python
from flowgram import Box, Column, Diagram, Edge, Row

spec = Diagram(
    root=Row(
        gap=2,
        children=[
            Box(id="score", label="Score"),
            Column(
                children=[Box(id="ship", label="Ship"), Box(id="hold", label="Hold")]
            ),
        ],
    ),
    edges=[
        Edge(src="score", dst="ship", label="pass"),
        Edge(src="score", dst="hold", label="fail", style="dashed", exit="bottom"),
    ],
)
```

## Look

| Field | Values |
| --- | --- |
| `label` | Text centred on the edge's longest segment, on a background patch |
| `style` | `"solid"`, `"dashed"` or `"dotted"` |
| `arrow` | `"end"`, `"both"` or `"none"` |
| `color`, `line_width` | Override `Theme.edge_color` and `Theme.edge_line_width` |

Edges are drawn under boxes, so a box hides any part of a line that crosses it.

## Limits

Edges do not route around boxes. Edges on the same side of a box share its one
anchor, so they overlap until they turn. In the example above, `exit="bottom"`
gives the second edge a side of its own, so the two labels do not land on one
shared line. See [Known limits](limits.md).
