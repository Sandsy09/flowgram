"""The root of a diagram spec, and the checks that tie its parts together."""

import os
from collections import Counter
from collections.abc import Mapping
from difflib import get_close_matches
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

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
    Load a spec from data with ``from_dict``, ``from_json`` or ``from_yaml``,
    or their file variants, and write it back out, without its defaults, with
    ``to_dict``, ``to_json`` or ``to_yaml``.

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
        display_format: How a notebook shows the diagram: ``"png"`` (the
            default) or ``"svg"``. Files written by ``save`` are not
            affected.
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
    display_format: Literal["png", "svg"] = "png"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Diagram":
        """Build a diagram from plain Python data, such as ``model_dump()`` gives.

        Every component names its ``kind``: ``"row"``, ``"column"``,
        ``"box"`` or ``"spacer"``. The same checks run as when building the
        spec in Python.

        Args:
            data: The spec as nested dicts and lists.

        Returns:
            The checked diagram.

        Raises:
            pydantic.ValidationError: If the data is not a valid spec.
        """
        from flowgram.loading import from_dict

        return from_dict(data)

    @classmethod
    def from_json(cls, text: str | bytes) -> "Diagram":
        """Build a diagram from a JSON document, such as ``model_dump_json()`` gives.

        Args:
            text: The JSON text.

        Returns:
            The checked diagram.

        Raises:
            pydantic.ValidationError: If the text is not valid JSON or not a
                valid spec.
        """
        from flowgram.loading import from_json

        return from_json(text)

    @classmethod
    def from_yaml(cls, text: str) -> "Diagram":
        """Build a diagram from a YAML document.

        Needs the ``yaml`` extra: ``pip install "flowgram[yaml]"``. The
        document is read with PyYAML's safe loader.

        Args:
            text: The YAML text, with a mapping at the top like a JSON spec.

        Returns:
            The checked diagram.

        Raises:
            ImportError: If PyYAML is not installed.
            yaml.YAMLError: If the text is not valid YAML.
            pydantic.ValidationError: If the document is not a valid spec.
        """
        from flowgram.loading import from_yaml

        return from_yaml(text)

    @classmethod
    def from_json_file(cls, path: str | os.PathLike[str]) -> "Diagram":
        """Build a diagram from a UTF-8 JSON file.

        Args:
            path: The file to read.

        Returns:
            The checked diagram.

        Raises:
            OSError: If the file cannot be read.
            pydantic.ValidationError: If the file is not a valid spec.
        """
        from flowgram.loading import from_json_file

        return from_json_file(path)

    @classmethod
    def from_yaml_file(cls, path: str | os.PathLike[str]) -> "Diagram":
        """Build a diagram from a UTF-8 YAML file.

        Needs the ``yaml`` extra: ``pip install "flowgram[yaml]"``.

        Args:
            path: The file to read.

        Returns:
            The checked diagram.

        Raises:
            ImportError: If PyYAML is not installed.
            OSError: If the file cannot be read.
            yaml.YAMLError: If the file is not valid YAML.
            pydantic.ValidationError: If the file is not a valid spec.
        """
        from flowgram.loading import from_yaml_file

        return from_yaml_file(path)

    def to_dict(self) -> dict[str, Any]:
        """Return the spec as plain data, without its defaults.

        Every component keeps its ``kind``, and the theme is left out when
        it is the default, so ``Diagram.from_dict(d.to_dict()) == d``.

        Returns:
            The spec as nested dicts and lists of JSON types.
        """
        from flowgram.loading import to_dict

        return to_dict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        """Return the spec as JSON, without its defaults.

        Args:
            indent: Spaces per level, or ``None`` for one compact line.

        Returns:
            JSON text that ``Diagram.from_json`` loads back equal.
        """
        from flowgram.loading import to_json

        return to_json(self, indent=indent)

    def to_yaml(self) -> str:
        """Return the spec as YAML, without its defaults.

        Needs the ``yaml`` extra: ``pip install "flowgram[yaml]"``.

        Returns:
            YAML text that ``Diagram.from_yaml`` loads back equal.

        Raises:
            ImportError: If PyYAML is not installed.
        """
        from flowgram.loading import to_yaml

        return to_yaml(self)

    def to_json_file(
        self, path: str | os.PathLike[str], *, indent: int | None = 2
    ) -> None:
        """Write the spec to a UTF-8 JSON file, without its defaults.

        Args:
            path: The file to write. An existing file is replaced.
            indent: Spaces per level, or ``None`` for one compact line.

        Raises:
            OSError: If the file cannot be written.
        """
        from flowgram.loading import to_json_file

        to_json_file(self, path, indent=indent)

    def to_yaml_file(self, path: str | os.PathLike[str]) -> None:
        """Write the spec to a UTF-8 YAML file, without its defaults.

        Needs the ``yaml`` extra: ``pip install "flowgram[yaml]"``.

        Args:
            path: The file to write. An existing file is replaced.

        Raises:
            ImportError: If PyYAML is not installed.
            OSError: If the file cannot be written.
        """
        from flowgram.loading import to_yaml_file

        to_yaml_file(self, path)

    def render(self) -> "Figure":
        """Draw the diagram into a new matplotlib figure.

        The figure is sized to fit the diagram, at ``scale`` inches per unit,
        and is built without pyplot. A diagram shows itself in Jupyter, so
        call this only to change the figure or draw more into it. Write a
        file with ``save``.

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

    def to_png(self, *, dpi: float | None = None, transparent: bool = False) -> bytes:
        """Render the diagram as PNG bytes, the same as ``save`` writes.

        Args:
            dpi: Pixels per inch. ``None`` uses
                ``flowgram.export.DEFAULT_DPI`` (300).
            transparent: Leave the background out.

        Returns:
            The PNG file's bytes.

        Raises:
            ValueError: If ``dpi`` is not a positive number.
        """
        from flowgram.export import DEFAULT_DPI, to_png

        return to_png(
            self, dpi=DEFAULT_DPI if dpi is None else dpi, transparent=transparent
        )

    def to_svg(self, *, transparent: bool = False, embed_fonts: bool = False) -> str:
        """Render the diagram as SVG text, the same as ``save`` writes.

        In a notebook, ``IPython.display.SVG(diagram.to_svg())`` shows one
        diagram as SVG. Set ``display_format="svg"`` to show it that way
        every time.

        Args:
            transparent: Leave the background out.
            embed_fonts: Turn text into paths.

        Returns:
            The SVG document.
        """
        from flowgram.export import to_svg

        return to_svg(self, transparent=transparent, embed_fonts=embed_fonts)

    def _repr_mimebundle_(
        self, include: object = None, exclude: object = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Show the diagram as a notebook cell's result.

        IPython and Jupyter call this. The diagram is drawn as a PNG, or as
        an SVG when ``display_format`` is ``"svg"``. IPython itself is not
        needed.

        Args:
            include: Media types the notebook asks for. Not used: the
                notebook drops what it did not ask for.
            exclude: Media types the notebook does not want. Not used.

        Returns:
            The image keyed by its media type, and display metadata.
        """
        from flowgram.export import mimebundle

        return mimebundle(self)

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
