"""Layout results: where every node of a diagram sits, in abstract units.

Layout is computed from a spec without drawing anything. Coordinates use the
spec's abstract units with the origin at the top left and y increasing
downward; the renderer converts them to inches and flips y for matplotlib.

Every node in the layout tree is addressed by its path: the tuple of child
indices from the root, so the root is ``()`` and its second child is ``(1,)``.
Boxes with an ``id`` can also be looked up by that id.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from flowgram._text import measure_text
from flowgram.components import Box, Child, Column, Row, Side, Spacer
from flowgram.theme import Theme

NodePath = tuple[int, ...]
"""Child indices from the root to a node; the root is ``()``."""

Point = tuple[float, float]
"""An ``(x, y)`` position in units, origin top left, y down."""

Size = tuple[float, float]
"""A ``(width, height)`` in units."""


@dataclass(frozen=True, slots=True)
class Rect:
    """An axis-aligned rectangle in units, origin top left, y down.

    Attributes:
        x: Left edge.
        y: Top edge.
        width: Size along x. Zero is allowed, for example the cross-axis size
            of a Spacer.
        height: Size along y. Zero is allowed.

    Raises:
        ValueError: If ``width`` or ``height`` is negative.
    """

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        """Reject a negative width or height."""
        if self.width < 0 or self.height < 0:
            msg = (
                f"rect size must not be negative; got width {self.width} "
                f"and height {self.height}"
            )
            raise ValueError(msg)

    @property
    def right(self) -> float:
        """The x coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """The y coordinate of the bottom edge."""
        return self.y + self.height

    @property
    def center(self) -> Point:
        """The centre point."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def side_midpoint(self, side: Side) -> Point:
        """Return the midpoint of one side, where edges attach.

        Args:
            side: ``"left"``, ``"right"``, ``"top"`` or ``"bottom"``.

        Returns:
            The point halfway along that side.
        """
        cx, cy = self.center
        midpoints: dict[Side, Point] = {
            "left": (self.x, cy),
            "right": (self.right, cy),
            "top": (cx, self.y),
            "bottom": (cx, self.bottom),
        }
        return midpoints[side]


def _format_path(path: NodePath) -> str:
    return "root" if not path else "path " + repr(path)


@dataclass(frozen=True, slots=True)
class Layout:
    """The positioned result of laying out a diagram.

    Build one with the layout functions rather than by hand. The mappings are
    read-only views, so a layout cannot be changed after it is made.

    Attributes:
        width: Width of the content, in units, before diagram padding.
        height: Height of the content, in units, before diagram padding.
        rects: The rectangle of every node (boxes, spacers and containers),
            keyed by node path.
        ids: The node path of every box that has an ``id``, keyed by that id.

    Raises:
        ValueError: If ``width`` or ``height`` is negative, or an id points at
            a path that has no rectangle.
    """

    width: float
    height: float
    rects: Mapping[NodePath, Rect] = field(hash=False)
    ids: Mapping[str, NodePath] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """Check the size and ids, then store read-only copies of the mappings."""
        if self.width < 0 or self.height < 0:
            msg = (
                f"layout size must not be negative; got width {self.width} "
                f"and height {self.height}"
            )
            raise ValueError(msg)
        missing = [
            f"{box_id!r} -> {_format_path(path)}"
            for box_id, path in self.ids.items()
            if path not in self.rects
        ]
        if missing:
            msg = f"box ids point at paths with no rect: {', '.join(missing)}"
            raise ValueError(msg)
        # Copy into read-only views so callers cannot mutate the layout.
        object.__setattr__(self, "rects", MappingProxyType(dict(self.rects)))
        object.__setattr__(self, "ids", MappingProxyType(dict(self.ids)))

    def rect(self, path: NodePath) -> Rect:
        """Return the rectangle of the node at ``path``.

        Args:
            path: Child indices from the root; ``()`` is the root.

        Returns:
            The node's rectangle.

        Raises:
            KeyError: If no node has that path.
        """
        try:
            return self.rects[path]
        except KeyError:
            msg = (
                f"no node at {_format_path(path)}; "
                f"the layout has {len(self.rects)} node(s)"
            )
            raise KeyError(msg) from None

    def box(self, box_id: str) -> Rect:
        """Return the rectangle of the box with this ``id``.

        Args:
            box_id: The ``id`` given to the box in the spec.

        Returns:
            The box's rectangle.

        Raises:
            KeyError: If no box has that id. The message lists the valid ids.
        """
        try:
            path = self.ids[box_id]
        except KeyError:
            if self.ids:
                known = ", ".join(repr(k) for k in sorted(self.ids))
                msg = f"no box has id {box_id!r}; valid ids: {known}"
            else:
                msg = f"no box has id {box_id!r}; no box in the layout has an id"
            raise KeyError(msg) from None
        return self.rects[path]


def box_size(box: Box, theme: Theme, scale: float) -> Size:
    """Return the size of a box in units.

    An automatic dimension is the text's size plus ``theme.text_padding`` on
    each side, but never less than ``theme.min_box_width`` or
    ``theme.min_box_height``. A fixed ``width`` or ``height`` on the box is
    used as given, each independently of the other, even when the text does
    not fit.

    Args:
        box: The box to size.
        theme: Supplies the fonts, padding and minimum sizes.
        scale: Inches per unit, as in ``Diagram.scale``.

    Returns:
        The box's ``(width, height)``.
    """
    if box.width is not None and box.height is not None:
        return (box.width, box.height)
    text = measure_text(
        box.label, theme, scale, subtitle=box.subtitle, eyebrow=box.eyebrow
    )
    pad = 2 * theme.text_padding
    width = box.width
    if width is None:
        width = max(text.width + pad, theme.min_box_width)
    height = box.height
    if height is None:
        height = max(text.height + pad, theme.min_box_height)
    return (width, height)


Container = Row | Column
"""A node that arranges children: the root of a diagram is always one."""


def _gap(node: Container, theme: Theme) -> float:
    return theme.gap if node.gap is None else node.gap


def _gaps(node: Container, theme: Theme) -> list[float]:
    """Return the space before each child after the first.

    A gap sits between two adjacent children only when neither is a Spacer,
    so a Spacer adds exactly its own size.
    """
    gap = _gap(node, theme)
    pairs = zip(node.children, node.children[1:], strict=False)
    return [
        0.0 if isinstance(a, Spacer) or isinstance(b, Spacer) else gap for a, b in pairs
    ]


def _spacer_size(spacer: Spacer, parent: Container) -> Size:
    return (spacer.size, 0.0) if isinstance(parent, Row) else (0.0, spacer.size)


def _size_child(
    node: Child,
    path: NodePath,
    parent: Container,
    theme: Theme,
    scale: float,
    sizes: dict[NodePath, Size],
) -> Size:
    if isinstance(node, Box):
        size = box_size(node, theme, scale)
    elif isinstance(node, Spacer):
        size = _spacer_size(node, parent)
    else:
        size = _size_container(node, path, theme, scale, sizes)
    sizes[path] = size
    return size


def _apply_uniform(
    node: Container,
    path: NodePath,
    children: list[Size],
    sizes: dict[NodePath, Size],
) -> list[Size]:
    """Give every automatic dimension of a direct Box child the group's largest.

    Only dimensions without a fixed value count towards the largest and take
    it, so a fixed width or height is never changed and never stretches the
    others. Spacers and nested containers are left alone.
    """
    boxes = [
        (index, child)
        for index, child in enumerate(node.children)
        if isinstance(child, Box)
    ]
    auto_widths = [children[i][0] for i, box in boxes if box.width is None]
    auto_heights = [children[i][1] for i, box in boxes if box.height is None]
    widest = max(auto_widths, default=0.0)
    tallest = max(auto_heights, default=0.0)
    result = list(children)
    for index, box in boxes:
        width, height = result[index]
        size = (
            widest if box.width is None else width,
            tallest if box.height is None else height,
        )
        result[index] = size
        sizes[(*path, index)] = size
    return result


def _size_container(
    node: Container,
    path: NodePath,
    theme: Theme,
    scale: float,
    sizes: dict[NodePath, Size],
) -> Size:
    children = [
        _size_child(child, (*path, index), node, theme, scale, sizes)
        for index, child in enumerate(node.children)
    ]
    if node.uniform:
        children = _apply_uniform(node, path, children, sizes)
    horizontal = isinstance(node, Row)
    main = [w if horizontal else h for w, h in children]
    cross = [h if horizontal else w for w, h in children]
    pad = 2 * node.padding
    main_total = sum(main) + sum(_gaps(node, theme)) + pad
    cross_total = max(cross) + pad
    return (main_total, cross_total) if horizontal else (cross_total, main_total)


def node_sizes(root: Container, theme: Theme, scale: float) -> dict[NodePath, Size]:
    """Return the size of every node in a layout tree, bottom-up.

    A Row is as wide as its children plus the gaps between them plus
    ``padding`` on both sides, and as tall as its tallest child plus
    ``padding`` above and below. A Column is the transpose. A ``gap`` of
    ``None`` uses ``theme.gap``. A Spacer adds its ``size`` along its parent's
    main axis, has no size across it, and has no gap on either side.

    Args:
        root: The top-level Row or Column.
        theme: Supplies fonts, padding, minimum box sizes and the default gap.
        scale: Inches per unit, as in ``Diagram.scale``.

    Returns:
        ``(width, height)`` in units for every node, keyed by node path.
    """
    sizes: dict[NodePath, Size] = {}
    sizes[()] = _size_container(root, (), theme, scale, sizes)
    return sizes
