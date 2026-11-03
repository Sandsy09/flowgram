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
