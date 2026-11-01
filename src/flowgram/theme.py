"""Themes: semantic colour roles plus typography and geometry defaults."""

from typing import Self

from pydantic import model_validator

from flowgram._base import Colour, NonNegative, Positive, Spec

DEFAULT_ROLE = "default"
"""The role every theme must define; boxes use it unless told otherwise."""


class RoleStyle(Spec):
    """Fill, outline and text colours for one semantic role.

    Attributes:
        fill: Box background colour.
        stroke: Box outline colour.
        text: Label colour drawn on top of the fill.
    """

    fill: Colour
    stroke: Colour
    text: Colour


def _light_roles() -> dict[str, RoleStyle]:
    return {
        "default": RoleStyle(fill="#FFFFFF", stroke="#334155", text="#0F172A"),
        "accent": RoleStyle(fill="#2563EB", stroke="#1D4ED8", text="#FFFFFF"),
        "muted": RoleStyle(fill="#F1F5F9", stroke="#94A3B8", text="#475569"),
        "positive": RoleStyle(fill="#16A34A", stroke="#15803D", text="#FFFFFF"),
        "negative": RoleStyle(fill="#DC2626", stroke="#B91C1C", text="#FFFFFF"),
    }


def _mono_roles() -> dict[str, RoleStyle]:
    return {
        "default": RoleStyle(fill="#FFFFFF", stroke="#222222", text="#111111"),
        "accent": RoleStyle(fill="#222222", stroke="#000000", text="#FFFFFF"),
        "muted": RoleStyle(fill="#EEEEEE", stroke="#888888", text="#444444"),
        "positive": RoleStyle(fill="#BBBBBB", stroke="#444444", text="#000000"),
        "negative": RoleStyle(fill="#666666", stroke="#000000", text="#FFFFFF"),
    }


class Theme(Spec):
    """Colours, type sizes and spacing shared by every component in a diagram.

    Boxes refer to colours by role name (``"accent"``, ``"muted"``, ...), so
    restyling a whole diagram means swapping one theme. Lengths marked "units"
    use the same abstract units as component sizes and gaps. Font sizes are in
    points and do not change with the diagram's ``scale``.

    Attributes:
        name: A label for the theme, used in error messages.
        roles: Maps a role name to its colours. Must include ``"default"``.
        font_family: Font family used for all text.
        title_size: Diagram title size in points.
        subtitle_size: Diagram and box subtitle size in points.
        label_size: Box label size in points.
        edge_label_size: Edge label size in points.
        line_width: Default box outline width in points.
        corner_radius: Default box corner radius in units.
        gap: Default space between children of a Row or Column, in units.
        text_padding: Space between a box's text and its border, in units.
        min_box_width: Smallest automatic box width in units.
        min_box_height: Smallest automatic box height in units.
        edge_color: Default edge colour.
        edge_line_width: Default edge width in points.
        arrow_size: Arrowhead size in points.
        background: Figure background colour, or ``None`` for transparent.
    """

    name: str = "custom"
    roles: dict[str, RoleStyle]

    font_family: str = "DejaVu Sans"
    title_size: Positive = 16.0
    subtitle_size: Positive = 11.0
    label_size: Positive = 11.0
    edge_label_size: Positive = 9.0

    line_width: Positive = 1.5
    corner_radius: NonNegative = 0.15
    gap: NonNegative = 1.0
    text_padding: NonNegative = 0.3
    min_box_width: Positive = 1.5
    min_box_height: Positive = 0.7

    edge_color: Colour = "#475569"
    edge_line_width: Positive = 1.5
    arrow_size: Positive = 10.0

    background: Colour | None = None

    @model_validator(mode="after")
    def _require_default_role(self) -> Self:
        if DEFAULT_ROLE not in self.roles:
            msg = (
                f"theme {self.name!r} must define a {DEFAULT_ROLE!r} role; "
                f"it defines: {', '.join(sorted(self.roles)) or 'no roles'}"
            )
            raise ValueError(msg)
        return self

    @classmethod
    def light(cls) -> Self:
        """Return the default theme: white boxes with blue, green and red accents.

        Returns:
            A new light theme.
        """
        return cls(name="light", roles=_light_roles())

    @classmethod
    def mono(cls) -> Self:
        """Return a greyscale theme suited to black-and-white printing.

        Returns:
            A new greyscale theme.
        """
        return cls(name="mono", roles=_mono_roles(), edge_color="#333333")
