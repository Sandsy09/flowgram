"""The root of a diagram spec, and the checks that tie its parts together."""

import os
from collections import Counter
from difflib import get_close_matches
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import ConfigDict, Field, model_validator

from flowgram._base import FrozenSeq, NonNegative, Positive, Spec
from flowgram.components import Box, Column, Edge, Row, iter_boxes
from flowgram.theme import Theme

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def _describe(box: Box) -> str:
    return f"box {box.id!r}" if box.id else f"box labelled {box.label!r}"


class Diagram(Spec):
    """A complete diagram: a layout tree, the edges between its boxes and a theme.

    Placement comes from the ``root`` tree of rows and columns. Edges are a
    flat list that refers to boxes by ``id`` wherever they sit in the tree.
    Construction checks the whole spec and reports every problem at once.

    Attributes:
        root: The top-level Row or Column.
        edges: Arrows between boxes, by ``id``.
        theme: Colours, type and spacing. Defaults to the light theme.
        title: Optional heading above the diagram.
        subtitle: Optional smaller line under the title.
        footnote: Optional note under the content, such as a source or a
            caveat, aligned like the title.
        scale: Inches per abstract unit when the figure is built.
        padding: Margin around the content, in units.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    root: Annotated[Row | Column, Field(discriminator="kind")]
    edges: FrozenSeq[Edge] = ()
    theme: Theme = Field(default_factory=Theme.light)
    title: str | None = None
    subtitle: str | None = None
    footnote: str | None = None
    scale: Positive = 1.0
    padding: NonNegative = 0.5

    def render(self) -> "Figure":
        """Draw the diagram into a new matplotlib figure.

        The figure is sized to fit the diagram, at ``scale`` inches per unit,
        and is built without pyplot. In Jupyter it displays as a cell's
        result. Write it to a file with ``save``.

        Returns:
            A new figure holding the whole diagram.
        """
        # Imported here: the renderer imports this module.
        from flowgram.render import render

        return render(self)

    def save(
        self,
        path: str | os.PathLike[str],
        *,
        dpi: float | None = None,
        transparent: bool = False,
        embed_fonts: bool = False,
    ) -> None:
        """Render the diagram and write it to a PNG, SVG or PDF file.

        The file type comes from the extension, which is not case sensitive.
        The page is the figure ``render`` builds, with nothing cropped.

        SVG text is kept as text, so it stays editable in a vector editor or
        slide software. The file names the theme's font, so a machine
        without that font shows a substitute whose widths can differ.
        ``embed_fonts=True`` turns the text into paths instead: it looks the
        same everywhere but can no longer be edited as text. PDF always
        embeds its fonts and PNG is pixels, so the option only affects SVG.

        Args:
            path: The file to write, ending ``.png``, ``.svg`` or ``.pdf``.
                An existing file is replaced.
            dpi: Pixels per inch for PNG output. ``None`` uses
                ``flowgram.export.DEFAULT_DPI`` (300), sharp on a full-width
                slide on a 4K screen.
            transparent: Leave the background out, so only the diagram is
                drawn. A theme with no ``background`` is transparent already.
            embed_fonts: Turn SVG text into paths.

        Raises:
            ValueError: If the extension is not ``.png``, ``.svg`` or
                ``.pdf``, or ``dpi`` is not a positive number.
        """
        from flowgram.export import DEFAULT_DPI, save

        save(
            self,
            path,
            dpi=DEFAULT_DPI if dpi is None else dpi,
            transparent=transparent,
            embed_fonts=embed_fonts,
        )

    def draw(self, ax: "Axes") -> None:
        """Draw the diagram into an existing matplotlib axes.

        Use this to place a diagram in a subplot next to other plots. The
        figure is not resized. The axes is set to show the whole diagram with
        equal aspect and no axis. Text stays at its point size, so it fits
        its boxes exactly only when the axes is ``scale`` inches per unit.

        Args:
            ax: The axes to draw into.
        """
        from flowgram.render import draw

        draw(self, ax)

    def boxes(self) -> tuple[Box, ...]:
        """Return every box in layout order.

        Returns:
            All boxes in the tree, depth first, in the order each parent
            lists its children.
        """
        return tuple(iter_boxes(self.root))

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        boxes = self.boxes()
        problems = [
            *self._duplicate_ids(boxes),
            *self._unknown_roles(boxes),
            *self._bad_edges(boxes),
        ]
        if problems:
            header = f"{len(problems)} problem(s) in the diagram:"
            raise ValueError("\n".join([header, *(f"- {p}" for p in problems)]))
        return self

    @staticmethod
    def _duplicate_ids(boxes: tuple[Box, ...]) -> list[str]:
        counts = Counter(box.id for box in boxes if box.id is not None)
        return [
            f"box id {box_id!r} is used {count} times; ids must be unique"
            for box_id, count in counts.items()
            if count > 1
        ]

    def _unknown_roles(self, boxes: tuple[Box, ...]) -> list[str]:
        valid = sorted(self.theme.roles)
        return [
            f"{_describe(box)} uses role {box.role!r}, which theme "
            f"{self.theme.name!r} does not define; valid roles: {', '.join(valid)}"
            for box in boxes
            if box.role not in self.theme.roles
        ]

    def _bad_edges(self, boxes: tuple[Box, ...]) -> list[str]:
        known = sorted({box.id for box in boxes if box.id is not None})
        problems: list[str] = []
        for index, edge in enumerate(self.edges):
            where = f"edge {index} ({edge.src!r} -> {edge.dst!r})"
            if edge.src == edge.dst:
                problems.append(f"{where}: self-loops are not supported yet")
            for end, box_id in (("src", edge.src), ("dst", edge.dst)):
                if box_id not in known:
                    problems.append(
                        f"{where}: {end} {box_id!r} matches no box; "
                        f"{self._suggest(box_id, known)}"
                    )
        return problems

    @staticmethod
    def _suggest(box_id: str, known: list[str]) -> str:
        if not known:
            return "no box in the diagram has an id"
        close = get_close_matches(box_id, known, n=3)
        if close:
            return f"closest ids: {', '.join(repr(c) for c in close)}"
        return f"known ids: {', '.join(repr(k) for k in known)}"
