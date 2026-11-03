"""Tests that the examples build, lay out and render."""

import runpy
from pathlib import Path

from matplotlib.figure import Figure

from flowgram import Diagram
from flowgram.edges import route
from flowgram.layout import layout

EXAMPLES = Path(__file__).parent.parent / "examples"


def _spec(name: str) -> Diagram:
    spec = runpy.run_path(str(EXAMPLES / f"{name}.py"))["spec"]
    assert isinstance(spec, Diagram)
    return spec


class TestCardFlow:
    def test_cards_have_eyebrow_title_and_body_left_aligned(self) -> None:
        spec = _spec("card_flow")
        cards = [box for box in spec.boxes() if box.eyebrow]
        assert len(cards) == 4
        assert all(box.subtitle for box in cards)
        assert spec.theme.text_align == "left"
        assert (spec.theme.label_weight, spec.theme.eyebrow_weight) == ("bold", "bold")

    def test_top_row_cards_share_one_size(self) -> None:
        spec = _spec("card_flow")
        result = layout(spec)
        sizes = {
            (result.box(i).width, result.box(i).height)
            for i in ("h1", "h2", "r1", "r2")
        }
        assert len(sizes) == 1

    def test_every_edge_runs_left_to_right(self) -> None:
        spec = _spec("card_flow")
        result = layout(spec)
        for edge in spec.edges:
            path = route(edge, result)
            assert (path.exit_side, path.entry_side) == ("right", "left")
            assert len(path.points) == 2

    def test_renders(self) -> None:
        assert isinstance(_spec("card_flow").render(), Figure)
