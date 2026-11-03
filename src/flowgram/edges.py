"""Edge geometry: where edges attach to boxes and the path they take.

Everything here is pure geometry in layout units (origin top left, y down),
computed from a ``Layout`` without drawing anything. The renderer turns the
result into lines and arrowheads.

Each box has four anchors, one at the midpoint of each side. In 0.1, edges
that leave or arrive at the same side of a box share its anchor.

Known limits in 0.1: edges do not route around boxes, so a line between
two boxes can cross a third (the third box's fill hides it). Edges that
share a side share one anchor rather than spreading along the side.
"""

import itertools
import math
from dataclasses import dataclass
from typing import Literal

from flowgram.components import Edge, Side
from flowgram.layout import Layout, Point, Rect

Routing = Literal["auto", "straight", "elbow"]
"""How an edge is routed: as ``Edge.routing``."""

STRAIGHT_TOLERANCE = 0.05
"""How far apart two anchors can be, in units, and still count as lined up.

Automatic routing draws a straight line between anchors on facing sides
when they are this close across the line, and an elbow otherwise.
"""

LOOP_OUTSET = 0.5
"""How far, in units, an elbow between two same-facing sides reaches out."""


def anchor(rect: Rect, side: Side) -> Point:
    """Return where an edge attaches to one side of a box.

    Args:
        rect: The box's rectangle from the layout.
        side: ``"left"``, ``"right"``, ``"top"`` or ``"bottom"``.

    Returns:
        The midpoint of that side, in units.
    """
    return rect.side_midpoint(side)


OPPOSITE: dict[Side, Side] = {
    "left": "right",
    "right": "left",
    "top": "bottom",
    "bottom": "top",
}
"""The side facing each side."""


def facing_side(rect: Rect, toward: Rect) -> Side:
    """Return the side of ``rect`` that faces another box.

    The side is chosen from the vector between the two centres. When it is
    at least as wide as it is tall, the edge runs horizontally and leaves
    from the left or right; otherwise it leaves from the top or bottom. A
    tie, where the vector is exactly diagonal, goes horizontal, because
    diagrams usually read left to right.

    Args:
        rect: The box the edge attaches to.
        toward: The box at the other end of the edge.

    Returns:
        The side of ``rect`` that points towards ``toward``.
    """
    (x1, y1), (x2, y2) = rect.center, toward.center
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    return "bottom" if dy > 0 else "top"


def choose_sides(
    src: Rect,
    dst: Rect,
    exit_side: Side | None = None,
    entry_side: Side | None = None,
) -> tuple[Side, Side]:
    """Return the sides an edge leaves and arrives at.

    An explicit ``exit_side`` or ``entry_side`` (an edge's ``exit`` and
    ``entry``) is always used as given. Each side
    left as ``None`` is the side of its box that faces the other box (see
    ``facing_side``), whether or not the other side was given. When both
    are automatic they are therefore opposite: an edge between boxes in a
    row leaves from the right and arrives at the left.

    Args:
        src: The rectangle of the box the edge leaves.
        dst: The rectangle of the box the edge arrives at.
        exit_side: The side of ``src`` to leave from, or ``None`` to choose it.
        entry_side: The side of ``dst`` to arrive at, or ``None`` to choose it.

    Returns:
        ``(exit, entry)``.
    """
    return (
        facing_side(src, dst) if exit_side is None else exit_side,
        facing_side(dst, src) if entry_side is None else entry_side,
    )


@dataclass(frozen=True, slots=True)
class Route:
    """The path of one edge, in layout units.

    Attributes:
        points: The polyline from the source anchor to the destination
            anchor. Two points for a straight edge, three for an L-shaped
            elbow, four for a Z-shaped one. Every segment of an elbow is
            horizontal or vertical.
        exit_side: The side of the source box the edge leaves.
        entry_side: The side of the destination box the edge arrives at.
    """

    points: tuple[Point, ...]
    exit_side: Side
    entry_side: Side


def _horizontal(side: Side) -> bool:
    return side in ("left", "right")


def _lined_up(start: Point, exit_side: Side, end: Point, entry_side: Side) -> bool:
    (sx, sy), (ex, ey) = start, end
    if _horizontal(exit_side) and _horizontal(entry_side):
        return abs(sy - ey) <= STRAIGHT_TOLERANCE
    if not _horizontal(exit_side) and not _horizontal(entry_side):
        return abs(sx - ex) <= STRAIGHT_TOLERANCE
    return False


