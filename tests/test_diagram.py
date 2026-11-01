"""Tests for the Diagram root and its cross-component checks."""

import pytest
from pydantic import ValidationError

from flowgram import Box, Column, Diagram, Edge, Row, Spacer, Theme


def _pipeline() -> Diagram:
    return Diagram(
        title="Model training pipeline",
        root=Row(
            gap=2,
            children=[
                Box(id="data", label="Raw data", role="muted"),
                Column(
                    gap=1,
                    children=[
                        Box(id="clean", label="Clean", subtitle="impute, clip"),
                        Box(id="feats", label="Features"),
                    ],
                ),
                Spacer(size=1),
                Box(id="model", label="Model", role="accent"),
            ],
        ),
        edges=[
            Edge(src="data", dst="clean"),
            Edge(src="data", dst="feats"),
            Edge(src="clean", dst="model", label="train"),
            Edge(src="feats", dst="model", style="dashed"),
        ],
    )


def _row(*boxes: Box) -> Row:
    return Row(children=list(boxes))


def test_valid_diagram_lists_boxes_in_layout_order() -> None:
    assert [box.id for box in _pipeline().boxes()] == [
        "data",
        "clean",
        "feats",
        "model",
    ]


def test_defaults() -> None:
    diagram = Diagram(root=_row(Box(label="A")))
    assert diagram.edges == ()
    assert diagram.theme.name == "light"
    assert diagram.scale == 1.0
    assert diagram.padding == 0.5
    assert diagram.title is None


def test_python_round_trip_keeps_the_spec() -> None:
    diagram = _pipeline()
    assert Diagram.model_validate(diagram.model_dump()) == diagram


def test_json_round_trip_keeps_the_spec() -> None:
    diagram = _pipeline()
    assert Diagram.model_validate_json(diagram.model_dump_json()) == diagram


def test_custom_theme_roles_are_accepted() -> None:
    theme = Theme.light().model_copy(
        update={
            "roles": {**Theme.light().roles, "brand": Theme.light().roles["accent"]}
        }
    )
    diagram = Diagram(root=_row(Box(label="A", role="brand")), theme=theme)
    assert diagram.boxes()[0].role == "brand"


def test_mono_theme_can_be_used() -> None:
    diagram = Diagram(root=_row(Box(label="A")), theme=Theme.mono())
    assert diagram.theme.name == "mono"


def test_duplicate_box_ids_are_rejected() -> None:
    root = _row(Box(id="a", label="A"), Box(id="a", label="B"))
    with pytest.raises(ValidationError, match="box id 'a' is used 2 times"):
        Diagram(root=root)


def test_boxes_without_ids_may_repeat_labels() -> None:
    root = _row(Box(label="Same"), Box(label="Same"))
    assert len(Diagram(root=root).boxes()) == 2


def test_unknown_role_lists_the_valid_roles() -> None:
    root = _row(Box(id="a", label="A", role="nope"))
    with pytest.raises(ValidationError) as caught:
        Diagram(root=root)
    message = str(caught.value)
    assert "box 'a' uses role 'nope'" in message
    assert "valid roles: accent, default, muted, negative, positive" in message


def test_unknown_role_names_unlabelled_box_by_label() -> None:
    root = _row(Box(label="Mystery", role="nope"))
    with pytest.raises(ValidationError, match="box labelled 'Mystery'"):
        Diagram(root=root)


def test_edge_to_missing_box_suggests_close_ids() -> None:
    root = _row(Box(id="encoder", label="E"), Box(id="decoder", label="D"))
    with pytest.raises(ValidationError) as caught:
        Diagram(root=root, edges=[Edge(src="encoder", dst="decodr")])
    message = str(caught.value)
    assert "edge 0 ('encoder' -> 'decodr')" in message
    assert "dst 'decodr' matches no box" in message
    assert "closest ids: 'decoder'" in message


def test_edge_to_missing_box_lists_known_ids_when_nothing_is_close() -> None:
    root = _row(Box(id="encoder", label="E"))
    with pytest.raises(ValidationError, match="known ids: 'encoder'"):
        Diagram(root=root, edges=[Edge(src="encoder", dst="zzzzzz")])


def test_edge_in_a_diagram_with_no_ids_says_so() -> None:
    with pytest.raises(ValidationError, match="no box in the diagram has an id"):
        Diagram(root=_row(Box(label="A")), edges=[Edge(src="a", dst="b")])


def test_self_loop_is_rejected() -> None:
    root = _row(Box(id="a", label="A"))
    with pytest.raises(ValidationError, match="self-loops are not supported"):
        Diagram(root=root, edges=[Edge(src="a", dst="a")])


def test_all_problems_are_reported_together() -> None:
    root = _row(
        Box(id="a", label="A", role="nope"),
        Box(id="a", label="B"),
    )
    with pytest.raises(ValidationError) as caught:
        Diagram(root=root, edges=[Edge(src="a", dst="a"), Edge(src="a", dst="x")])
    message = str(caught.value)
    assert "4 problem(s) in the diagram" in message
    assert message.count("\n- ") == 4


def test_error_does_not_dump_the_whole_input() -> None:
    root = _row(Box(id="a", label="A"), Box(id="a", label="B"))
    with pytest.raises(ValidationError) as caught:
        Diagram(root=root)
    assert "input_value" not in str(caught.value)


def test_root_must_be_a_row_or_column() -> None:
    with pytest.raises(ValidationError):
        Diagram(root=Box(label="A"))  # type: ignore[arg-type]


def test_scale_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Diagram(root=_row(Box(label="A")), scale=0)


def test_padding_may_be_zero_but_not_negative() -> None:
    assert Diagram(root=_row(Box(label="A")), padding=0).padding == 0
    with pytest.raises(ValidationError):
        Diagram(root=_row(Box(label="A")), padding=-1)


def test_diagram_is_frozen() -> None:
    diagram = Diagram(root=_row(Box(label="A")))
    with pytest.raises(ValidationError):
        diagram.title = "Changed"


def test_loading_from_a_dict_needs_kind_markers() -> None:
    data = {
        "root": {
            "kind": "row",
            "children": [{"kind": "box", "id": "a", "label": "A"}],
        },
        "edges": [],
    }
    assert Diagram.model_validate(data).boxes()[0].id == "a"
