"""A linear pipeline: five steps in a row, each one feeding the next.

``uniform`` gives every step the size of the largest, so the row reads as one
even band. Run this file to write ``linear_pipeline.png`` next to it.
"""

from itertools import pairwise

from flowgram import Box, Diagram, Edge, Row

spec = Diagram(
    title="Nightly training run",
    subtitle="Each step starts when the one before it succeeds",
    root=Row(
        gap=1,
        uniform=True,
        children=[
            Box(id="ingest", label="Ingest", subtitle="daily batch", role="muted"),
            Box(id="validate", label="Validate", subtitle="schema, ranges"),
            Box(id="transform", label="Transform", subtitle="join, aggregate"),
            Box(id="train", label="Train", subtitle="gradient boosting"),
            Box(id="publish", label="Publish", subtitle="registry", role="accent"),
        ],
    ),
    edges=[
        Edge(src=src, dst=dst)
        for src, dst in pairwise(
            ["ingest", "validate", "transform", "train", "publish"]
        )
    ],
)

if __name__ == "__main__":
    from pathlib import Path

    spec.save(Path(__file__).with_suffix(".png"))
