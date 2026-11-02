"""Tests for the renderer: figures, axes and drawn artists, without images."""

import io
import re
from pathlib import Path

import matplotlib as mpl
import pytest
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

import flowgram
from flowgram import Box, Column, Diagram, Edge, RoleStyle, Row, Spacer, Theme
from flowgram._base import TextAlign
from flowgram._text import POINTS_PER_INCH, TIER_GAP, measure_text, text_size
from flowgram.components import EdgeStyle
from flowgram.edges import anchor, route
from flowgram.layout import Layout, NodePath, Rect, layout
from flowgram.render import (
    ARROW_LENGTH,
    ARROW_WIDTH,
    FIGURE_DPI,
    SVG_HASH_SALT,
    TITLE_GAP,
    Z_BOX,
    Z_BOX_TEXT,
    Z_EDGE,
    Z_EDGE_LABEL,
    DrawnBox,
    DrawnEdge,
    Frame,
    box_look,
    draw_box,
    draw_boxes,
    draw_edge,
    draw_edges,
    draw_title,
    edge_look,
    frame,
    new_figure,
    rc_params,
    render,
    title_band,
)

LIGHT = Theme.light()


def _two_boxes(**diagram: object) -> Diagram:
    """A 6 x 1 unit row: boxes 2 and 3 wide with the theme's gap of 1."""
    root = Row(
        children=[
            Box(label="a", width=2, height=1),
            Box(label="b", width=3, height=1),
        ]
    )
    return Diagram.model_validate({"root": root, **diagram})


class TestFrame:
    def test_adds_padding_around_the_content(self) -> None:
        diagram = _two_boxes(padding=0.5)
        assert frame(diagram, layout(diagram)) == Frame(-0.5, -0.5, 6.5, 1.5)

    def test_zero_padding_is_the_content(self) -> None:
        diagram = _two_boxes(padding=0)
        result = frame(diagram, layout(diagram))
        assert (result.left, result.top, result.width, result.height) == (0, 0, 6, 1)

    def test_size(self) -> None:
        box = Frame(-1, -2, 3, 4)
        assert (box.width, box.height) == (4, 6)


class TestNewFigure:
    def test_size_is_units_times_scale(self) -> None:
        diagram = _two_boxes(padding=0.5, scale=0.5)
        figure, _ = new_figure(diagram, frame(diagram, layout(diagram)))
        assert tuple(figure.get_size_inches()) == pytest.approx((3.5, 1.0))
        assert figure.dpi == FIGURE_DPI

    def test_scale_does_not_change_fixed_sizes_in_units(self) -> None:
        small, large = _two_boxes(scale=1), _two_boxes(scale=2)
        small_figure, _ = new_figure(small, frame(small, layout(small)))
        large_figure, _ = new_figure(large, frame(large, layout(large)))
        assert tuple(large_figure.get_size_inches()) == pytest.approx(
            tuple(2 * small_figure.get_size_inches())
        )

    def test_one_axes_covers_the_figure(self) -> None:
        diagram = _two_boxes()
        figure, axes = new_figure(diagram, frame(diagram, layout(diagram)))
        assert figure.axes == [axes]
        assert axes.get_position().bounds == pytest.approx((0, 0, 1, 1))
        assert not axes.axison

    def test_limits_are_the_frame_with_y_down(self) -> None:
        diagram = _two_boxes(padding=0.5)
        _, axes = new_figure(diagram, frame(diagram, layout(diagram)))
        assert axes.get_xlim() == pytest.approx((-0.5, 6.5))
        assert axes.get_ylim() == pytest.approx((1.5, -0.5))
        assert axes.yaxis_inverted()

    def test_layout_point_maps_to_the_matching_figure_point(self) -> None:
        # The content's top left corner sits one padding in from the
        # figure's top left: 0.5 units at 1 inch per unit and 100 dpi.
        diagram = _two_boxes(padding=0.5)
        figure, axes = new_figure(diagram, frame(diagram, layout(diagram)))
        x, y = axes.transData.transform((0, 0))
        height = figure.get_size_inches()[1] * FIGURE_DPI
        assert (x, height - y) == pytest.approx((50, 50))

    def test_no_background_is_transparent(self) -> None:
        diagram = _two_boxes()
        figure, _ = new_figure(diagram, frame(diagram, layout(diagram)))
        assert to_rgba(figure.get_facecolor())[3] == 0

    def test_theme_background_fills_the_figure(self) -> None:
        theme = Theme.light().model_copy(update={"background": "#FAFAF9"})
        diagram = _two_boxes(theme=theme)
        figure, _ = new_figure(diagram, frame(diagram, layout(diagram)))
        assert figure.get_facecolor() == pytest.approx(to_rgba("#FAFAF9"))

    def test_empty_diagram_is_rejected_with_a_reason(self) -> None:
        diagram = Diagram(root=Column(children=[Spacer(size=0)]), padding=0)
        with pytest.raises(ValueError, match="nothing to draw: it is 0 x 0 units"):
            new_figure(diagram, frame(diagram, layout(diagram)))


