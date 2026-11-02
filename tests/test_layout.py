"""Tests for layout result types."""

import dataclasses

import pytest

from flowgram.components import Side
from flowgram.layout import Layout, NodePath, Rect


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
