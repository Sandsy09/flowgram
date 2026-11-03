"""Tests for edge geometry: anchors, side choice and routing, without drawing."""

import pytest

from flowgram.components import Side
from flowgram.edges import anchor
from flowgram.layout import Point, Rect

BOX = Rect(1, 2, 4, 2)


@pytest.mark.parametrize(
    ("side", "point"),
    [("left", (1, 3)), ("right", (5, 3)), ("top", (3, 2)), ("bottom", (3, 4))],
)
def test_anchor_is_the_side_midpoint(side: Side, point: Point) -> None:
    assert anchor(BOX, side) == point


def test_anchors_lie_on_the_box_border() -> None:
    sides: list[Side] = ["left", "right", "top", "bottom"]
    for side in sides:
        x, y = anchor(BOX, side)
        on_vertical = x in (BOX.x, BOX.right) and BOX.y <= y <= BOX.bottom
        on_horizontal = y in (BOX.y, BOX.bottom) and BOX.x <= x <= BOX.right
        assert on_vertical or on_horizontal
