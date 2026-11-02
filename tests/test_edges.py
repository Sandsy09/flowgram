"""Tests for edge geometry: anchors, side choice and routing, without drawing."""

import pytest

from flowgram.components import Side
from flowgram.edges import OPPOSITE, anchor, choose_sides, facing_side
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


def _at(cx: float, cy: float) -> Rect:
    """A 2 x 1 box centred on ``(cx, cy)``."""
    return Rect(cx - 1, cy - 0.5, 2, 1)


ORIGIN = _at(0, 0)


@pytest.mark.parametrize(
    ("cx", "cy", "out", "into"),
    [
        (5, 0, "right", "left"),
        (-5, 0, "left", "right"),
        (0, 5, "bottom", "top"),
        (0, -5, "top", "bottom"),
        (5, 2, "right", "left"),
        (-5, -2, "left", "right"),
        (2, 5, "bottom", "top"),
        (-2, -5, "top", "bottom"),
        (5, -2, "right", "left"),
        (-2, 5, "bottom", "top"),
    ],
)
def test_dominant_axis_picks_facing_sides(
    cx: float, cy: float, out: Side, into: Side
) -> None:
    assert choose_sides(ORIGIN, _at(cx, cy)) == (out, into)


@pytest.mark.parametrize(
    ("cx", "cy", "out"),
    [(3, 3, "right"), (-3, 3, "left"), (3, -3, "right"), (-3, -3, "left")],
)
def test_diagonal_tie_goes_horizontal(cx: float, cy: float, out: Side) -> None:
    assert choose_sides(ORIGIN, _at(cx, cy)) == (out, OPPOSITE[out])


def test_automatic_sides_are_opposite() -> None:
    for cx, cy in [(4, 1), (-1, 6), (0.5, -3), (-7, -7)]:
        out, into = choose_sides(ORIGIN, _at(cx, cy))
        assert into == OPPOSITE[out]


def test_explicit_sides_win() -> None:
    assert choose_sides(ORIGIN, _at(5, 0), "top", "top") == ("top", "top")


def test_explicit_exit_with_automatic_entry() -> None:
    # The entry still faces the source, whatever side the edge leaves from.
    assert choose_sides(ORIGIN, _at(5, 0), exit_side="bottom") == ("bottom", "left")


def test_explicit_entry_with_automatic_exit() -> None:
    assert choose_sides(ORIGIN, _at(0, 5), entry_side="left") == ("bottom", "left")


def test_facing_side_uses_centres_not_edges() -> None:
    wide = Rect(0, 0, 10, 1)
    below_right = _at(8, 4)
    # The vector between centres (3, 3.5) is mostly vertical.
    assert facing_side(wide, below_right) == "bottom"


def test_opposite_pairs() -> None:
    assert all(OPPOSITE[OPPOSITE[side]] == side for side in OPPOSITE)
