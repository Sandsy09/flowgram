"""Measure box text in abstract units, without drawing anything.

Text is measured with matplotlib's own text layout on an off-screen Agg
canvas, so sizes match what the renderer draws later. Font sizes are in
points and do not follow ``Diagram.scale``: at a larger scale the same text
takes fewer units.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

from flowgram._base import FontWeight
from flowgram.theme import Theme

POINTS_PER_INCH = 72.0
"""Typographic points in one inch."""

LINE_SPACING = 1.2
"""Line spacing inside one tier, as a multiple of the font size."""

TIER_GAP = 0.3
"""Space between the eyebrow, label and subtitle, as a multiple of the label size."""

# Agg snaps text extents to whole pixels. Measuring at ten pixels per point
# keeps that rounding below a tenth of a point.
_DPI = POINTS_PER_INCH * 10

TierKind = Literal["eyebrow", "label", "subtitle"]
"""Which line of box text a tier is."""


@dataclass(frozen=True, slots=True)
class Tier:
    """One measured tier of box text, in units.

    Attributes:
        kind: ``"eyebrow"``, ``"label"`` or ``"subtitle"``.
        text: The tier's text, which may contain newlines.
        top: Distance from the top of the text block to the top of this tier.
        width: Width of the widest line in the tier.
        height: Height of all the tier's lines.
    """

    kind: TierKind
    text: str
    top: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class TextBlock:
    """The measured text of one box, in units.

    Attributes:
        width: Width of the widest tier.
        height: Height of all tiers plus the gaps between them.
        tiers: The tiers present, top to bottom.
    """

    width: float
    height: float
    tiers: tuple[Tier, ...]


@lru_cache(maxsize=1)
def _canvas() -> tuple[Figure, FigureCanvasAgg]:
    figure = Figure(dpi=_DPI)
    return figure, FigureCanvasAgg(figure)


@lru_cache(maxsize=64)
def _check_font(family: str) -> None:
    try:
        font_manager.findfont(
            font_manager.FontProperties(family=family), fallback_to_default=False
        )
    except ValueError:
        msg = (
            f"font family {family!r} is not installed or not known to matplotlib; "
            "use an installed family or the default 'DejaVu Sans'"
        )
        raise ValueError(msg) from None


@lru_cache(maxsize=4096)
def _extent_points(
    text: str, size: float, weight: FontWeight, family: str
) -> tuple[float, float]:
    """Return the ``(width, height)`` of ``text`` in points.

    Both come from matplotlib's own text layout, the same one that draws the
    text later. Width is the extent of ``text`` itself. Height is the extent
    of a stand-in with the same number of lines, each reading ``"lp"``
    (matplotlib's reference line), so every line at a given size and weight
    is the same height whatever its letters, on every matplotlib version.
    Text is never parsed as mathtext, matching the renderer.
    """
    figure, canvas = _canvas()
    props = font_manager.FontProperties(family=family, size=size, weight=weight)
    # matplotlib's stubs leave FigureCanvasAgg.get_renderer unannotated.
    renderer = canvas.get_renderer()  # type: ignore[no-untyped-call]

    def extent(content: str) -> tuple[float, float]:
        artist = Text(
            0,
            0,
            content,
            fontproperties=props,
            linespacing=LINE_SPACING,
            parse_math=False,
        )
        artist.set_figure(figure)
        box = artist.get_window_extent(renderer)
        return box.width, box.height

    width, _ = extent(text)
    lines = text.count("\n") + 1
    _, height = extent("\n".join(["lp"] * lines))
    scale = _DPI / POINTS_PER_INCH
    return width / scale, height / scale


def text_size(
    text: str, size: float, weight: FontWeight, family: str, scale: float
) -> tuple[float, float]:
    """Measure one piece of text in units, such as a diagram title.

    Lines break only at newline characters. Height counts every line at the
    font's full line height, as in ``measure_text``.

    Args:
        text: The text to measure.
        size: Font size in points.
        weight: ``"normal"`` or ``"bold"``.
        family: An installed font family.
        scale: Inches per unit, as in ``Diagram.scale``.

    Returns:
        The text's ``(width, height)`` in units.

    Raises:
        ValueError: If the font family is not installed.
    """
    _check_font(family)
    width, height = _extent_points(text, size, weight, family)
    to_units = 1 / (POINTS_PER_INCH * scale)
    return width * to_units, height * to_units


def measure_text(
    label: str,
    theme: Theme,
    scale: float,
    *,
    subtitle: str | None = None,
    eyebrow: str | None = None,
) -> TextBlock:
    """Measure a box's eyebrow, label and subtitle in units.

    Each tier uses its theme size and weight. Tiers are stacked top to
    bottom with a gap of ``TIER_GAP`` label sizes between them. Missing or
    empty tiers are skipped. Lines break only at newline characters.

    Args:
        label: The main text.
        theme: Supplies the font family, sizes and weights.
        scale: Inches per unit, as in ``Diagram.scale``.
        subtitle: Optional text under the label.
        eyebrow: Optional text above the label.

    Returns:
        The size of the whole block and of each tier, in units.

    Raises:
        ValueError: If the theme's font family is not installed.
    """
    _check_font(theme.font_family)
    to_units = 1 / (POINTS_PER_INCH * scale)
    specs: list[tuple[TierKind, str | None, float, FontWeight]] = [
        ("eyebrow", eyebrow, theme.eyebrow_size, theme.eyebrow_weight),
        ("label", label, theme.label_size, theme.label_weight),
        ("subtitle", subtitle, theme.subtitle_size, theme.subtitle_weight),
    ]
    gap = theme.label_size * TIER_GAP * to_units
    tiers: list[Tier] = []
    top = 0.0
    for kind, text, size, weight in specs:
        if not text:
            continue
        if tiers:
            top += gap
        width, height = _extent_points(text, size, weight, theme.font_family)
        tier = Tier(kind, text, top, width * to_units, height * to_units)
        tiers.append(tier)
        top += tier.height
    width = max(tier.width for tier in tiers) if tiers else 0.0
    return TextBlock(width=width, height=top, tiers=tuple(tiers))