class TestRcParams:
    def test_settings_are_valid_for_matplotlib(self) -> None:
        theme = Theme.light()
        with mpl.rc_context(rc_params(theme)):
            assert mpl.rcParams["font.family"] == [theme.font_family]
            assert mpl.rcParams["svg.hashsalt"] == SVG_HASH_SALT
            assert mpl.rcParams["svg.fonttype"] == "none"
            assert mpl.rcParams["text.parse_math"] is False

    def test_settings_do_not_leak(self) -> None:
        before = mpl.rcParams["svg.hashsalt"]
        with mpl.rc_context(rc_params(Theme.light())):
            pass
        assert mpl.rcParams["svg.hashsalt"] == before

    def test_font_family_follows_the_theme(self) -> None:
        theme = Theme.light().model_copy(update={"font_family": "DejaVu Serif"})
        assert rc_params(theme)["font.family"] == "DejaVu Serif"


def _drawn(diagram: Diagram) -> tuple[Figure, Layout, dict[NodePath, DrawnBox]]:
    result = layout(diagram)
    figure, axes = new_figure(diagram, frame(diagram, result))
    return figure, result, draw_boxes(axes, diagram, result)


def _axes() -> Axes:
    diagram = _two_boxes()
    return new_figure(diagram, frame(diagram, layout(diagram)))[1]


def _extent(figure: Figure, artist: object) -> Bbox:
    renderer = FigureCanvasAgg(figure).get_renderer()  # type: ignore[no-untyped-call]
    return artist.get_window_extent(renderer)  # type: ignore[attr-defined, no-any-return]


class TestBoxLook:
    def test_defaults_come_from_the_role_and_theme(self) -> None:
        look = box_look(Box(label="x", role="accent"), LIGHT)
        accent = LIGHT.roles["accent"]
        assert (look.fill, look.stroke, look.text) == (
            accent.fill,
            accent.stroke,
            accent.text,
        )
        assert look.eyebrow == accent.text
        assert look.line_width == LIGHT.line_width
        assert look.corner_radius == LIGHT.corner_radius
        assert look.text_align == LIGHT.text_align

    def test_box_overrides_win(self) -> None:
        box = Box(
            label="x",
            role="accent",
            fill="#111111",
            stroke="#222222",
            text_color="#333333",
            eyebrow_color="#444444",
            line_width=3,
            corner_radius=0,
            text_align="right",
        )
        look = box_look(box, LIGHT)
        assert (look.fill, look.stroke, look.text, look.eyebrow) == (
            "#111111",
            "#222222",
            "#333333",
            "#444444",
        )
        assert (look.line_width, look.corner_radius, look.text_align) == (
            3,
            0,
            "right",
        )

    def test_eyebrow_uses_the_role_eyebrow_colour(self) -> None:
        roles = {
            "default": RoleStyle(
                fill="#FFFFFF", stroke="#000000", text="#000000", eyebrow="#2563EB"
            )
        }
        look = box_look(Box(label="x"), Theme(roles=roles))
        assert look.eyebrow == "#2563EB"

    def test_eyebrow_follows_a_text_colour_override(self) -> None:
        look = box_look(Box(label="x", text_color="#DC2626"), LIGHT)
        assert look.eyebrow == "#DC2626"

    def test_theme_alignment_applies_when_the_box_has_none(self) -> None:
        theme = LIGHT.model_copy(update={"text_align": "left"})
        assert box_look(Box(label="x"), theme).text_align == "left"


