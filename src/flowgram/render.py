"""Turn a laid-out diagram into a matplotlib figure.

The renderer never uses pyplot. It builds ``Figure`` objects directly, so
rendering has no global state and behaves the same in scripts, notebooks and
servers.

Drawing uses the layout's own coordinates. The axes are set up in abstract
units with the origin at the top left of the content and y increasing
downward, and the figure is ``scale`` inches per unit. A diagram ``n`` units
wide is therefore ``n * scale`` inches wide, and text measured in points
during layout fits the boxes it was measured for.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text

from flowgram._base import FontWeight, TextAlign
from flowgram._text import LINE_SPACING, TierKind, measure_text
from flowgram.components import Box, Child, Column, Row
from flowgram.diagram import Diagram
from flowgram.layout import Layout, NodePath, Rect
from flowgram.theme import Theme

if TYPE_CHECKING:
    from matplotlib.typing import RcKeyType

FIGURE_DPI = 100.0
"""Resolution of a rendered figure on screen. Saving can choose its own."""

SVG_HASH_SALT = "flowgram"
"""Fixed salt for SVG element ids, so one diagram always gives the same SVG."""

Z_EDGE = 1.0
"""Edges sit under boxes, so a line that crosses a box is hidden by its fill."""

Z_BOX = 2.0
"""Box outlines and fills."""

Z_BOX_TEXT = 3.0
"""Box eyebrows, labels and subtitles, above their box."""

Z_EDGE_LABEL = 4.0
"""Edge labels, above everything so a crossing box never hides one."""


def rc_params(theme: Theme) -> "dict[RcKeyType, Any]":
    """Return the matplotlib settings that every render uses.

    Rendering applies them with ``matplotlib.rc_context``. The user's own
    settings, such as a style sheet or a custom ``matplotlibrc``, then cannot
    change how a diagram looks, and nothing leaks into their other figures.

    - Text uses the theme's font family and is never parsed as mathtext or
      sent to LaTeX, so a label such as ``"$5 to $10"`` is drawn as written.
    - Paths are not simplified, so outlines are drawn exactly.
    - SVG ids use a fixed salt, and SVG text stays as editable text.
    - PDF and PostScript embed TrueType fonts, which slide software can edit.

    Args:
        theme: Supplies the font family.

    Returns:
        Settings for ``matplotlib.rc_context``.
    """
    return {
        "font.family": theme.font_family,
        "text.parse_math": False,
        "text.usetex": False,
        "path.simplify": False,
        "svg.hashsalt": SVG_HASH_SALT,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }


@dataclass(frozen=True, slots=True)
class Frame:
    """The visible area of a rendered diagram, in layout units.

    Coordinates are the layout's, with the origin at the top left of the
    content and y increasing downward. The frame adds the diagram's padding
    around the content, so ``left`` and ``top`` are usually negative.

    Attributes:
        left: x of the left edge.
        top: y of the top edge.
        right: x of the right edge.
        bottom: y of the bottom edge.
    """

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        """Width of the frame in units."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Height of the frame in units."""
        return self.bottom - self.top


def frame(diagram: Diagram, layout: Layout) -> Frame:
    """Return the area to show: the laid-out content plus diagram padding.

    Args:
        diagram: Supplies the padding.
        layout: The diagram's layout, from ``flowgram.layout.layout``.

    Returns:
        The frame, in layout units.
    """
    pad = diagram.padding
    return Frame(-pad, -pad, layout.width + pad, layout.height + pad)


def setup_axes(axes: Axes, frame: Frame) -> None:
    """Show exactly ``frame`` in ``axes``, with y increasing downward.

    The y limits are given bottom first, which inverts the axis, so layout
    coordinates can be drawn as they are. The axis, ticks and axes
    background are hidden.

    Args:
        axes: The axes to set up.
        frame: The area to show.
    """
    axes.set_xlim(frame.left, frame.right)
    axes.set_ylim(frame.bottom, frame.top)
    axes.set_axis_off()


def new_figure(diagram: Diagram, frame: Frame) -> tuple[Figure, Axes]:
    """Create a figure sized to ``frame`` with one axes covering all of it.

    The figure is ``scale`` inches per unit. Its background is the theme's
    ``background``, or transparent when that is ``None``. Call this inside
    ``matplotlib.rc_context(rc_params(theme))`` so the render settings apply.

    Args:
        diagram: Supplies ``scale`` and the theme background.
        frame: The area the figure shows.

    Returns:
        The new figure and its axes.

    Raises:
        ValueError: If the frame has no width or no height, which happens
            when the content and padding are both empty along one axis.
    """
    if frame.width <= 0 or frame.height <= 0:
        msg = (
            f"the diagram has nothing to draw: it is {frame.width:g} x "
            f"{frame.height:g} units including padding; give it a box or "
            "some padding"
        )
        raise ValueError(msg)
    background = diagram.theme.background
    figure = Figure(
        figsize=(frame.width * diagram.scale, frame.height * diagram.scale),
        dpi=FIGURE_DPI,
        facecolor="none" if background is None else background,
    )
    axes = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    setup_axes(axes, frame)
    return figure, axes


