"""Write a diagram to a PNG, SVG or PDF file.

The file type comes from the path's extension. Saving renders the diagram
afresh and writes it with the same ``rc_params`` as rendering, so the user's
own matplotlib settings cannot change the file.

Output is deterministic: saving the same diagram twice gives the same bytes,
in any process. SVG ids use a fixed salt, and ``EXPORT_METADATA`` leaves out
the dates and the matplotlib version that files would otherwise carry. The
bytes can still change between matplotlib or FreeType versions.
"""

import math
import os
from pathlib import Path
from typing import IO, Any, Literal, get_args

from matplotlib import rc_context
from matplotlib.figure import Figure

from flowgram.diagram import Diagram
from flowgram.render import rc_params, render

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

CREATOR = "flowgram"
"""The program named in each file's metadata, without a version."""

EXPORT_METADATA: dict[ExportFormat, dict[str, Any]] = {
    "png": {"Software": CREATOR},
    "svg": {"Creator": CREATOR, "Date": None},
    "pdf": {"Creator": CREATOR, "Producer": None, "CreationDate": None},
}
"""Metadata written into each file type. ``None`` leaves a key out."""


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
    with rc_context(settings):
        figure.savefig(
            target,
            format=fmt,
            dpi=dpi,
            transparent=transparent,
            metadata=EXPORT_METADATA[fmt],
        )


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
    slide software. The file names the theme's font, so a machine without
    that font shows a substitute whose widths can differ and push text past
    its box. ``embed_fonts=True`` turns the text into paths instead: it looks
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