class TestDrawBox:
    RECT = Rect(1, 2, 3, 1.5)

    def test_patch_fills_the_rect_with_the_role_colours(self) -> None:
        drawn = draw_box(_axes(), Box(label="x", role="muted"), self.RECT, LIGHT, 1)
        patch = drawn.patch
        muted = LIGHT.roles["muted"]
        assert (patch.get_x(), patch.get_y()) == (1, 2)
        assert (patch.get_width(), patch.get_height()) == (3, 1.5)
        assert patch.get_facecolor() == pytest.approx(to_rgba(muted.fill))
        assert patch.get_edgecolor() == pytest.approx(to_rgba(muted.stroke))
        assert patch.get_linewidth() == LIGHT.line_width
        assert patch.get_zorder() == Z_BOX

    def test_patch_is_added_to_the_axes(self) -> None:
        axes = _axes()
        drawn = draw_box(axes, Box(label="x"), self.RECT, LIGHT, 1)
        assert drawn.patch in axes.patches
        assert all(text in axes.texts for text in drawn.texts)

    def test_corner_radius_is_in_units(self) -> None:
        box = Box(label="x", corner_radius=0.25)
        style = draw_box(_axes(), box, self.RECT, LIGHT, 1).patch.get_boxstyle()
        assert style.rounding_size == 0.25  # type: ignore[attr-defined]

    def test_corner_radius_is_capped_at_half_the_short_side(self) -> None:
        box = Box(label="x", corner_radius=5)
        style = draw_box(_axes(), box, self.RECT, LIGHT, 1).patch.get_boxstyle()
        assert style.rounding_size == 0.75  # type: ignore[attr-defined]

    def test_zero_radius_draws_square_corners(self) -> None:
        box = Box(label="x", corner_radius=0)
        style = draw_box(_axes(), box, self.RECT, LIGHT, 1).patch.get_boxstyle()
        assert type(style).__name__ == "Square"

    def test_tiers_are_drawn_top_to_bottom_with_their_fonts(self) -> None:
        box = Box(label="Model", subtitle="gradient boosting", eyebrow="STEP 3")
        texts = draw_box(_axes(), box, self.RECT, LIGHT, 1).texts
        assert [t.get_text() for t in texts] == ["STEP 3", "Model", "gradient boosting"]
        assert [t.get_fontsize() for t in texts] == [
            LIGHT.eyebrow_size,
            LIGHT.label_size,
            LIGHT.subtitle_size,
        ]
        assert [t.get_fontweight() for t in texts] == ["bold", "bold", "normal"]
        assert all(t.get_zorder() == Z_BOX_TEXT for t in texts)
        assert all(t.get_fontfamily() == [LIGHT.font_family] for t in texts)

    def test_eyebrow_and_text_colours(self) -> None:
        box = Box(label="x", eyebrow="e", subtitle="s", eyebrow_color="#2563EB")
        texts = draw_box(_axes(), box, self.RECT, LIGHT, 1).texts
        text = to_rgba(LIGHT.roles["default"].text)
        assert [to_rgba(t.get_color()) for t in texts] == [
            to_rgba("#2563EB"),
            text,
            text,
        ]

    def test_text_block_is_centred_vertically_at_the_measured_offsets(self) -> None:
        box = Box(label="Model", subtitle="boosting", eyebrow="STEP")
        texts = draw_box(_axes(), box, self.RECT, LIGHT, 1).texts
        block = measure_text("Model", LIGHT, 1, subtitle="boosting", eyebrow="STEP")
        top = 2 + (1.5 - block.height) / 2
        assert [t.get_position()[1] for t in texts] == pytest.approx(
            [top + tier.top for tier in block.tiers]
        )
        assert all(t.get_verticalalignment() == "top" for t in texts)

    @pytest.mark.parametrize(
        ("align", "x"),
        [
            ("left", 1 + LIGHT.text_padding),
            ("center", 2.5),
            ("right", 4 - LIGHT.text_padding),
        ],
    )
    def test_alignment_sets_anchor_and_inset(self, align: TextAlign, x: float) -> None:
        box = Box(label="one\ntwo", text_align=align)
        (text,) = draw_box(_axes(), box, self.RECT, LIGHT, 1).texts
        assert text.get_position()[0] == pytest.approx(x)
        assert text.get_horizontalalignment() == align
        # matplotlib has no getter for the alignment between lines.
        assert text._multialignment == align  # type: ignore[attr-defined]

    def test_dollar_signs_are_not_mathtext(self) -> None:
        diagram = Diagram(root=Row(children=[Box(label="$5 to $10")]))
        figure, _, drawn = _drawn(diagram)
        (text,) = drawn[(0,)].texts
        as_math = figure.axes[0].text(0, 0, "$5 to $10", parse_math=True)
        as_math.update_from(text)
        # Mathtext drops the dollar signs and the spaces between them.
        assert _extent(figure, text).width > 1.2 * _extent(figure, as_math).width


