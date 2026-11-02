"""Snapshot tests for rendered output.

Opt-in and Linux only; see ``tests/conftest.py``. Run with
``uv run poe test:snapshots``.
"""

from collections.abc import Callable

import pytest
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

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
