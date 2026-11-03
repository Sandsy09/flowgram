"""Measure box text in abstract units, without drawing anything.

Widths come from matplotlib's own text layout on an off-screen Agg canvas,
so they match what the renderer draws later. Heights and baselines come from
the font's ascent and descent, not from the letters on each line, so every
line of a given size is the same height and lines sit at an even pitch.
Font sizes are in points and do not follow ``Diagram.scale``: at a larger
scale the same text takes fewer units.
"""

import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

from flowgram._base import FontWeight
from flowgram.theme import Theme

POINTS_PER_INCH = 72.0
"""Typographic points in one inch."""

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


def _typo_metrics(path: str) -> tuple[int, int] | None:
    """Read ``sTypoAscender`` and ``sTypoDescender`` from a font file.

    They live in the ``OS/2`` table of a TrueType or OpenType font, or of
    the first font in a collection. Older matplotlib does not expose them,
    so the table is read directly.

    Returns:
        The two values in font units, or ``None`` when the font has no
        ``OS/2`` table.
    """
    data = Path(path).read_bytes()
    start = 0
    if data[:4] == b"ttcf":
        (start,) = struct.unpack_from(">I", data, 12)
    (tables,) = struct.unpack_from(">H", data, start + 4)
    for index in range(tables):
        tag, _, offset, _ = struct.unpack_from(">4sIII", data, start + 12 + 16 * index)
        if tag == b"OS/2":
            ascent, descent = struct.unpack_from(">hh", data, offset + 68)
            return ascent, descent
    return None


@lru_cache(maxsize=64)
def _font_metrics(family: str, weight: FontWeight) -> tuple[float, float]:
    """Return the font's ``(ascent, descent)`` as fractions of its size.

    These are the typographic metrics from the font's ``OS/2`` table, the
    ones matplotlib 3.11 uses for line height, or FreeType's when the font
    has no such table. Both are positive, and they are the same on every
    matplotlib version.
    """
    path = font_manager.findfont(
        font_manager.FontProperties(family=family, weight=weight)
    )
    font = font_manager.get_font(path)
    metrics = _typo_metrics(path)
    ascent, descent = (font.ascender, font.descender) if metrics is None else metrics
    return ascent / font.units_per_EM, -descent / font.units_per_EM


def _line_height_points(
    size: float, weight: FontWeight, family: str, line_spacing: float
) -> float:
    ascent, descent = _font_metrics(family, weight)
    return line_spacing * (ascent + descent) * size


@lru_cache(maxsize=4096)
def _width_points(text: str, size: float, weight: FontWeight, family: str) -> float:
    """Return the width of the widest line of ``text`` in points.

    It comes from matplotlib's own text layout, the same one that draws the
    text later. Text is never parsed as mathtext, matching the renderer.
    """
    figure, canvas = _canvas()
    props = font_manager.FontProperties(family=family, size=size, weight=weight)
    # matplotlib's stubs leave FigureCanvasAgg.get_renderer unannotated.
    renderer = canvas.get_renderer()  # type: ignore[no-untyped-call]
    artist = Text(0, 0, text, fontproperties=props, parse_math=False)
    artist.set_figure(figure)
    return float(artist.get_window_extent(renderer).width) * POINTS_PER_INCH / _DPI


def _extent_points(
    text: str, size: float, weight: FontWeight, family: str, line_spacing: float
) -> tuple[float, float]:
    """Return the ``(width, height)`` of ``text`` in points."""
    lines = text.count("\n") + 1
    height = lines * _line_height_points(size, weight, family, line_spacing)
    return _width_points(text, size, weight, family), height


def baselines(
    text: str,
    size: float,
    weight: FontWeight,
    family: str,
    scale: float,
    *,
    line_spacing: float,
) -> tuple[float, ...]:
    """Place each line's baseline below the top of the text, in units.

    Every line is ``line_spacing`` times the font's ascent plus descent
    tall, with the extra space split evenly above and below, as in CSS. So
    lines sit at an even pitch, and text of one size and font shares its
    baselines whatever its letters.

    Args:
        text: The text, with lines broken at newline characters.
        size: Font size in points.
        weight: ``"normal"`` or ``"bold"``.
        family: An installed font family.
        scale: Inches per unit, as in ``Diagram.scale``.
        line_spacing: Distance between lines as a multiple of the font's
            height, as in ``Theme.line_spacing``.

    Returns:
        One distance per line, top to bottom.

    Raises:
        ValueError: If the font family is not installed.
    """
    _check_font(family)
    ascent, descent = _font_metrics(family, weight)
    pitch = _line_height_points(size, weight, family, line_spacing)
    first = (pitch - (ascent + descent) * size) / 2 + ascent * size
    to_units = 1 / (POINTS_PER_INCH * scale)
    lines = text.count("\n") + 1
    return tuple((first + k * pitch) * to_units for k in range(lines))


def text_size(
    text: str,
    size: float,
    weight: FontWeight,
    family: str,
    scale: float,
    *,
    line_spacing: float,
) -> tuple[float, float]:
    """Measure one piece of text in units, such as a diagram title.

    Lines break only at newline characters. Every line is
    ``line_spacing`` times the font's ascent plus descent tall, as in
    ``measure_text``.

    Args:
        text: The text to measure.
        size: Font size in points.
        weight: ``"normal"`` or ``"bold"``.
        family: An installed font family.
        scale: Inches per unit, as in ``Diagram.scale``.
        line_spacing: Distance between lines as a multiple of ``size``, as
            in ``Theme.line_spacing``.

    Returns:
        The text's ``(width, height)`` in units.

    Raises:
        ValueError: If the font family is not installed.
    """
    _check_font(family)
    width, height = _extent_points(text, size, weight, family, line_spacing)
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

    Each tier uses its theme size and weight. Each line is
    ``theme.line_spacing`` times the font's ascent plus descent tall, which
    for DejaVu Sans is ``theme.line_spacing`` font sizes. Tiers are stacked
    top to bottom with a gap of ``theme.tier_gap`` label sizes between them.
    Missing or empty tiers are skipped. Lines break only at newline characters.

    Args:
        label: The main text.
        theme: Supplies the font family, sizes, weights and spacing.
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
    gap = theme.label_size * theme.tier_gap * to_units
    tiers: list[Tier] = []
    top = 0.0
    for kind, text, size, weight in specs:
        if not text:
            continue
        if tiers:
            top += gap
        width, height = _extent_points(
            text, size, weight, theme.font_family, theme.line_spacing
        )
        tier = Tier(kind, text, top, width * to_units, height * to_units)
        tiers.append(tier)
        top += tier.height
    width = max(tier.width for tier in tiers) if tiers else 0.0
    return TextBlock(width=width, height=top, tiers=tuple(tiers))