def _bend(a: float, b: float, exit_side: Side, entry_side: Side) -> float:
    """Return where the middle segment of a Z-shaped elbow runs.

    Between opposite or perpendicular sides it is halfway between the
    anchors. Two sides facing the same way loop out past the farther anchor.
    """
    if exit_side != entry_side:
        return (a + b) / 2
    if exit_side in ("right", "bottom"):
        return max(a, b) + LOOP_OUTSET
    return min(a, b) - LOOP_OUTSET


def _elbow(
    start: Point, exit_side: Side, end: Point, entry_side: Side
) -> tuple[Point, ...]:
    (sx, sy), (ex, ey) = start, end
    out_h, in_h = _horizontal(exit_side), _horizontal(entry_side)
    if out_h and in_h:
        x = _bend(sx, ex, exit_side, entry_side)
        return (start, (x, sy), (x, ey), end)
    if not out_h and not in_h:
        y = _bend(sy, ey, exit_side, entry_side)
        return (start, (sx, y), (ex, y), end)
    if out_h:
        return (start, (ex, sy), end)
    return (start, (sx, ey), end)


def _simplify(points: tuple[Point, ...]) -> tuple[Point, ...]:
    """Drop repeated points and corners that do not turn."""
    kept: list[Point] = []
    for point in points:
        if kept and point == kept[-1]:
            continue
        if len(kept) >= 2:
            (ax, ay), (bx, by) = kept[-2], kept[-1]
            if (ax == bx == point[0]) or (ay == by == point[1]):
                kept[-1] = point
                continue
        kept.append(point)
    return tuple(kept)


def route_between(
    start: Point,
    exit_side: Side,
    end: Point,
    entry_side: Side,
    routing: Routing = "auto",
) -> tuple[Point, ...]:
    """Return the polyline between two anchors.

    - ``"straight"`` always joins the anchors with one line, even a
      diagonal one.
    - ``"elbow"`` uses horizontal and vertical segments only. Between two
      left or right sides it is Z-shaped, bending halfway between the
      anchors; between two top or bottom sides likewise. Between a left or
      right side and a top or bottom side it is L-shaped, with one corner.
      Two sides facing the same way loop out by ``LOOP_OUTSET``.
    - ``"auto"`` is straight when the anchors are on facing axes and line up
      within ``STRAIGHT_TOLERANCE``, and an elbow otherwise.

    Segments of zero length are dropped, so an elbow between anchors that
    line up exactly is a single straight line. Edges do not avoid boxes.

    Args:
        start: The source anchor.
        exit_side: The side of the source box at ``start``.
        end: The destination anchor.
        entry_side: The side of the destination box at ``end``.
        routing: ``"auto"``, ``"straight"`` or ``"elbow"``.

    Returns:
        The points from ``start`` to ``end``.
    """
    if routing == "straight" or (
        routing == "auto" and _lined_up(start, exit_side, end, entry_side)
    ):
        return (start, end)
    return _simplify(_elbow(start, exit_side, end, entry_side))


def route(edge: Edge, layout: Layout) -> Route:
    """Return the path of an edge between two laid-out boxes.

    The sides come from ``choose_sides`` and the anchors from ``anchor``;
    the path from ``route_between`` with the edge's ``routing``.

    Args:
        edge: The edge to route. Its ``src`` and ``dst`` must be box ids in
            ``layout``, which ``Diagram`` validation guarantees.
        layout: The diagram's layout.

    Returns:
        The polyline and the sides it uses.

    Raises:
        KeyError: If ``src`` or ``dst`` is not a box id in ``layout``.
    """
    src, dst = layout.box(edge.src), layout.box(edge.dst)
    exit_side, entry_side = choose_sides(src, dst, edge.exit, edge.entry)
    points = route_between(
        anchor(src, exit_side),
        exit_side,
        anchor(dst, entry_side),
        entry_side,
        edge.routing,
    )
    return Route(points=points, exit_side=exit_side, entry_side=entry_side)


def label_point(points: tuple[Point, ...]) -> Point:
    """Return where an edge's label goes: the middle of its longest segment.

    When two segments are equally long, the first one wins, so the label
    sits nearer the source.

    Args:
        points: The edge's polyline, as in ``Route.points``. At least one
            point.

    Returns:
        The midpoint of the longest segment, in units. A polyline with a
        single point, or only zero-length segments, gives its first point.
    """
    best = (points[0], points[0])
    longest = 0.0
    for a, b in itertools.pairwise(points):
        length = math.dist(a, b)
        if length > longest:
            best, longest = (a, b), length
    (x1, y1), (x2, y2) = best
    return ((x1 + x2) / 2, (y1 + y2) / 2)
