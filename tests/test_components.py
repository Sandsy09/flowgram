"""Tests for boxes, spacers, containers and edges."""

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from flowgram import Box, Column, Edge, Row, Spacer
from flowgram.components import Child, iter_boxes

Container = type[Row] | type[Column]


def _box(**fields: Any) -> Box:
    return Box.model_validate({"label": "A", **fields})


def _container(kind: Container, **fields: Any) -> Row | Column:
    children = fields.pop("children", [Box(label="A")])
    return kind.model_validate({"children": children, **fields})


def _edge(**fields: Any) -> Edge:
    return Edge.model_validate({"src": "a", "dst": "b", **fields})


class TestBox:
    def test_minimal_box_uses_defaults(self) -> None:
        box = Box(label="Data")
        assert box.id is None
        assert box.role == "default"
        assert box.width is None
        assert box.height is None

    @pytest.mark.parametrize("fields", [{"label": ""}, {"id": ""}])
    def test_empty_text_fields_are_rejected(self, fields: dict[str, str]) -> None:
        with pytest.raises(ValidationError):
            _box(**fields)

    def test_misspelt_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _box(colour="red")

    @pytest.mark.parametrize(
        "field", ["fill", "stroke", "text_color", "eyebrow_color", "subtitle_color"]
    )
    def test_bad_colour_overrides_are_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            _box(**{field: "nope"})

    @pytest.mark.parametrize("field", ["width", "height", "line_width"])
    def test_sizes_must_be_positive(self, field: str) -> None:
        with pytest.raises(ValidationError):
            _box(**{field: 0})

    def test_corner_radius_may_be_zero(self) -> None:
        assert Box(label="A", corner_radius=0).corner_radius == 0

    def test_box_is_frozen(self) -> None:
        box = Box(label="A")
        with pytest.raises(ValidationError):
            box.label = "B"

    def test_model_copy_builds_a_variant(self) -> None:
        box = Box(id="a", label="A")
        assert box.model_copy(update={"role": "accent"}).role == "accent"
        assert box.role == "default"

    def test_text_styling_defaults_to_the_theme(self) -> None:
        box = Box(label="A")
        assert box.eyebrow is None
        assert box.text_align is None
        assert box.text_valign is None
        assert box.eyebrow_color is None

    def test_three_text_tiers(self) -> None:
        box = Box(eyebrow="STEP 2", label="Health score", subtitle="Wear\nindex")
        assert (box.eyebrow, box.label, box.subtitle) == (
            "STEP 2",
            "Health score",
            "Wear\nindex",
        )

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_text_align_values(self, align: str) -> None:
        assert _box(text_align=align).text_align == align

    def test_unknown_text_align_lists_the_choices(self) -> None:
        with pytest.raises(ValidationError, match="'left', 'center' or 'right'"):
            _box(text_align="justify")

    @pytest.mark.parametrize("valign", ["top", "center"])
    def test_text_valign_values(self, valign: str) -> None:
        assert _box(text_valign=valign).text_valign == valign

    def test_unknown_text_valign_lists_the_choices(self) -> None:
        with pytest.raises(ValidationError, match="'top' or 'center'"):
            _box(text_valign="bottom")

    def test_empty_eyebrow_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _box(eyebrow="")

    def test_bad_eyebrow_colour_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="eyebrow_color"):
            _box(eyebrow_color="nope")

    def test_every_problem_is_reported_at_once(self) -> None:
        with pytest.raises(ValidationError) as caught:
            _box(eyebrow="", text_align="justify", eyebrow_color="nope")
        assert caught.value.error_count() == 3


class TestSpacer:
    def test_size_is_required(self) -> None:
        with pytest.raises(ValidationError):
            Spacer.model_validate({})

    def test_zero_is_allowed_but_negative_is_not(self) -> None:
        assert Spacer(size=0).size == 0
        with pytest.raises(ValidationError):
            Spacer(size=-1)


