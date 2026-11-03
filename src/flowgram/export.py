"""Write a diagram to a PNG, SVG or PDF file, or show it in Jupyter.

The file type comes from the path's extension. Saving renders the diagram
afresh and writes it with the same ``rc_params`` as rendering, so the user's
own matplotlib settings cannot change the file.

SVG text is kept as text, and each text element names the theme's font then
its ``font_fallbacks``, so a viewer without the font picks a close one.

Output is deterministic: saving the same diagram twice gives the same bytes,
in any process. SVG ids use a fixed salt, and ``EXPORT_METADATA`` leaves out
the dates and the matplotlib version that files would otherwise carry. The
bytes can still change between matplotlib or FreeType versions.
"""

import io
import math
import os
import re
from pathlib import Path
from typing import IO, Any, Literal, get_args

from matplotlib import rc_context
from matplotlib.figure import Figure

from flowgram.diagram import Diagram
from flowgram.render import FIGURE_DPI, rc_params, render
from flowgram.theme import GENERIC_FONT_FAMILIES, Theme

ExportFormat = Literal["png", "svg", "pdf"]
"""A file type that ``save`` can write."""

EXPORT_FORMATS: tuple[ExportFormat, ...] = get_args(ExportFormat)
"""Every file type ``save`` can write, by extension without the dot."""

DEFAULT_DPI = 300.0
"""Resolution of saved PNGs.

A 16:9 slide is 13.33 inches wide, so a diagram filling it at 300 dpi is
4000 pixels across: sharp on a 4K screen or projector, and in print. SVG and
PDF are vector files and ignore it, except for any raster content.
"""
DISPLAY_DPI = 2 * FIGURE_DPI
"""Resolution of the PNG a notebook shows.

It is drawn at twice the size it is shown, so it stays sharp on high-density
screens. The notebook is told the size to show it at, ``FIGURE_DPI`` pixels
per inch, which matches a figure shown by matplotlib's inline backend.
"""

MIME_TYPES: dict[ExportFormat, str] = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}
"""The media type of each file type."""

CREATOR = "flowgram"
"""The program named in each file's metadata, without a version."""

EXPORT_METADATA: dict[ExportFormat, dict[str, Any]] = {
    "png": {"Software": CREATOR},
    "svg": {"Creator": CREATOR, "Date": None},
    "pdf": {"Creator": CREATOR, "Producer": None, "CreationDate": None},
}
"""Metadata written into each file type. ``None`` leaves a key out."""


_SVG_TEXT_STYLE = re.compile(r'(<text\b[^>]*?\bstyle=")([^"]*)(")')
"""The style attribute of a ``<text>`` element. Text content cannot match,
because the SVG escapes ``<`` there."""
_FONT_FAMILY = re.compile(r"(font-family: )[^;]*")
"""The font list as recent matplotlib writes it."""
_FONT_SHORTHAND = re.compile(r"(\bfont: [^;]*?px )[^;]*")
"""The font list at the end of the ``font`` shorthand that older matplotlib,
such as 3.8, writes instead: ``font: 700 11px 'DejaVu Sans'``."""


def css_font_family(theme: Theme) -> str:
    """Return the CSS ``font-family`` list an SVG names for a theme's text.

    It is ``theme.font_family`` then ``theme.font_fallbacks``, without
    repeats. Specific names are quoted and generic families are not.

    Args:
        theme: Supplies the font and its fallbacks.

    Returns:
        A value such as ``'DejaVu Sans', 'Verdana', sans-serif``.
    """
    names = dict.fromkeys([theme.font_family, *theme.font_fallbacks])
    return ", ".join(
        name if name in GENERIC_FONT_FAMILIES else f"'{name}'" for name in names
    )


def add_font_fallbacks(svg: str, theme: Theme) -> str:
    """Return an SVG with each text element's font list set from the theme.

    matplotlib names only the font it drew with. Viewers that lack that font
    then substitute their own default, so this names the fallbacks too.

    Args:
        svg: An SVG written by matplotlib with ``svg.fonttype`` ``"none"``.
        theme: Supplies the font and its fallbacks.

    Returns:
        The SVG with every ``font-family`` replaced.
    """
    family = css_font_family(theme)

    def restyle(match: re.Match[str]) -> str:
        style = match[2]
        for pattern in (_FONT_FAMILY, _FONT_SHORTHAND):
            style = pattern.sub(lambda found: found[1] + family, style)
        return match[1] + style + match[3]

    return _SVG_TEXT_STYLE.sub(restyle, svg)


def export_format(path: str | os.PathLike[str]) -> ExportFormat:
    """Return the file type to write for ``path``, from its extension.

    The extension is not case sensitive.

    Args:
        path: The file to write.

    Returns:
        ``"png"``, ``"svg"`` or ``"pdf"``.

    Raises:
        ValueError: If the extension is missing or not one of those three.
    """
    suffix = Path(path).suffix.lower().removeprefix(".")
    for name in EXPORT_FORMATS:
        if suffix == name:
            return name
    choices = ", ".join(f".{name}" for name in EXPORT_FORMATS)
    found = f"extension .{suffix}" if suffix else "no file extension"
    msg = f"cannot save {os.fspath(path)!r}: it has {found}; use one of {choices}"
    raise ValueError(msg)


