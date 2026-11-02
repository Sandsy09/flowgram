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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from flowgram.diagram import Diagram
from flowgram.layout import Layout
from flowgram.theme import Theme

if TYPE_CHECKING:
    from matplotlib.typing import RcKeyType

FIGURE_DPI = 100.0
"""Resolution of a rendered figure on screen. Saving can choose its own."""

SVG_HASH_SALT = "flowgram"
"""Fixed salt for SVG element ids, so one diagram always gives the same SVG."""


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