@pytest.mark.parametrize("container", [Row, Column])
class TestContainers:
    def test_defaults(self, container: Container) -> None:
        node = _container(container)
        assert node.gap is None
        assert node.align == "center"
        assert node.padding == 0
        assert node.uniform is False

    def test_children_list_becomes_a_tuple(self, container: Container) -> None:
        node = container(children=[Box(label="A"), Spacer(size=1)])
        assert isinstance(node.children, tuple)
        assert len(node.children) == 2

    def test_children_may_be_given_as_a_tuple(self, container: Container) -> None:
        node = container(children=(Box(label="A"),))
        assert len(node.children) == 1

    def test_empty_container_is_rejected(self, container: Container) -> None:
        with pytest.raises(ValidationError, match="at least 1 item"):
            _container(container, children=[])

    @pytest.mark.parametrize("field", ["gap", "padding"])
    def test_negative_spacing_is_rejected(
        self, container: Container, field: str
    ) -> None:
        with pytest.raises(ValidationError):
            _container(container, **{field: -1})

    def test_unknown_alignment_is_rejected(self, container: Container) -> None:
        with pytest.raises(ValidationError):
            _container(container, align="middle")

    def test_containers_nest(self, container: Container) -> None:
        inner = Column(children=[Box(label="A")])
        outer = container(children=[inner, Row(children=[Box(label="B")])])
        assert isinstance(outer.children[0], Column)
        assert isinstance(outer.children[1], Row)


def test_iter_boxes_walks_depth_first_in_layout_order() -> None:
    tree = Row(
        children=[
            Box(id="a", label="A"),
            Spacer(size=1),
            Column(
                children=[
                    Box(id="b", label="B"),
                    Row(children=[Box(id="c", label="C"), Box(id="d", label="D")]),
                ]
            ),
            Box(id="e", label="E"),
        ]
    )
    assert [box.id for box in iter_boxes(tree)] == ["a", "b", "c", "d", "e"]


def test_iter_boxes_skips_spacers() -> None:
    assert list(iter_boxes(Spacer(size=1))) == []


def test_child_union_needs_kind_when_loading_from_data() -> None:
    adapter: TypeAdapter[Child] = TypeAdapter(Child)
    assert isinstance(adapter.validate_python({"kind": "box", "label": "A"}), Box)
    with pytest.raises(ValidationError, match="kind"):
        adapter.validate_python({"label": "A"})


def test_nested_containers_load_from_dicts() -> None:
    data = {
        "kind": "row",
        "children": [
            {"kind": "box", "label": "A", "id": "a"},
            {"kind": "column", "children": [{"kind": "spacer", "size": 2}]},
        ],
    }
    row = TypeAdapter(Child).validate_python(data)
    assert isinstance(row, Row)
    assert isinstance(row.children[1], Column)


class TestEdge:
    def test_defaults(self) -> None:
        edge = Edge(src="a", dst="b")
        assert edge.exit is None
        assert edge.entry is None
        assert edge.routing == "auto"
        assert edge.style == "solid"
        assert edge.arrow == "end"

    def test_sides_are_plain_strings(self) -> None:
        edge = Edge(src="a", dst="b", exit="right", entry="left")
        assert edge.exit == "right"
        assert edge.entry == "left"

    @pytest.mark.parametrize("field", ["exit", "entry"])
    def test_unknown_side_is_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError):
            _edge(**{field: "middle"})

    @pytest.mark.parametrize(
        ("field", "value"),
        [("routing", "curved"), ("style", "wavy"), ("arrow", "start")],
    )
    def test_unknown_options_are_rejected(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError):
            _edge(**{field: value})

    @pytest.mark.parametrize("field", ["src", "dst"])
    def test_ids_must_not_be_empty(self, field: str) -> None:
        with pytest.raises(ValidationError):
            _edge(**{field: ""})

    def test_bad_colour_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="not a colour"):
            Edge(src="a", dst="b", color="nope")

    def test_line_width_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Edge(src="a", dst="b", line_width=0)
