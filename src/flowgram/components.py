"""Building blocks of a diagram: boxes, spacers, layout containers and edges."""

from collections.abc import Iterator
from typing import Annotated, Literal

from pydantic import Field

from flowgram._base import (
    Colour,
    FrozenSeq,
    NonNegative,
    Positive,
    Spec,
    TextAlign,
    TextVAlign,
)

Align = Literal["start", "center", "end"]
"""Cross-axis alignment of children inside a Row or Column."""


Side = Literal["left", "right", "top", "bottom"]
"""A side of a box where an edge can leave or arrive."""


EdgeStyle = Literal["solid", "dashed", "dotted"]
"""How an edge's line is drawn."""


class Box(Spec):
    """A labelled rectangle, the basic node of a diagram.

    Text is stacked top to bottom: an optional ``eyebrow``, the ``label``, then
    an optional ``subtitle``. Leave ``width`` and ``height`` unset to size the
    box from its text. Style fields left as ``None`` fall back to the theme
    role named by ``role``, or to the theme itself.

    Attributes:
        label: Main text. Put a newline character where the line should break;
            text does not wrap on its own.
        id: Name that edges use to refer to this box. Only needed when an
            edge connects to it. Must be unique within a diagram.
        subtitle: Smaller text shown under the label.
        eyebrow: Short line shown above the label, such as a category or step
            name.
        role: Name of the theme role that supplies colours.
        width: Fixed width in units, or ``None`` to size from the text.
        height: Fixed height in units, or ``None`` to size from the text.
        text_align: Horizontal alignment of every line of text, or ``None`` for
            the theme's ``text_align``.
        text_valign: Vertical placement of the text, ``"top"`` or
            ``"center"``, or ``None`` for the theme's ``text_valign``.
        fill: Overrides the role's fill colour.
        stroke: Overrides the role's outline colour.
        text_color: Overrides the role's text colour. It colours the label,
            and the eyebrow and subtitle when neither the box nor the role
            gives them a colour of their own.
        eyebrow_color: Overrides the role's eyebrow colour.
        subtitle_color: Overrides the role's subtitle colour.
        line_width: Overrides the theme's outline width, in points.
        corner_radius: Overrides the theme's corner radius, in units.
    """

    kind: Literal["box"] = "box"
    label: str = Field(min_length=1)
    id: str | None = Field(default=None, min_length=1)
    subtitle: str | None = None
    eyebrow: str | None = Field(default=None, min_length=1)
    role: str = "default"
    width: Positive | None = None
    height: Positive | None = None
    text_align: TextAlign | None = None
    text_valign: TextVAlign | None = None
    fill: Colour | None = None
    stroke: Colour | None = None
    text_color: Colour | None = None
    eyebrow_color: Colour | None = None
    subtitle_color: Colour | None = None
    line_width: Positive | None = None
    corner_radius: NonNegative | None = None


class Spacer(Spec):
    """Empty space inside a Row or Column, used to line things up.

    Attributes:
        size: Space along the parent's main axis, in units. A Spacer in a
            Row adds width; in a Column it adds height. The parent's ``gap``
            is not added on either side of a Spacer, so it adds exactly
            ``size``.
    """

    kind: Literal["spacer"] = "spacer"
    size: NonNegative


class _Container(Spec):
    """Fields shared by Row and Column.

    Containers only arrange their children. They draw no fill, border or title.

    Attributes:
        children: One or more boxes, spacers or nested containers.
        gap: Space between adjacent children in units, or ``None`` for the
            theme's gap. No gap is added next to a Spacer.
        align: How children line up on the cross axis.
        padding: Space around the children, in units.
        uniform: When true, direct Box children share one size: every width
            that is not fixed becomes the largest such width in the group,
            and likewise for heights. Fixed widths and heights keep their
            value and do not count towards the largest. Nested containers and
            spacers are unaffected.
    """

    children: FrozenSeq["Child"] = Field(min_length=1)
    gap: NonNegative | None = None
    align: Align = "center"
    padding: NonNegative = 0.0
    uniform: bool = False


class Row(_Container):
    """Children laid out left to right."""

    kind: Literal["row"] = "row"


class Column(_Container):
    """Children laid out top to bottom."""

    kind: Literal["column"] = "column"


Child = Annotated[Box | Spacer | Row | Column, Field(discriminator="kind")]
"""Anything that can sit inside a Row or Column."""

Row.model_rebuild()
Column.model_rebuild()


class Edge(Spec):
    """An arrow between two boxes, referred to by their ``id``.

    Attributes:
        src: ``id`` of the box the edge leaves.
        dst: ``id`` of the box the edge arrives at.
        exit: Side of ``src`` to leave from, or ``None`` to choose automatically.
        entry: Side of ``dst`` to arrive at, or ``None`` to choose automatically.
        routing: ``"straight"``, ``"elbow"``, or ``"auto"`` to pick by geometry.
        label: Text shown beside the edge.
        style: Line style.
        arrow: Where arrowheads are drawn.
        color: Overrides the theme's edge colour.
        line_width: Overrides the theme's edge width, in points.
    """

    src: str = Field(min_length=1)
    dst: str = Field(min_length=1)
    exit: Side | None = None
    entry: Side | None = None
    routing: Literal["auto", "straight", "elbow"] = "auto"
    label: str | None = None
    style: EdgeStyle = "solid"
    arrow: Literal["end", "both", "none"] = "end"
    color: Colour | None = None
    line_width: Positive | None = None


def iter_boxes(node: Child) -> Iterator[Box]:
    """Yield every box at or below ``node``, depth first in layout order.

    Args:
        node: A box, spacer or container to walk.

    Yields:
        Each ``Box`` found, in the order its parent lists it.
    """
    if isinstance(node, Box):
        yield node
    elif isinstance(node, Row | Column):
        for child in node.children:
            yield from iter_boxes(child)
