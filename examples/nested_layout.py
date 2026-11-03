"""A nested layout: columns inside a row inside a column, in the mono theme.

Containers nest to any depth. ``align="start"`` tops the service columns
against each other, and edges reach across the nesting. Run this file to
write ``nested_layout.png`` next to it.
"""

from flowgram import Box, Column, Diagram, Edge, Row, Theme


def service(name: str, *parts: str) -> Column:
    """Return a service box over the boxes it owns."""
    owned = [Box(id=part, label=part.title(), role="muted") for part in parts]
    return Column(gap=0.5, children=[Box(id=name, label=name.title()), *owned])


spec = Diagram(
    title="Order platform",
    theme=Theme.mono(),
    root=Column(
        gap=1.5,
        children=[
            Row(
                gap=1, children=[Box(id="web", label="Web"), Box(id="app", label="App")]
            ),
            Box(id="gateway", label="API gateway", role="accent"),
            Row(
                gap=1.5,
                align="start",
                children=[
                    service("accounts", "users"),
                    service("orders", "queue", "billing"),
                    service("search", "index"),
                ],
            ),
        ],
    ),
    edges=[
        *(Edge(src=client, dst="gateway") for client in ("web", "app")),
        *(Edge(src="gateway", dst=name) for name in ("accounts", "orders", "search")),
        *(Edge(src=a, dst=b) for a, b in [("accounts", "users"), ("orders", "queue")]),
        Edge(src="queue", dst="billing"),
        Edge(src="search", dst="index"),
    ],
)

if __name__ == "__main__":
    from pathlib import Path

    spec.save(Path(__file__).with_suffix(".png"))