class TestDrawBoxes:
    def test_every_box_is_drawn_at_its_path(self) -> None:
        diagram = Diagram(
            root=Row(
                children=[
                    Box(label="a"),
                    Column(children=[Box(label="b"), Spacer(size=1), Box(label="c")]),
                ]
            )
        )
        _, result, drawn = _drawn(diagram)
        assert set(drawn) == {(0,), (1, 0), (1, 2)}
        for path, box in drawn.items():
            rect = result.rect(path)
            assert (box.patch.get_x(), box.patch.get_y()) == (rect.x, rect.y)

    @pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_text_stays_inside_its_box(self, scale: float, align: TextAlign) -> None:
        theme = LIGHT.model_copy(update={"text_align": align})
        diagram = Diagram(
            theme=theme,
            scale=scale,
            root=Row(
                children=[
                    Box(label="A rather long label for one box"),
                    Box(label="x"),
                    Box(
                        label="Two lines\nof label",
                        eyebrow="EYEBROW TEXT",
                        subtitle="and a subtitle that is longer still",
                    ),
                ]
            ),
        )
        figure, _, drawn = _drawn(diagram)
        for box in drawn.values():
            outline = _extent(figure, box.patch)
            for text in box.texts:
                inside = _extent(figure, text)
                # Half the outline width sits outside the patch's extent.
                assert inside.x0 >= outline.x0 - 0.5
                assert inside.x1 <= outline.x1 + 0.5
                assert inside.y0 >= outline.y0 - 0.5
                assert inside.y1 <= outline.y1 + 0.5


def test_z_order_puts_edges_under_boxes_and_labels_on_top() -> None:
    assert Z_EDGE < Z_BOX < Z_BOX_TEXT < Z_EDGE_LABEL


def _titled(title: str | None, subtitle: str | None = None, **theme: object) -> Diagram:
    return _two_boxes(
        title=title,
        subtitle=subtitle,
        padding=0.5,
        theme=LIGHT.model_copy(update=theme),
    )


def _title_size(text: str, theme: Theme = LIGHT) -> tuple[float, float]:
    return text_size(text, theme.title_size, theme.title_weight, theme.font_family, 1)


class TestTitleBand:
    def test_no_title_means_no_band(self) -> None:
        diagram = _titled(None)
        assert title_band(diagram) is None
        assert frame(diagram, layout(diagram)) == Frame(-0.5, -0.5, 6.5, 1.5)

    def test_empty_title_means_no_band(self) -> None:
        assert title_band(_titled("")) is None

    def test_title_only(self) -> None:
        band = title_band(_titled("Pipeline"))
        assert band is not None
        width, height = _title_size("Pipeline")
        assert [line.text for line in band.lines] == ["Pipeline"]
        assert (band.width, band.height) == (width, height)
        assert band.gap == pytest.approx(LIGHT.title_size * TITLE_GAP / POINTS_PER_INCH)
        (line,) = band.lines
        assert (line.size, line.weight, line.top) == (LIGHT.title_size, "bold", 0)

    def test_title_and_subtitle_stack_with_a_gap(self) -> None:
        band = title_band(_titled("Pipeline", "Training and scoring"))
        assert band is not None
        title, subtitle = band.lines
        gap = LIGHT.title_size * TIER_GAP / POINTS_PER_INCH
        assert subtitle.top == pytest.approx(title.height + gap)
        assert (subtitle.size, subtitle.weight) == (LIGHT.subtitle_size, "normal")
        assert band.height == pytest.approx(subtitle.top + subtitle.height)
        assert band.width == max(title.width, subtitle.width)

    def test_subtitle_without_a_title(self) -> None:
        band = title_band(_titled(None, "Just a note"))
        assert band is not None
        assert [line.text for line in band.lines] == ["Just a note"]

    def test_band_follows_scale(self) -> None:
        small = title_band(_titled("Pipeline"))
        large = title_band(_titled("Pipeline").model_copy(update={"scale": 2}))
        assert small is not None
        assert large is not None
        assert large.height == pytest.approx(small.height / 2)