def write_figure(
    figure: Figure,
    diagram: Diagram,
    target: str | os.PathLike[str] | IO[bytes],
    fmt: ExportFormat,
    *,
    dpi: float = DEFAULT_DPI,
    transparent: bool = False,
    embed_fonts: bool = False,
) -> None:
    """Write a rendered diagram's figure to a file or binary stream.

    The file's metadata is ``EXPORT_METADATA[fmt]``, so it holds no date.
    SVG text names the theme's font and then its fallbacks.

    Args:
        figure: The figure from ``render(diagram)``.
        diagram: Supplies the theme for the render settings.
        target: A path, or a binary stream such as ``io.BytesIO``.
        fmt: The file type to write.
        dpi: Pixels per inch for PNG output.
        transparent: Leave the background out, so only the diagram is drawn.
        embed_fonts: Turn SVG text into paths.

    Raises:
        ValueError: If ``dpi`` is not a positive, finite number.
    """
    if not (math.isfinite(dpi) and dpi > 0):
        msg = f"dpi must be a positive number, got {dpi!r}"
        raise ValueError(msg)
    settings = rc_params(diagram.theme)
    if embed_fonts:
        settings["svg.fonttype"] = "path"
    buffer = io.BytesIO()
    with rc_context(settings):
        figure.savefig(
            buffer,
            format=fmt,
            dpi=dpi,
            transparent=transparent,
            metadata=EXPORT_METADATA[fmt],
        )
    data = buffer.getvalue()
    if fmt == "svg" and not embed_fonts:
        data = add_font_fallbacks(data.decode("utf-8"), diagram.theme).encode("utf-8")
    if isinstance(target, str | os.PathLike):
        Path(target).write_bytes(data)
    else:
        target.write(data)


def save(
    diagram: Diagram,
    path: str | os.PathLike[str],
    *,
    dpi: float = DEFAULT_DPI,
    transparent: bool = False,
    embed_fonts: bool = False,
) -> None:
    """Render a diagram and write it to ``path``.

    The file type comes from the extension: ``.png``, ``.svg`` or ``.pdf``.
    The page is the figure ``render`` builds, at ``scale`` inches per unit,
    with nothing cropped.

    SVG text is kept as text, so it stays editable in a vector editor or
    slide software. The file names the theme's font, then its
    ``font_fallbacks``. A machine without the font uses the first fallback
    it has; the default, Verdana, is within about 2% of DejaVu Sans's
    width. ``embed_fonts=True`` turns the text into paths instead: it looks
    the same everywhere but can no longer be edited as text. PDF always
    embeds its fonts, and PNG is pixels, so the option only affects SVG.

    Args:
        diagram: The diagram to save.
        path: The file to write. An existing file is replaced.
        dpi: Pixels per inch for PNG output.
        transparent: Leave the background out, so only the diagram is drawn.
            A theme with no ``background`` is transparent already.
        embed_fonts: Turn SVG text into paths.

    Raises:
        ValueError: If the extension is not a supported file type or
            ``dpi`` is not a positive number.
    """
    fmt = export_format(path)
    write_figure(
        render(diagram),
        diagram,
        path,
        fmt,
        dpi=dpi,
        transparent=transparent,
        embed_fonts=embed_fonts,
    )


def to_png(
    diagram: Diagram, *, dpi: float = DEFAULT_DPI, transparent: bool = False
) -> bytes:
    """Render a diagram as PNG bytes, as ``save`` would write them.

    Args:
        diagram: The diagram to draw.
        dpi: Pixels per inch.
        transparent: Leave the background out.

    Returns:
        The PNG file's bytes.
    """
    buffer = io.BytesIO()
    write_figure(
        render(diagram), diagram, buffer, "png", dpi=dpi, transparent=transparent
    )
    return buffer.getvalue()


def to_svg(
    diagram: Diagram, *, transparent: bool = False, embed_fonts: bool = False
) -> str:
    """Render a diagram as SVG text, as ``save`` would write it.

    Args:
        diagram: The diagram to draw.
        transparent: Leave the background out.
        embed_fonts: Turn text into paths.

    Returns:
        The SVG document.
    """
    buffer = io.BytesIO()
    write_figure(
        render(diagram),
        diagram,
        buffer,
        "svg",
        transparent=transparent,
        embed_fonts=embed_fonts,
    )
    return buffer.getvalue().decode("utf-8")


def mimebundle(diagram: Diagram) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return what a notebook needs to show a diagram.

    The format is ``diagram.display_format``. A PNG is drawn at
    ``DISPLAY_DPI`` and comes with the size to show it at, so it appears at
    the size matplotlib would show the figure, at twice the pixels.

    Args:
        diagram: The diagram to show.

    Returns:
        The data, keyed by media type, and its display metadata.
    """
    if diagram.display_format == "svg":
        return {MIME_TYPES["svg"]: to_svg(diagram)}, {}
    figure = render(diagram)
    buffer = io.BytesIO()
    write_figure(figure, diagram, buffer, "png", dpi=DISPLAY_DPI)
    width, height = figure.get_size_inches() * FIGURE_DPI
    size = {"width": round(width), "height": round(height)}
    return {MIME_TYPES["png"]: buffer.getvalue()}, {MIME_TYPES["png"]: size}
