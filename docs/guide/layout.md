# Layout

Layout runs in two passes: sizes are worked out from the boxes up, then
positions from the root down. Everything is in units, with the origin at the
top left.

## Box sizes

A box is as large as its text plus `Theme.text_padding` on each side, and never
smaller than `Theme.min_box_width` by `Theme.min_box_height`. Set `width` or
`height` on a box to fix either one. A fixed size is used as given, even when
the text does not fit.

Text does not wrap. Put `\n` where a line should break:

```python
from flowgram import Box, Column, Diagram, Row, Spacer

card = Box(label="Score", subtitle="weekly,\nper customer", width=3)
```

## Rows and columns

| Field | What it does |
| --- | --- |
| `gap` | Space between neighbouring children. `None` uses `Theme.gap`. |
| `align` | How children line up across the container: `"start"`, `"center"` or `"end"`. In a Row, `"start"` lines up their tops. |
| `padding` | Space around all the children. |
| `uniform` | Gives every direct `Box` child the size of the largest. |

`uniform` only touches sizes that are not fixed: a fixed width or height keeps
its value and does not count towards the largest. Nested containers and spacers
are left alone.

```python
row = Row(
    gap=0.6,
    align="start",
    uniform=True,
    children=[Box(label="Short"), Box(label="A longer label"), card],
)
```

## Spacers

A `Spacer` adds exactly its `size` along its parent's direction, with no gap on
either side. Use one to push boxes apart, or to line them up with boxes in
another row:

```python
spec = Diagram(
    root=Column(
        align="start",
        children=[
            Row(children=[Box(label="A"), Box(label="B"), Box(label="C")]),
            Row(children=[Spacer(size=2.5), Box(label="Under B")]),
        ],
    )
)
```

## The figure

The figure is the content plus `Diagram.padding` on every side, with room for
the title and subtitle above and the footnote below. A title wider than the
content widens the figure. Multiply by `Diagram.scale` to get inches.

Layout is a pure function of the spec, so you can inspect it without drawing:

```python
from flowgram.layout import layout

result = layout(spec)
print(result.width, result.height)  # the content, in units
```