class TestTitleFrame:
    def test_band_is_reserved_above_the_content(self) -> None:
        diagram = _titled("Pipeline", "Training")
        band = title_band(diagram)
        assert band is not None
        result = frame(diagram, layout(diagram))
        assert result.top == pytest.approx(-0.5 - band.gap - band.height)
        assert (result.left, result.right, result.bottom) == (-0.5, 6.5, 1.5)

    @pytest.mark.parametrize(
        ("align", "left_extra"), [("left", 0.0), ("center", 0.5), ("right", 1.0)]
    )
    def test_wide_title_widens_the_frame(
        self, align: TextAlign, left_extra: float
    ) -> None:
        title = "A title that is much wider than the six units of content"
        diagram = _titled(title, title_align=align)
        result = frame(diagram, layout(diagram))
        extra = _title_size(title)[0] - 6
        assert extra > 0
        assert result.width == pytest.approx(_title_size(title)[0] + 1)
        assert result.left == pytest.approx(-0.5 - left_extra * extra)
        assert result.right == pytest.approx(6.5 + (1 - left_extra) * extra)

    def test_figure_grows_with_the_band(self) -> None:
        plain = _titled(None)
        titled = _titled("Pipeline")
        band = title_band(titled)
        assert band is not None
        plain_figure, _ = new_figure(plain, frame(plain, layout(plain)))
        titled_figure, _ = new_figure(titled, frame(titled, layout(titled)))
        grown = titled_figure.get_size_inches()[1] - plain_figure.get_size_inches()[1]
        assert grown == pytest.approx(band.height + band.gap)


class TestDrawTitle:
    def _draw(self, diagram: Diagram) -> tuple[Frame, tuple[Text, ...]]:
        result = frame(diagram, layout(diagram))
        _, axes = new_figure(diagram, result)
        return result, draw_title(axes, diagram, result)

    def test_nothing_is_drawn_without_a_title(self) -> None:
        assert self._draw(_titled(None))[1] == ()

    def test_title_and_subtitle_are_drawn_top_down(self) -> None:
        diagram = _titled("Pipeline", "Training")
        band = title_band(diagram)
        assert band is not None
        result, texts = self._draw(diagram)
        assert [t.get_text() for t in texts] == ["Pipeline", "Training"]
        assert [t.get_position()[1] for t in texts] == pytest.approx(
            [result.top + 0.5 + line.top for line in band.lines]
        )
        assert [t.get_fontsize() for t in texts] == [
            LIGHT.title_size,
            LIGHT.subtitle_size,
        ]
        assert [t.get_fontweight() for t in texts] == ["bold", "normal"]

    @pytest.mark.parametrize(
        ("align", "x"), [("left", 0.0), ("center", 3.0), ("right", 6.0)]
    )
    def test_alignment_across_the_content(self, align: TextAlign, x: float) -> None:
        _, texts = self._draw(_titled("Pipeline", title_align=align))
        (text,) = texts
        assert text.get_position()[0] == pytest.approx(x)
        assert text.get_horizontalalignment() == align

    def test_default_colour_is_the_default_role_text(self) -> None:
        (text,) = self._draw(_titled("Pipeline"))[1]
        assert to_rgba(text.get_color()) == to_rgba(LIGHT.roles["default"].text)

    def test_title_colour_override(self) -> None:
        (text,) = self._draw(_titled("Pipeline", title_color="#2563EB"))[1]
        assert to_rgba(text.get_color()) == to_rgba("#2563EB")

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_title_stays_in_the_figure_above_the_content(
        self, align: TextAlign
    ) -> None:
        title = "A title that is much wider than the six units of content"
        diagram = _titled(title, "and a subtitle", title_align=align)
        result = frame(diagram, layout(diagram))
        figure, axes = new_figure(diagram, result)
        texts = draw_title(axes, diagram, result)
        content_top = axes.transData.transform((0, 0))[1]
        width, height = figure.bbox.width, figure.bbox.height
        for text in texts:
            box = _extent(figure, text)
            assert box.x0 >= -0.5
            assert box.x1 <= width + 0.5
            assert box.y1 <= height + 0.5
            assert box.y0 >= content_top


