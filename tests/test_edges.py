"""Tests for edge geometry: anchors, side choice and routing, without drawing."""

import itertools

import pytest

from flowgram import Box, Column, Diagram, Edge, Row
from flowgram.components import Side
from flowgram.edges import (
    LOOP_OUTSET,
    OPPOSITE,
    STRAIGHT_TOLERANCE,
    Routing,
    anchor,
    choose_sides,
    facing_side,
    route,
    route_between,
)
from flowgram.layout import Point, Rect, layout

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


SIDES: list[Side] = ["left", "right", "top", "bottom"]
A: Point = (0.0, 0.0)
B: Point = (4.0, 2.0)


def _orthogonal(points: tuple[Point, ...]) -> bool:
    return all(
        ax == bx or ay == by for (ax, ay), (bx, by) in itertools.pairwise(points)
    )


class TestRouteBetween:
    def test_facing_anchors_in_line_are_straight(self) -> None:
        assert route_between(A, "right", (4, 0), "left") == (A, (4, 0))
        assert route_between(A, "bottom", (0, 4), "top") == (A, (0, 4))

    def test_anchors_within_tolerance_are_straight(self) -> None:
        end = (4.0, STRAIGHT_TOLERANCE)
        assert route_between(A, "right", end, "left") == (A, end)

    def test_anchors_beyond_tolerance_get_an_elbow(self) -> None:
        end = (4.0, STRAIGHT_TOLERANCE * 2)
        assert len(route_between(A, "right", end, "left")) == 4

    def test_horizontal_pair_bends_halfway(self) -> None:
        assert route_between(A, "right", B, "left") == (A, (2, 0), (2, 2), B)

    def test_vertical_pair_bends_halfway(self) -> None:
        assert route_between(A, "bottom", B, "top") == (A, (0, 1), (4, 1), B)

    def test_horizontal_then_vertical_is_one_corner(self) -> None:
        assert route_between(A, "right", B, "top") == (A, (4, 0), B)

    def test_vertical_then_horizontal_is_one_corner(self) -> None:
        assert route_between(A, "bottom", B, "left") == (A, (0, 2), B)

    @pytest.mark.parametrize(
        ("side", "bend"),
        [
            ("right", (4 + LOOP_OUTSET, 0)),
            ("left", (-LOOP_OUTSET, 0)),
            ("bottom", (0, 2 + LOOP_OUTSET)),
            ("top", (0, -LOOP_OUTSET)),
        ],
    )
    def test_same_facing_sides_loop_out(self, side: Side, bend: Point) -> None:
        points = route_between(A, side, B, side)
        assert points[1] == bend
        assert _orthogonal(points)

    @pytest.mark.parametrize(
        ("exit_side", "entry_side"), list(itertools.product(SIDES, SIDES))
    )
    def test_every_side_pair_makes_an_orthogonal_elbow(
        self, exit_side: Side, entry_side: Side
    ) -> None:
        points = route_between(A, exit_side, B, entry_side, "elbow")
        assert (points[0], points[-1]) == (A, B)
        assert 3 <= len(points) <= 4
        assert _orthogonal(points)

    @pytest.mark.parametrize(
        ("exit_side", "entry_side"), list(itertools.product(SIDES, SIDES))
    )
    def test_straight_routing_is_always_one_line(
        self, exit_side: Side, entry_side: Side
    ) -> None:
        assert route_between(A, exit_side, B, entry_side, "straight") == (A, B)

    def test_auto_never_straightens_perpendicular_sides(self) -> None:
        assert route_between(A, "right", B, "top") == (A, (4, 0), B)

    def test_forced_elbow_between_lined_up_anchors_is_one_segment(self) -> None:
        assert route_between(A, "right", (4, 0), "left", "elbow") == (A, (4, 0))

    @pytest.mark.parametrize("routing", ["auto", "straight", "elbow"])
    def test_routes_start_and_end_on_the_anchors(self, routing: Routing) -> None:
        points = route_between(A, "right", B, "left", routing)
        assert (points[0], points[-1]) == (A, B)


def _pipeline() -> Diagram:
    return Diagram(
        root=Row(
            gap=2,
            children=[
                Box(id="data", label="Raw data"),
                Column(
                    gap=1,
                    children=[
                        Box(id="clean", label="Clean"),
                        Box(id="feats", label="Features"),
                    ],
                ),
                Box(id="model", label="Model"),
                Box(id="under", label="Report", width=2, height=1),
            ],
        ),
        edges=[Edge(src="data", dst="clean")],
    )


class TestRoute:
    def test_uses_the_layout_and_chosen_sides(self) -> None:
        diagram = _pipeline()
        result = layout(diagram)
        edge = Edge(src="data", dst="clean")
        path = route(edge, result)
        assert (path.exit_side, path.entry_side) == ("right", "left")
        assert path.points[0] == anchor(result.box("data"), "right")
        assert path.points[-1] == anchor(result.box("clean"), "left")
        assert len(path.points) == 4

    def test_row_neighbours_are_straight(self) -> None:
        result = layout(_pipeline())
        path = route(Edge(src="model", dst="under"), result)
        assert path.points == (
            anchor(result.box("model"), "right"),
            anchor(result.box("under"), "left"),
        )

    def test_explicit_sides_and_routing_are_used(self) -> None:
        result = layout(_pipeline())
        edge = Edge(src="data", dst="model", exit="bottom", entry="bottom")
        path = route(edge, result)
        assert (path.exit_side, path.entry_side) == ("bottom", "bottom")
        assert path.points[1][1] > result.box("data").bottom
        forced = route(edge.model_copy(update={"routing": "straight"}), result)
        assert len(forced.points) == 2

    def test_unknown_box_is_a_key_error(self) -> None:
        with pytest.raises(KeyError, match="no box has id 'nope'"):
            route(Edge(src="data", dst="nope"), layout(_pipeline()))
