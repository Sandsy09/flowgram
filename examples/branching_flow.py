"""A branching model flow: two models fork from shared features and meet again.

Boxes stacked in a Column fan edges out and back in, and labelled edges
mark the two outcomes. ``exit="bottom"`` sends the "worse" edge out of its own
side, so the two outcome labels do not share a line. Run this file to write
``branching_flow.png`` next to it.
"""

from flowgram import Box, Column, Diagram, Edge, Row

spec = Diagram(
    title="Champion and challenger",
    subtitle="A new model ships only if it beats the current one",
    root=Row(
        gap=2,
        children=[
            Box(id="features", label="Features", subtitle="shared", role="muted"),
            Column(
                gap=1,
                children=[
                    Box(id="champion", label="Champion", subtitle="in production"),
                    Box(id="challenger", label="Challenger", role="accent"),
                ],
            ),
            Box(id="compare", label="Compare", subtitle="hold-out set"),
            Column(
                gap=1,
                children=[
                    Box(id="ship", label="Ship", role="positive"),
                    Box(id="keep", label="Keep champion", role="muted"),
                ],
            ),
        ],
    ),
    edges=[
        Edge(src="features", dst="champion"),
        Edge(src="features", dst="challenger"),
        Edge(src="champion", dst="compare", style="dashed"),
        Edge(src="challenger", dst="compare"),
        Edge(src="compare", dst="ship", label="better"),
        Edge(src="compare", dst="keep", label="worse", style="dashed", exit="bottom"),
    ],
)

if __name__ == "__main__":
    from pathlib import Path

    spec.save(Path(__file__).with_suffix(".png"))
