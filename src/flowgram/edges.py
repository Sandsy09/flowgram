"""Edge geometry: where edges attach to boxes and the path they take.

Everything here is pure geometry in layout units (origin top left, y down),
computed from a ``Layout`` without drawing anything. The renderer turns the
result into lines and arrowheads.

Each box has four anchors, one at the midpoint of each side. In 0.1, edges
that leave or arrive at the same side of a box share its anchor.
"""

from flowgram.components import Side
from flowgram.layout import Point, Rect


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