def _one_row() -> Diagram:
    return Diagram(
        title="Model training pipeline",
        subtitle="Three steps, three roles",
        root=Row(
            children=[
                Box(id="data", label="Raw data", role="muted"),
                Box(id="clean", label="Clean", subtitle="impute, clip"),
                Box(id="model", label="Model", eyebrow="STEP 3", role="accent"),
            ]
        ),
    )


class TestRender:
    def test_returns_a_figure_sized_to_the_frame(self) -> None:
        diagram = _one_row()
        figure = diagram.render()
        view = frame(diagram, layout(diagram))
        assert isinstance(figure, Figure)
        assert tuple(figure.get_size_inches()) == pytest.approx(
            (view.width * diagram.scale, view.height * diagram.scale)
        )

    def test_draws_every_box_and_the_title(self) -> None:
        (axes,) = _one_row().render().axes
        assert len(axes.patches) == 3
        assert [t.get_text() for t in axes.texts] == [
            "Raw data",
            "Clean",
            "impute, clip",
            "STEP 3",
            "Model",
            "Model training pipeline",
            "Three steps, three roles",
        ]

    def test_method_and_function_agree(self) -> None:
        diagram = _one_row()
        by_method = diagram.render()
        by_function = render(diagram)
        assert tuple(by_method.get_size_inches()) == tuple(
            by_function.get_size_inches()
        )
        assert by_method.axes[0].get_xlim() == by_function.axes[0].get_xlim()

    def test_figures_are_not_tracked_by_pyplot(self) -> None:
        figure = _one_row().render()
        assert figure.canvas.manager is None

    def test_renders_to_png_on_every_platform(self) -> None:
        # The image compare only runs on Linux; this checks drawing works.
        figure = _one_row().render()
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png")
        assert buffer.getvalue().startswith(b"\x89PNG")

    def test_theme_font_is_used_even_under_another_style(self) -> None:
        with mpl.rc_context({"font.family": "DejaVu Serif"}):
            figure = _one_row().render()
        assert all(
            t.get_fontfamily() == [LIGHT.font_family] for t in figure.axes[0].texts
        )

    def test_render_settings_do_not_leak(self) -> None:
        before = dict(mpl.rcParams)
        _one_row().render()
        assert dict(mpl.rcParams) == before


class TestDraw:
    def test_draws_into_a_subplot_without_resizing_the_figure(self) -> None:
        figure = Figure(figsize=(8, 3))
        left, right = figure.subplots(1, 2)
        right.plot([0, 1], [0, 1])
        _one_row().draw(left)
        assert tuple(figure.get_size_inches()) == (8, 3)
        assert len(left.patches) == 3
        assert len(left.texts) == 7
        assert not right.patches

    def test_sets_limits_equal_aspect_and_no_axis(self) -> None:
        diagram = _one_row()
        axes = Figure().subplots()
        diagram.draw(axes)
        view = frame(diagram, layout(diagram))
        assert axes.get_xlim() == pytest.approx((view.left, view.right))
        assert axes.get_ylim() == pytest.approx((view.bottom, view.top))
        assert axes.get_aspect() == 1.0
        assert not axes.axison


PYPLOT_IMPORT = re.compile(
    r"^\s*(?:import\s+matplotlib\.pyplot|from\s+matplotlib(?:\.pyplot\s+import|"
    r"\s+import\s+.*\bpyplot\b))",
    re.MULTILINE,
)


@pytest.mark.parametrize(
    "line",
    [
        "import matplotlib.pyplot as plt",
        "from matplotlib import pyplot",
        "from matplotlib import colors, pyplot as plt",
        "    from matplotlib.pyplot import subplots",
    ],
)
def test_pyplot_import_pattern(line: str) -> None:
    assert PYPLOT_IMPORT.search(line)


