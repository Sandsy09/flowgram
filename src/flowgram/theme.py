"""Themes: semantic colour roles plus typography and geometry defaults."""

from typing import Annotated, Self

from pydantic import AfterValidator, model_validator

from flowgram._base import (
    Colour,
    Finite,
    FontWeight,
    FrozenSeq,
    NonNegative,
    Opacity,
    Positive,
    Spec,
    TextAlign,
    TextVAlign,
)

DEFAULT_ROLE = "default"
"""The role every theme must define; boxes use it unless told otherwise."""

GENERIC_FONT_FAMILIES = frozenset(
    {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"}
)
"""CSS generic families, which an SVG names without quotes."""

_FONT_NAME_FORBIDDEN = "'\";<>&\\"


def _check_font_name(value: str) -> str:
    """Return ``value`` unchanged if it can be written into SVG as a font name.

    Args:
        value: A font family name such as ``"DejaVu Sans"``.

    Returns:
        The same string.

    Raises:
        ValueError: If the name is blank or holds a quote, semicolon, angle
            bracket, ampersand or backslash, which no font name needs and
            which would break the SVG's style attribute.
    """
    if not value.strip() or any(char in value for char in _FONT_NAME_FORBIDDEN):
        msg = (
            f"{value!r} is not a usable font name; it must not be blank or "
            f"contain any of: {' '.join(_FONT_NAME_FORBIDDEN)}"
        )
        raise ValueError(msg)
    return value


FontName = Annotated[str, AfterValidator(_check_font_name)]
"""A font family name, safe to write into an SVG style attribute."""


class RoleStyle(Spec):
    """Fill, outline and text colours for one semantic role.

    Attributes:
        fill: Box background colour.
        stroke: Box outline colour.
        text: Label colour drawn on top of the fill, and the eyebrow and
            subtitle colour when those are ``None``.
        eyebrow: Eyebrow colour, or ``None`` to use ``text``.
        subtitle: Subtitle colour, or ``None`` to use ``text``. Set it to
            mute body text under a darker label.
    """

    fill: Colour
    stroke: Colour
    text: Colour
    eyebrow: Colour | None = None
    subtitle: Colour | None = None


class Shadow(Spec):
    """A soft drop shadow under each box.

    The shadow is the box's shape, offset and filled with a faint colour.
    Its edge fades out over ``softness``, drawn as a few overlapping
    layers, since matplotlib cannot blur. It sits under the box and above
    edges, and is not counted in layout, so a large offset can reach into
    the diagram's padding.

    Attributes:
        dx: Offset to the right, in units. Negative moves it left.
        dy: Offset downward, in units. Negative moves it up.
        color: Shadow colour.
        alpha: Opacity where the shadow is fullest, from 0 to 1.
        softness: Width of the faded edge, in units. 0 draws one
            hard-edged shape.
    """

    dx: Finite = 0.04
    dy: Finite = 0.06
    color: Colour = "#0F172A"
    alpha: Opacity = 0.12
    softness: NonNegative = 0.06


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
        font_fallbacks: Fonts an SVG viewer tries, in order, when it does
            not have ``font_family``, ending in a CSS generic family such as
            ``"sans-serif"``. Drawing and measuring always use
            ``font_family``. The default puts Verdana first: it comes with
            Windows and macOS, and its text is within about 2% of DejaVu
            Sans's width, so labels still fit their boxes.
        title_size: Diagram title size in points.
        subtitle_size: Box subtitle size in points, and the diagram
            subtitle's unless ``title_subtitle_size`` is set.
        label_size: Box label size in points.
        eyebrow_size: Box eyebrow size in points.
        edge_label_size: Edge label size in points.
        label_weight: Weight of box labels.
        subtitle_weight: Weight of box subtitles.
        eyebrow_weight: Weight of box eyebrows.
        text_align: Default horizontal alignment of text inside boxes.
        text_valign: Default vertical placement of text inside boxes:
            ``"center"``, or ``"top"`` to start it one ``text_padding`` below
            the top border. It only shows on boxes taller than their text.
        line_spacing: Distance between the baselines of one piece of text,
            as a multiple of the font's ascent plus descent, which for
            DejaVu Sans is its font size. Used for box text, the diagram
            title and edge labels.
        tier_gap: Space between a box's eyebrow, label and subtitle, as a
            multiple of the label size. The diagram subtitle sits this many
            title sizes below the title.
        title_weight: Weight of the diagram title. Its subtitle uses
            ``subtitle_weight``.
        title_align: Alignment of the diagram title and subtitle across
            the figure.
        title_color: Colour of the diagram title, or ``None`` for the
            ``default`` role's text colour.
        title_subtitle_size: Diagram subtitle size in points, or ``None``
            for ``subtitle_size``, the box subtitle size.
        title_subtitle_color: Diagram subtitle colour, or ``None`` for the
            title's colour.
        footnote_size: Diagram footnote size in points, or ``None`` for the
            diagram subtitle's size.
        footnote_color: Diagram footnote colour, or ``None`` for the
            diagram subtitle's colour.
        line_width: Default box outline width in points.
        corner_radius: Default box corner radius in units.
        shadow: Drop shadow under every box, or ``None`` for none.
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

    font_family: FontName = "DejaVu Sans"
    font_fallbacks: FrozenSeq[FontName] = ("Verdana", "sans-serif")
    title_size: Positive = 16.0
    subtitle_size: Positive = 11.0
    label_size: Positive = 11.0
    eyebrow_size: Positive = 8.5
    edge_label_size: Positive = 9.0
    label_weight: FontWeight = "bold"
    subtitle_weight: FontWeight = "normal"
    eyebrow_weight: FontWeight = "bold"
    text_align: TextAlign = "center"
    text_valign: TextVAlign = "center"
    line_spacing: Positive = 1.2
    tier_gap: NonNegative = 0.3
    title_weight: FontWeight = "bold"
    title_align: TextAlign = "left"
    title_color: Colour | None = None
    title_subtitle_size: Positive | None = None
    title_subtitle_color: Colour | None = None
    footnote_size: Positive | None = None
    footnote_color: Colour | None = None

    line_width: Positive = 1.5
    corner_radius: NonNegative = 0.15
    shadow: Shadow | None = None
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
