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

from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text

from flowgram._base import FontWeight, TextAlign
from flowgram._text import (
    LINE_SPACING,
    POINTS_PER_INCH,
    TIER_GAP,
    TierKind,
    measure_text,
    text_size,
)
from flowgram.components import Box, Child, Column, Row
from flowgram.diagram import Diagram
from flowgram.layout import Layout, NodePath, Rect
from flowgram.layout import layout as compute_layout
from flowgram.theme import Theme

if TYPE_CHECKING:
    from matplotlib.typing import RcKeyType

FIGURE_DPI = 100.0
"""Resolution of a rendered figure on screen. Saving can choose its own."""

SVG_HASH_SALT = "flowgram"
"""Fixed salt for SVG element ids, so one diagram always gives the same SVG."""

TITLE_GAP = 1.0
"""Space between the title band and the content, in title font sizes."""

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


@dataclass(frozen=True, slots=True)
class TitleLine:
    """The diagram title or subtitle, measured in units.

    Attributes:
        text: What the line says. It may contain newlines.
        size: Font size in points.
        weight: ``"normal"`` or ``"bold"``.
        top: Distance from the top of the band to the top of this line.
        width: Width of the widest line of text.
        height: Height of all its lines of text.
    """

    text: str
    size: float
    weight: FontWeight
    top: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class TitleBand:
    """The measured title and subtitle, stacked above the content.

    Attributes:
        lines: The title, the subtitle, or both, top to bottom.
        width: Width of the wider line.
        height: Height of the lines and the space between them, not counting
            the ``TITLE_GAP`` between the band and the content.
        gap: Space between the band and the content, in units.
    """

    lines: tuple[TitleLine, ...]
    width: float
    height: float
    gap: float


def title_band(diagram: Diagram) -> TitleBand | None:
    """Measure the diagram's title and subtitle.

    The title uses ``theme.title_size`` and ``theme.title_weight``, and the
    subtitle uses ``theme.subtitle_size`` and ``theme.subtitle_weight``. The
    subtitle sits ``TIER_GAP`` title sizes below the title, as box tiers do.

    Args:
        diagram: Supplies the title, subtitle, theme and scale.

    Returns:
        The band, or ``None`` when the diagram has no title or subtitle.
    """
    theme = diagram.theme
    to_units = 1 / (POINTS_PER_INCH * diagram.scale)
    specs: list[tuple[str | None, float, FontWeight]] = [
        (diagram.title, theme.title_size, theme.title_weight),
        (diagram.subtitle, theme.subtitle_size, theme.subtitle_weight),
    ]
    lines: list[TitleLine] = []
    top = 0.0
    for text, size, weight in specs:
        if not text:
            continue
        if lines:
            top += theme.title_size * TIER_GAP * to_units
        width, height = text_size(text, size, weight, theme.font_family, diagram.scale)
        lines.append(TitleLine(text, size, weight, top, width, height))
        top += height
    if not lines:
        return None
    return TitleBand(
        lines=tuple(lines),
        width=max(line.width for line in lines),
        height=top,
        gap=theme.title_size * TITLE_GAP * to_units,
    )


def _spread(align: TextAlign, extra: float) -> tuple[float, float]:
    """Split ``extra`` width into space before and after, by alignment."""
    if align == "left":
        return 0.0, extra
    if align == "right":
        return extra, 0.0
    return extra / 2, extra / 2


def frame(diagram: Diagram, layout: Layout) -> Frame:
    """Return the area to show: the title band, the content and padding.

    The content keeps its layout coordinates. The title band, when there is
    one, is added above it, so ``top`` moves up by the band's height and
    ``TITLE_GAP``. A title wider than the content widens the frame. The
    content then lines up with the title by ``theme.title_align``: it stays
    on the left, sits in the middle, or moves to the right.

    Args:
        diagram: Supplies the padding, title and theme.
        layout: The diagram's layout, from ``flowgram.layout.layout``.

    Returns:
        The frame, in layout units.
    """
    pad = diagram.padding
    band = title_band(diagram)
    if band is None:
        return Frame(-pad, -pad, layout.width + pad, layout.height + pad)
    extra = max(band.width - layout.width, 0.0)
    before, after = _spread(diagram.theme.title_align, extra)
    return Frame(
        -pad - before,
        -pad - band.gap - band.height,
        layout.width + after + pad,
        layout.height + pad,
    )


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


def draw_title(axes: Axes, diagram: Diagram, frame: Frame) -> tuple[Text, ...]:
    """Draw the diagram's title and subtitle at the top of ``frame``.

    The lines sit one padding in from the top and sides of the frame and are
    aligned across it by ``theme.title_align``. Their colour is
    ``theme.title_color``, or the ``default`` role's text colour when that is
    ``None``.

    Args:
        axes: Axes set up by ``setup_axes`` to show ``frame``.
        diagram: Supplies the title, subtitle, theme and padding.
        frame: The frame from ``frame(diagram, layout)``.

    Returns:
        The text artists added, title first. Empty when there is no title or
        subtitle.
    """
    band = title_band(diagram)
    if band is None:
        return ()
    theme = diagram.theme
    pad = diagram.padding
    align = theme.title_align
    inner = Rect(frame.left + pad, frame.top, frame.width - 2 * pad, frame.height)
    x = _text_x(inner, align, 0.0)
    color = theme.title_color or theme.roles["default"].text
    return tuple(
        axes.text(
            x,
            frame.top + pad + line.top,
            line.text,
            color=color,
            fontfamily=theme.font_family,
            fontsize=line.size,
            fontweight=line.weight,
            horizontalalignment=align,
            multialignment=align,
            verticalalignment="top",
            linespacing=LINE_SPACING,
            parse_math=False,
            zorder=Z_BOX_TEXT,
        )
        for line in band.lines
    )


def render(diagram: Diagram) -> Figure:
    """Lay out and draw a diagram into a new figure.

    The figure is sized to the content, the title band and the padding, at
    ``scale`` inches per unit, and drawn with ``rc_params(theme)``. It is
    built without pyplot, so it is not shown or tracked by pyplot. Display
    it in Jupyter as the cell's result, or save it with ``savefig``.

    Args:
        diagram: The diagram to draw.

    Returns:
        A new figure holding the whole diagram.
    """
    result = compute_layout(diagram)
    view = frame(diagram, result)
    with rc_context(rc_params(diagram.theme)):
        figure, axes = new_figure(diagram, view)
        draw_boxes(axes, diagram, result)
        draw_title(axes, diagram, view)
    return figure


def draw(diagram: Diagram, axes: Axes) -> None:
    """Draw a diagram into an existing axes, such as one subplot of a figure.

    The figure is not created or resized. The axes is set to show the whole
    diagram with equal aspect and its axis turned off. Font sizes stay in
    points, so text fits its boxes exactly only when the axes is
    ``scale`` inches per unit, as in ``render``. The theme background is not
    drawn, because the figure belongs to the caller.

    Args:
        diagram: The diagram to draw.
        axes: Where to draw it.
    """
    result = compute_layout(diagram)
    view = frame(diagram, result)
    with rc_context(rc_params(diagram.theme)):
        draw_boxes(axes, diagram, result)
        draw_title(axes, diagram, view)
    setup_axes(axes, view)
    axes.set_aspect("equal")