def test_no_pyplot_import_in_the_package() -> None:
    package = Path(flowgram.__file__).parent
    offenders = [
        path.name
        for path in sorted(package.rglob("*.py"))
        if PYPLOT_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def _edge_diagram(*edges: Edge, line_width: float = 2.0) -> Diagram:
    """Two fixed boxes 2 units apart in a row, plus ``edges`` between them."""
    return Diagram(
        root=Row(
            gap=2,
            children=[
                Box(id="a", label="a", width=2, height=1, line_width=line_width),
                Box(id="b", label="b", width=2, height=1, line_width=line_width),
                Box(id="c", label="c", width=2, height=3, line_width=line_width),
            ],
        ),
        edges=list(edges),
    )


def _draw_edges(diagram: Diagram) -> tuple[Layout, tuple[DrawnEdge, ...]]:
    result = layout(diagram)
    _, axes = new_figure(diagram, frame(diagram, result))
    return result, draw_edges(axes, diagram, result)


UNIT = 1 / POINTS_PER_INCH
"""One point in units, at scale 1."""


class TestEdgeLook:
    def test_defaults_come_from_the_theme(self) -> None:
        look = edge_look(Edge(src="a", dst="b"), LIGHT)
        assert (look.color, look.line_width, look.line_style) == (
            LIGHT.edge_color,
            LIGHT.edge_line_width,
            "solid",
        )

    def test_overrides_win(self) -> None:
        edge = Edge(src="a", dst="b", color="#DC2626", line_width=3, style="dotted")
        look = edge_look(edge, LIGHT)
        assert (look.color, look.line_width, look.line_style) == (
            "#DC2626",
            3,
            "dotted",
        )


class TestDrawEdge:
    @pytest.mark.parametrize(
        ("style", "pattern"), [("solid", "-"), ("dashed", "--"), ("dotted", ":")]
    )
    def test_line_styles(self, style: EdgeStyle, pattern: str) -> None:
        _, (drawn,) = _draw_edges(_edge_diagram(Edge(src="a", dst="b", style=style)))
        assert drawn.line.get_linestyle() == pattern
        assert all(head.get_linestyle() == "solid" for head in drawn.heads)

    def test_colour_and_width(self) -> None:
        edge = Edge(src="a", dst="b", color="#16A34A", line_width=2.5)
        _, (drawn,) = _draw_edges(_edge_diagram(edge))
        assert drawn.line.get_linewidth() == 2.5
        assert to_rgba(drawn.line.get_color()) == to_rgba("#16A34A")
        (head,) = drawn.heads
        assert head.get_facecolor() == pytest.approx(to_rgba("#16A34A"))

    @pytest.mark.parametrize(("arrow", "count"), [("end", 1), ("both", 2), ("none", 0)])
    def test_arrow_ends(self, arrow: str, count: int) -> None:
        _, (drawn,) = _draw_edges(
            _edge_diagram(Edge.model_validate({"src": "a", "dst": "b", "arrow": arrow}))
        )
        assert len(drawn.heads) == count

    def test_tip_touches_the_outside_of_the_outline(self) -> None:
        result, (drawn,) = _draw_edges(_edge_diagram(Edge(src="a", dst="b")))
        (head,) = drawn.heads
        tip = tuple(head.get_xy()[0])
        x, y = anchor(result.box("b"), "left")
        # Half of the 2 pt outline sits outside the box.
        assert tip == pytest.approx((x - 1 * UNIT, y))

    def test_arrowhead_size_follows_the_theme(self) -> None:
        _, (drawn,) = _draw_edges(_edge_diagram(Edge(src="a", dst="b")))
        tip, wing, other = (tuple(p) for p in drawn.heads[0].get_xy()[:3])
        length = LIGHT.arrow_size * ARROW_LENGTH * UNIT
        width = LIGHT.arrow_size * ARROW_WIDTH * UNIT
        assert tip[0] - wing[0] == pytest.approx(length)
        assert abs(wing[1] - other[1]) == pytest.approx(width)

    def test_line_stops_at_the_arrowhead_base(self) -> None:
        result, (drawn,) = _draw_edges(_edge_diagram(Edge(src="a", dst="b")))
        xs = drawn.line.get_xdata()
        tip = drawn.heads[0].get_xy()[0][0]
        assert xs[-1] == pytest.approx(tip - LIGHT.arrow_size * ARROW_LENGTH * UNIT)  # type: ignore[index]
        # The start has no arrowhead: it only clears the source outline.
        assert xs[0] == pytest.approx(anchor(result.box("a"), "right")[0] + UNIT)  # type: ignore[index]

    def test_both_ends_point_outwards(self) -> None:
        edge = Edge(src="a", dst="b", arrow="both")
        result, (drawn,) = _draw_edges(_edge_diagram(edge))
        end, start = (head.get_xy()[0] for head in drawn.heads)
        assert end[0] == pytest.approx(anchor(result.box("b"), "left")[0] - UNIT)
        assert start[0] == pytest.approx(anchor(result.box("a"), "right")[0] + UNIT)

    def test_elbow_heads_follow_the_last_segment(self) -> None:
        # In a top-aligned row, a's bottom (y 1) is above c's middle
        # (y 1.5), so the edge goes down out of a, then right into c.
        diagram = Diagram(
            root=Row(
                align="start",
                children=[
                    Box(id="a", label="a", width=2, height=1),
                    Box(id="c", label="c", width=2, height=3),
                ],
            ),
            edges=[Edge(src="a", dst="c", exit="bottom", entry="left")],
        )
        result, (drawn,) = _draw_edges(diagram)
        start, corner, end = drawn.route.points
        assert corner == (start[0], end[1])
        tip, wing, _ = (tuple(p) for p in drawn.heads[0].get_xy()[:3])
        outline = LIGHT.line_width / 2 * UNIT
        left = anchor(result.box("c"), "left")
        assert tip == pytest.approx((left[0] - outline, left[1]))
        assert wing[0] < tip[0]

    def test_edges_sit_under_boxes(self) -> None:
        _, (drawn,) = _draw_edges(_edge_diagram(Edge(src="a", dst="b")))
        assert drawn.line.get_zorder() == Z_EDGE
        assert all(head.get_zorder() == Z_EDGE for head in drawn.heads)

    def test_short_segment_never_reverses(self) -> None:
        theme = LIGHT.model_copy(update={"arrow_size": 400})
        diagram = _edge_diagram(Edge(src="a", dst="b")).model_copy(
            update={"theme": theme}
        )
        result, (drawn,) = _draw_edges(diagram)
        xs = list(drawn.line.get_xdata())  # type: ignore[arg-type]
        assert xs[-1] >= xs[0]
        assert xs[0] >= result.box("a").right

    def test_draw_edge_without_outlines_ends_on_the_anchor(self) -> None:
        diagram = _edge_diagram()
        result = layout(diagram)
        edge = Edge(src="a", dst="b", arrow="none")
        drawn = draw_edge(_axes(), edge, route(edge, result), LIGHT, 1)
        end = (drawn.line.get_xdata()[-1], drawn.line.get_ydata()[-1])  # type: ignore[index]
        assert end == anchor(result.box("b"), "left")


class TestDrawEdges:
    def test_one_drawn_edge_per_edge_in_order(self) -> None:
        diagram = _edge_diagram(Edge(src="a", dst="b"), Edge(src="b", dst="c"))
        _, drawn = _draw_edges(diagram)
        assert [(d.route.points[0], d.route.points[-1]) for d in drawn] == [
            (route(e, layout(diagram)).points[0], route(e, layout(diagram)).points[-1])
            for e in diagram.edges
        ]

    def test_render_and_draw_include_edges(self) -> None:
        diagram = _edge_diagram(Edge(src="a", dst="b"), Edge(src="b", dst="c"))
        (axes,) = diagram.render().axes
        assert len(axes.lines) == 2
        target = Figure().subplots()
        diagram.draw(target)
        assert len(target.lines) == 2

    def test_dash_settings_are_fixed(self) -> None:
        params = rc_params(LIGHT)
        assert params["lines.scale_dashes"] is True
        with mpl.rc_context({"lines.dashed_pattern": [10, 10]}):
            (axes,) = (
                _edge_diagram(Edge(src="a", dst="b", style="dashed")).render().axes
            )
        _, dashes = axes.lines[0]._dash_pattern  # type: ignore[attr-defined]
        assert dashes[0] == pytest.approx(3.7 * LIGHT.edge_line_width)


def test_edge_between_touching_boxes_draws_without_error() -> None:
    diagram = Diagram(
        root=Row(
            gap=0,
            children=[
                Box(id="a", label="a", width=2, height=1),
                Box(id="b", label="b", width=2, height=1),
            ],
        ),
        edges=[Edge(src="a", dst="b", arrow="both")],
    )
    _, (drawn,) = _draw_edges(diagram)
    assert len(drawn.heads) == 2
    FigureCanvasAgg(drawn.line.get_figure()).draw()  # type: ignore[arg-type, no-untyped-call]
    assert list(drawn.route.points) == [(2, 0.5), (2, 0.5)]
