"""Tests for layout result types."""

import dataclasses

import pytest

from flowgram import Box, Column, Row, Spacer, Theme
from flowgram._text import measure_text
from flowgram.components import Side
from flowgram.layout import Layout, NodePath, Rect, box_size, node_sizes

THEME = Theme.light()
LONG = "A label long enough to need more than the minimum width"
# Minimums tall enough that one line of default text never reaches them.
ROOMY = THEME.model_copy(update={"min_box_height": 1.5})


def _layout() -> Layout:
    return Layout(
        width=10,
        height=4,
        rects={
            (): Rect(0, 0, 10, 4),
            (0,): Rect(0, 0, 3, 2),
            (1,): Rect(5, 1, 2, 2),
        },
        ids={"data": (0,), "model": (1,)},
    )


class TestRect:
    def test_edges_and_centre(self) -> None:
        rect = Rect(x=1, y=2, width=4, height=6)
        assert rect.right == 5
        assert rect.bottom == 8
        assert rect.center == (3, 5)

    @pytest.mark.parametrize(
        ("side", "point"),
        [
            ("left", (1, 5)),
            ("right", (5, 5)),
            ("top", (3, 2)),
            ("bottom", (3, 8)),
        ],
    )
    def test_side_midpoints(self, side: Side, point: tuple[float, float]) -> None:
        assert Rect(1, 2, 4, 6).side_midpoint(side) == point

    def test_zero_size_is_allowed(self) -> None:
        rect = Rect(2, 3, 0, 0)
        assert rect.center == (2, 3)

    @pytest.mark.parametrize(("width", "height"), [(-1, 1), (1, -1)])
    def test_negative_size_is_rejected(self, width: float, height: float) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            Rect(0, 0, width, height)

    def test_rect_is_frozen(self) -> None:
        rect = Rect(0, 0, 1, 1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            rect.x = 2  # type: ignore[misc]

    def test_equal_rects_compare_and_hash_equal(self) -> None:
        assert Rect(0, 0, 1, 2) == Rect(0, 0, 1, 2)
        assert len({Rect(0, 0, 1, 2), Rect(0, 0, 1, 2)}) == 1


class TestLayout:
    def test_lookup_by_path(self) -> None:
        layout = _layout()
        assert layout.rect(()) == Rect(0, 0, 10, 4)
        assert layout.rect((1,)) == Rect(5, 1, 2, 2)

    def test_lookup_by_id(self) -> None:
        assert _layout().box("model") == Rect(5, 1, 2, 2)

    def test_unknown_path_names_the_path(self) -> None:
        with pytest.raises(KeyError, match=r"no node at path \(2,\); .* 3 node"):
            _layout().rect((2,))

    def test_unknown_id_lists_valid_ids(self) -> None:
        with pytest.raises(KeyError, match="'modle'; valid ids: 'data', 'model'"):
            _layout().box("modle")

    def test_unknown_id_without_any_ids(self) -> None:
        layout = Layout(width=1, height=1, rects={(): Rect(0, 0, 1, 1)})
        with pytest.raises(KeyError, match="no box in the layout has an id"):
            layout.box("data")

    def test_id_pointing_at_missing_path_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"'data' -> path \(3,\)"):
            Layout(width=1, height=1, rects={(): Rect(0, 0, 1, 1)}, ids={"data": (3,)})

    def test_id_pointing_at_root_names_root(self) -> None:
        with pytest.raises(ValueError, match="'data' -> root"):
            Layout(width=1, height=1, rects={}, ids={"data": ()})

    def test_negative_size_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            Layout(width=-1, height=1, rects={})

    def test_mappings_are_read_only_copies(self) -> None:
        rects: dict[NodePath, Rect] = {(): Rect(0, 0, 1, 1)}
        layout = Layout(width=1, height=1, rects=rects)
        rects[(0,)] = Rect(0, 0, 1, 1)
        assert (0,) not in layout.rects
        with pytest.raises(TypeError):
            layout.rects[(1,)] = Rect(0, 0, 1, 1)  # type: ignore[index]

    def test_layout_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            _layout().width = 3  # type: ignore[misc]

    def test_equal_layouts_compare_equal(self) -> None:
        assert _layout() == _layout()
        assert _layout() != dataclasses.replace(_layout(), width=11)