@dataclass(frozen=True, slots=True)
class BoxLook:
    """The resolved style of one box: what is actually drawn.

    Attributes:
        fill: Background colour.
        stroke: Outline colour.
        text: Label and subtitle colour.
        eyebrow: Eyebrow colour.
        line_width: Outline width in points.
        corner_radius: Corner radius in units.
        text_align: Horizontal alignment of every line of text.
    """

    fill: str
    stroke: str
    text: str
    eyebrow: str
    line_width: float
    corner_radius: float
    text_align: TextAlign


def box_look(box: Box, theme: Theme) -> BoxLook:
    """Resolve a box's style from its overrides, its role and the theme.

    Each field takes the box's own value when set, then the theme role's,
    then the theme's. The eyebrow colour falls back to the role's eyebrow
    colour and then to the box's text colour, so overriding ``text_color``
    alone recolours all of the box's text.

    Args:
        box: The box to style. Its ``role`` must exist in ``theme``, which
            ``Diagram`` validation guarantees.
        theme: Supplies the role colours and defaults.

    Returns:
        The style to draw the box with.
    """
    role = theme.roles[box.role]
    text = box.text_color or role.text
    return BoxLook(
        fill=box.fill or role.fill,
        stroke=box.stroke or role.stroke,
        text=text,
        eyebrow=box.eyebrow_color or role.eyebrow or text,
        line_width=theme.line_width if box.line_width is None else box.line_width,
        corner_radius=(
            theme.corner_radius if box.corner_radius is None else box.corner_radius
        ),
        text_align=theme.text_align if box.text_align is None else box.text_align,
    )


@dataclass(frozen=True, slots=True)
class DrawnBox:
    """The artists drawn for one box.

    Attributes:
        patch: The rounded rectangle.
        texts: One text artist per tier present, top to bottom: eyebrow,
            label, subtitle.
    """

    patch: FancyBboxPatch
    texts: tuple[Text, ...]


def _text_x(rect: Rect, align: TextAlign, inset: float) -> float:
    if align == "left":
        return rect.x + inset
    if align == "right":
        return rect.right - inset
    return rect.center[0]


def _tier_font(kind: TierKind, theme: Theme) -> tuple[float, FontWeight]:
    fonts: dict[TierKind, tuple[float, FontWeight]] = {
        "eyebrow": (theme.eyebrow_size, theme.eyebrow_weight),
        "label": (theme.label_size, theme.label_weight),
        "subtitle": (theme.subtitle_size, theme.subtitle_weight),
    }
    return fonts[kind]


def draw_box(axes: Axes, box: Box, rect: Rect, theme: Theme, scale: float) -> DrawnBox:
    """Draw one box and its text into ``axes``.

    The box is a rounded rectangle filling ``rect``, with its corner radius
    capped at half the shorter side. The text is measured exactly as layout
    measured it and the stack of tiers is centred vertically in the box, each
    tier at the offset the measurement gave it. Left- and right-aligned text
    is inset by ``theme.text_padding``.

    Args:
        axes: Axes set up by ``setup_axes``, in layout units with y down.
        box: The box to draw.
        rect: Where the layout placed it.
        theme: Supplies fonts, colours and defaults.
        scale: Inches per unit, as in ``Diagram.scale``, used to measure the
            text in units.

    Returns:
        The patch and text artists that were added.
    """
    look = box_look(box, theme)
    radius = min(look.corner_radius, rect.width / 2, rect.height / 2)
    style = f"round,pad=0,rounding_size={radius!r}" if radius > 0 else "square,pad=0"
    patch = FancyBboxPatch(
        (rect.x, rect.y),
        rect.width,
        rect.height,
        boxstyle=style,
        facecolor=look.fill,
        edgecolor=look.stroke,
        linewidth=look.line_width,
        zorder=Z_BOX,
    )
    axes.add_patch(patch)

    block = measure_text(
        box.label, theme, scale, subtitle=box.subtitle, eyebrow=box.eyebrow
    )
    top = rect.y + (rect.height - block.height) / 2
    x = _text_x(rect, look.text_align, theme.text_padding)
    texts: list[Text] = []
    for tier in block.tiers:
        size, weight = _tier_font(tier.kind, theme)
        texts.append(
            axes.text(
                x,
                top + tier.top,
                tier.text,
                color=look.eyebrow if tier.kind == "eyebrow" else look.text,
                fontfamily=theme.font_family,
                fontsize=size,
                fontweight=weight,
                horizontalalignment=look.text_align,
                multialignment=look.text_align,
                verticalalignment="top",
                linespacing=LINE_SPACING,
                parse_math=False,
                zorder=Z_BOX_TEXT,
            )
        )
    return DrawnBox(patch=patch, texts=tuple(texts))


def _boxes(node: Child, path: NodePath) -> Iterator[tuple[NodePath, Box]]:
    if isinstance(node, Box):
        yield path, node
    elif isinstance(node, Row | Column):
        for index, child in enumerate(node.children):
            yield from _boxes(child, (*path, index))


def draw_boxes(
    axes: Axes, diagram: Diagram, layout: Layout
) -> dict[NodePath, DrawnBox]:
    """Draw every box of a diagram at its laid-out position.

    Args:
        axes: Axes set up by ``setup_axes``.
        diagram: Supplies the boxes, theme and scale.
        layout: The diagram's layout.

    Returns:
        The artists drawn for each box, keyed by node path.
    """
    return {
        path: draw_box(axes, box, layout.rect(path), diagram.theme, diagram.scale)
        for path, box in _boxes(diagram.root, ())
    }
