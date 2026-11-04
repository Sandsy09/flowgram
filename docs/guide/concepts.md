# Concepts

A flowgram diagram is a **spec**: a tree of plain data that says what to draw,
not where. flowgram works out the sizes and positions, then draws it.

## The spec tree

Every diagram has one `root`, a `Row` or a `Column`. Containers hold boxes,
spacers and other containers, nested as deep as you like:

```python
from flowgram import Box, Column, Diagram, Row

spec = Diagram(
    title="Two stages",
    root=Row(
        children=[
            Box(id="load", label="Load"),
            Column(
                children=[Box(id="fit", label="Fit"), Box(id="score", label="Score")]
            ),
        ]
    ),
)
```

- **`Box`** is the only thing that draws. It has a `label`, and optionally an
  `eyebrow` above it and a `subtitle` below it. These are its three text tiers.
- **`Row`** lays its children out left to right, **`Column`** top to bottom. They
  draw nothing themselves: no fill, border or title.
- **`Spacer`** is empty space along its parent's direction.

## Edges

Edges sit beside the tree in `Diagram.edges` and refer to boxes by `id`, wherever
the boxes are nested. They never use coordinates:

```python
from flowgram import Edge

spec = spec.model_copy(
    update={"edges": [Edge(src="load", dst="fit"), Edge(src="load", dst="score")]}
)
```

Only boxes that an edge refers to need an `id`. Ids must be unique within a
diagram.

## Specs are checked and immutable

A spec is checked when it is built. A mistake reports every problem at once,
naming the offending ids and the valid choices, so one run shows everything to
fix:

```python
from pydantic import ValidationError

try:
    Diagram(
        root=Row(children=[Box(id="a", label="A", role="nope")]),
        edges=[Edge(src="a", dst="b")],
    )
except ValidationError as error:
    print(error)
```

Specs cannot be changed once built. Make a variant with
`model_copy(update={...})`, as above. The variant is checked just like a new
spec, so a bad value, a misspelt field or an edge to a missing box fails at once,
with every problem listed:

```python
try:
    spec.model_copy(update={"scale": -1, "titel": "Typo"})
except ValidationError as error:
    print(error)
```

Values in `update` can be specs or plain data, such as a dict with a `kind`.

## Units

Sizes, gaps and padding are in abstract **units**. `Diagram.scale` says how many
inches one unit is when the figure is built, `1.0` by default. Font sizes are in
points and stay the same at any scale, so a larger scale gives the same text more
room. See [Layout](layout.md).