class TestBoxSize:
    def test_text_plus_padding_on_each_side(self) -> None:
        text = measure_text(LONG, THEME, 1.0, subtitle="two\nlines", eyebrow="STEP")
        box = Box(label=LONG, subtitle="two\nlines", eyebrow="STEP")
        pad = 2 * THEME.text_padding
        assert box_size(box, THEME, 1.0) == pytest.approx(
            (text.width + pad, text.height + pad)
        )

    def test_short_text_is_clamped_to_the_minimum(self) -> None:
        assert box_size(Box(label="A"), ROOMY, 1.0) == (
            ROOMY.min_box_width,
            ROOMY.min_box_height,
        )

    def test_width_and_height_clamp_independently(self) -> None:
        width, height = box_size(Box(label=LONG), ROOMY, 1.0)
        assert width > ROOMY.min_box_width
        assert height == ROOMY.min_box_height

    def test_fixed_width_wins_and_height_stays_automatic(self) -> None:
        tall = Box(label="A\nB\nC\nD", width=0.5)
        width, height = box_size(tall, THEME, 1.0)
        assert width == 0.5
        assert height > THEME.min_box_height

    def test_fixed_height_wins_and_width_stays_automatic(self) -> None:
        width, height = box_size(Box(label=LONG, height=0.2), THEME, 1.0)
        assert height == 0.2
        assert width > THEME.min_box_width

    def test_fully_fixed_box_ignores_its_text(self) -> None:
        missing_font = THEME.model_copy(update={"font_family": "No Such Sans"})
        box = Box(label=LONG, width=2, height=1)
        assert box_size(box, missing_font, 1.0) == (2, 1)

    def test_padding_comes_from_the_theme(self) -> None:
        roomy = THEME.model_copy(update={"text_padding": THEME.text_padding + 1})
        base = box_size(Box(label=LONG), THEME, 1.0)
        assert box_size(Box(label=LONG), roomy, 1.0)[0] == pytest.approx(base[0] + 2)

    def test_larger_scale_shrinks_text_but_not_padding(self) -> None:
        box = Box(label=LONG)
        pad = 2 * THEME.text_padding
        at_one = box_size(box, THEME, 1.0)[0] - pad
        at_two = box_size(box, THEME, 2.0)[0] - pad
        assert at_two == pytest.approx(at_one / 2)


def _fixed(width: float, height: float) -> Box:
    return Box(label="x", width=width, height=height)


class TestNodeSizes:
    def test_single_child_row_is_the_child_plus_padding(self) -> None:
        sizes = node_sizes(Row(padding=0.5, children=[_fixed(2, 1)]), THEME, 1.0)
        assert sizes == {(0,): (2, 1), (): (3, 2)}

    def test_row_adds_widths_and_gaps_and_takes_the_tallest(self) -> None:
        row = Row(gap=0.5, children=[_fixed(1, 1), _fixed(2, 3), _fixed(1, 2)])
        assert node_sizes(row, THEME, 1.0)[()] == (5, 3)

    def test_column_is_the_transpose(self) -> None:
        column = Column(gap=0.5, children=[_fixed(1, 1), _fixed(3, 2), _fixed(2, 1)])
        assert node_sizes(column, THEME, 1.0)[()] == (3, 5)

    def test_gap_none_uses_the_theme_gap(self) -> None:
        wide = THEME.model_copy(update={"gap": 2.5})
        row = Row(children=[_fixed(1, 1), _fixed(1, 1)])
        assert node_sizes(row, wide, 1.0)[()] == (4.5, 1)

    def test_explicit_zero_gap_overrides_the_theme(self) -> None:
        row = Row(gap=0, children=[_fixed(1, 1), _fixed(1, 1)])
        assert node_sizes(row, THEME, 1.0)[()] == (2, 1)

    def test_spacer_adds_exactly_its_size_with_no_gaps(self) -> None:
        row = Row(gap=2, children=[_fixed(1, 1), Spacer(size=1), _fixed(2, 1)])
        sizes = node_sizes(row, THEME, 1.0)
        assert (sizes[()], sizes[(1,)]) == ((4, 1), (1, 0))

    def test_spacer_in_a_column_adds_height(self) -> None:
        column = Column(gap=2, children=[_fixed(1, 1), Spacer(size=3)])
        sizes = node_sizes(column, THEME, 1.0)
        assert (sizes[(1,)], sizes[()]) == ((0, 3), (1, 4))

    def test_adjacent_spacers_have_no_gap_between_them(self) -> None:
        row = Row(gap=1, children=[Spacer(size=1), Spacer(size=2), _fixed(1, 1)])
        assert node_sizes(row, THEME, 1.0)[()] == (4, 1)

    def test_spacers_only_container_has_no_cross_size(self) -> None:
        assert node_sizes(Row(children=[Spacer(size=2)]), THEME, 1.0)[()] == (2, 0)

    def test_padding_applies_on_all_four_sides(self) -> None:
        column = Column(padding=1, gap=0, children=[_fixed(2, 1), _fixed(2, 1)])
        assert node_sizes(column, THEME, 1.0)[()] == (4, 4)

    def test_three_levels_of_nesting(self) -> None:
        inner = Row(gap=0.5, children=[_fixed(1, 1), _fixed(1, 2)])
        middle = Column(gap=1, padding=0.25, children=[inner, _fixed(3, 1)])
        outer = Row(gap=2, padding=0.5, children=[_fixed(1, 1), middle])
        sizes = node_sizes(outer, THEME, 1.0)
        assert (sizes[(1, 0)], sizes[(1,)], sizes[()]) == (
            (2.5, 2),
            (3.5, 4.5),
            (7.5, 5.5),
        )
        assert set(sizes) == {(), (0,), (1,), (1, 0), (1, 0, 0), (1, 0, 1), (1, 1)}

    def test_measured_boxes_feed_the_container(self) -> None:
        row = Row(gap=1, children=[Box(label=LONG), Box(label="A")])
        sizes = node_sizes(row, THEME, 1.0)
        assert sizes[()][0] == pytest.approx(sizes[(0,)][0] + 1 + sizes[(1,)][0])
