"""Tests for the renderer: figures, axes and drawn artists, without images."""

import matplotlib as mpl
import pytest
from matplotlib.colors import to_rgba

from flowgram import Box, Column, Diagram, Row, Spacer, Theme
from flowgram.layout import layout
from flowgram.render import (
    FIGURE_DPI,
    SVG_HASH_SALT,
    Frame,
    frame,
    new_figure,
    rc_params,
)


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
