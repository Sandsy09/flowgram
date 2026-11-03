"""Snapshot tests for rendered output.

Opt-in and Linux only; see ``tests/conftest.py``. Run with
``uv run poe test:snapshots``.
"""

from collections.abc import Callable

import pytest
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from flowgram import Box, Diagram, Row, Shadow, Theme
from tests.conftest import spec_pipeline

SnapshotCheck = Callable[[Figure, str], None]


@pytest.mark.snapshot
def test_harness_smoke(snapshot: SnapshotCheck) -> None:
    figure = Figure(figsize=(2, 1))
    axes = figure.add_axes((0, 0, 1, 1))
    axes.set_xlim(0, 2)
    axes.set_ylim(0, 1)
    axes.set_axis_off()
    axes.add_patch(
        FancyBboxPatch(
            (0.25, 0.25),
            1.5,
            0.5,
            boxstyle="round,pad=0,rounding_size=0.1",
            facecolor="#2563EB",
            edgecolor="#1D4ED8",
        )
    )
    axes.text(1, 0.5, "flowgram", ha="center", va="center", color="white")
    snapshot(figure, "harness_smoke")


@pytest.mark.snapshot
def test_one_row(snapshot: SnapshotCheck) -> None:
    """Milestone 3 gate: one row of three boxes with mixed roles and a title."""
    diagram = Diagram(
        title="Model training pipeline",
        subtitle="Raw data is cleaned, then used to fit the model",
        root=Row(
            children=[
                Box(id="data", label="Raw data", role="muted"),
                Box(id="clean", label="Clean", subtitle="impute, clip"),
                Box(id="model", label="Model", eyebrow="STEP 3", role="accent"),
            ]
        ),
    )
    snapshot(diagram.render(), "one_row")


@pytest.mark.snapshot
def test_branching_pipeline(snapshot: SnapshotCheck) -> None:
    """Milestone 4 gate: the spec's branching pipeline with every edge drawn."""
    snapshot(spec_pipeline().render(), "branching_pipeline")


@pytest.mark.snapshot
def test_box_shadow(snapshot: SnapshotCheck) -> None:
    """Soft shadows under rounded and square boxes, with one box opting out."""
    theme = Theme.light().model_copy(
        update={"background": "#F8FAFC", "shadow": Shadow(dx=0.05, dy=0.08)}
    )
    diagram = Diagram(
        theme=theme,
        footnote="The middle box turns its shadow off",
        root=Row(
            children=[
                Box(label="Rounded", subtitle="theme shadow"),
                Box(label="No shadow", role="muted", shadow=False),
                Box(label="Square", role="accent", corner_radius=0),
            ]
        ),
    )
    snapshot(diagram.render(), "box_shadow")
