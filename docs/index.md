# flowgram

Reusable components, modular diagram builder

## Installation

```bash
uv add git+https://github.com/Sandsy09/flowgram
```

## Quick start

```python
from flowgram import Box, Column, Diagram, Edge, Row

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

fig = spec.render()  # a matplotlib Figure; spec.draw(ax) draws into an Axes
```

Save it with `spec.save("pipeline.svg")`, which writes PNG, SVG or PDF by the file's
extension. In Jupyter a diagram shows itself as a cell's result.

Specs also load from data. Every component names its `kind`:

```yaml
# pipeline.yaml
title: Model training pipeline
root:
  kind: row
  children:
    - {kind: box, id: data, label: Raw data, role: muted}
    - {kind: box, id: model, label: Model, role: accent}
edges:
  - {src: data, dst: model}
```

```python
spec = Diagram.from_yaml_file("pipeline.yaml")  # needs: pip install "flowgram[yaml]"
spec = Diagram.from_json_file("pipeline.json")  # or from_dict, from_json, from_yaml
```

`examples/pipeline.yaml` holds the whole quick-start spec as YAML.

Edges leave and arrive at the sides of their boxes that face each other, as a
straight line when the anchors line up and an orthogonal elbow otherwise. Set
`exit`, `entry` or `routing` on an `Edge` to choose for yourself.

## Known limits in 0.1

- **Edges do not avoid boxes.** An edge between two boxes takes the direct
  straight or elbow route, even when a third box is in the way. The box hides
  the part of the line that crosses it. Rearrange the layout, or set `exit`,
  `entry` and `routing` to send the edge another way.
- **Edges on one side of a box share one anchor**, at the middle of that side.
  Several edges leaving the same side start from the same point and overlap
  until they turn.
- **Text does not wrap.** Put `\n` in a label or subtitle where a line should
  break.
- **Font sizes do not follow `scale`.** They are in points, so a larger scale
  gives more room around the same text.

See the [API Reference](./reference.md).
