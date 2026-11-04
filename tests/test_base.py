"""Tests for the Spec base model: variants made with model_copy are checked."""

import pytest
from pydantic import ValidationError

from flowgram import Box, Column, Diagram, Edge, Row, Theme


@pytest.fixture
def diagram() -> Diagram:
    return Diagram(
        title="Base",
        root=Row(children=[Box(id="a", label="A"), Box(id="b", label="B")]),
        edges=[Edge(src="a", dst="b")],
    )


def _error(build: object) -> str:
    assert callable(build)
    with pytest.raises(ValidationError) as caught:
        build()
    return str(caught.value)


class TestValidUpdates:
    def test_update_changes_only_the_named_fields(self, diagram: Diagram) -> None:
        variant = diagram.model_copy(update={"title": "Changed", "scale": 2})
        assert (variant.title, variant.scale) == ("Changed", 2)
        assert variant.root is diagram.root
        assert variant.edges == diagram.edges
        assert diagram.title == "Base"

    def test_matches_building_from_scratch(self, diagram: Diagram) -> None:
        variant = diagram.model_copy(update={"title": "Changed"})
        rebuilt = Diagram(title="Changed", root=diagram.root, edges=diagram.edges)
        assert variant == rebuilt
        assert variant.model_fields_set == rebuilt.model_fields_set

    def test_plain_data_is_validated_into_specs(self, diagram: Diagram) -> None:
        variant = diagram.model_copy(
            update={
                "root": {
                    "kind": "column",
                    "children": [
                        {"kind": "box", "id": "a", "label": "A"},
                        {"kind": "box", "id": "c", "label": "C"},
                    ],
                },
                "edges": [{"src": "a", "dst": "c"}],
            }
        )
        assert isinstance(variant.root, Column)
        assert variant.edges == (Edge(src="a", dst="c"),)

    def test_sequences_are_stored_as_tuples(self, diagram: Diagram) -> None:
        variant = diagram.model_copy(update={"edges": [Edge(src="b", dst="a")]})
        assert isinstance(variant.edges, tuple)

    def test_nested_specs_validate_too(self) -> None:
        theme = Theme.light().model_copy(update={"label_size": 14})
        assert theme.label_size == 14
        box = Box(id="a", label="A").model_copy(update={"label": "Changed"})
        assert box.label == "Changed"

    def test_result_is_frozen(self, diagram: Diagram) -> None:
        variant = diagram.model_copy(update={"title": "Changed"})
        with pytest.raises(ValidationError):
            setattr(variant, "title", "Again")  # noqa: B010


class TestBadUpdates:
    def test_bad_value_raises(self, diagram: Diagram) -> None:
        message = _error(lambda: diagram.model_copy(update={"scale": -1}))
        assert "scale" in message
        assert "greater than 0" in message

    def test_every_field_problem_is_reported(self, diagram: Diagram) -> None:
        message = _error(
            lambda: diagram.model_copy(
                update={"scale": -1, "display_format": "jpg", "bogus": 1}
            )
        )
        assert "3 validation errors for Diagram" in message
        for field in ("scale", "display_format", "bogus"):
            assert field in message

    def test_unknown_field_is_rejected(self, diagram: Diagram) -> None:
        message = _error(lambda: diagram.model_copy(update={"titel": "Typo"}))
        assert "titel" in message
        assert "Extra inputs are not permitted" in message

    def test_cross_component_problems_are_reported(self, diagram: Diagram) -> None:
        message = _error(
            lambda: diagram.model_copy(
                update={
                    "root": Row(
                        children=[
                            Box(id="a", label="A", role="nope"),
                            Box(id="a", label="A2"),
                        ]
                    ),
                    "edges": [Edge(src="a", dst="missing")],
                }
            )
        )
        assert "3 problem(s) in the diagram" in message
        assert "'a' is used 2 times" in message
        assert "'nope'" in message
        assert "'missing'" in message

    def test_same_error_as_construction(self, diagram: Diagram) -> None:
        edges = [Edge(src="a", dst="missing")]
        copied = _error(lambda: diagram.model_copy(update={"edges": edges}))
        built = _error(lambda: Diagram(title="Base", root=diagram.root, edges=edges))
        assert copied == built

    def test_nested_spec_update_is_checked(self) -> None:
        message = _error(lambda: Theme.light().model_copy(update={"roles": {}}))
        assert "must define a 'default' role" in message
        message = _error(lambda: Box(label="A").model_copy(update={"width": 0}))
        assert "width" in message


class TestPlainCopies:
    def test_no_update_is_an_equal_copy(self, diagram: Diagram) -> None:
        updates: tuple[dict[str, object] | None, ...] = (None, {})
        for update in updates:
            copy = diagram.model_copy(update=update)
            assert copy == diagram
            assert copy is not diagram
            assert copy.root is diagram.root

    def test_deep_copy_shares_nothing(self, diagram: Diagram) -> None:
        copy = diagram.model_copy(deep=True)
        assert copy == diagram
        assert copy.root is not diagram.root

    def test_deep_copy_with_update(self, diagram: Diagram) -> None:
        copy = diagram.model_copy(update={"title": "Deep"}, deep=True)
        assert copy.title == "Deep"
        assert copy.root == diagram.root
        assert copy.root is not diagram.root

    def test_deep_copy_with_bad_update_raises(self, diagram: Diagram) -> None:
        with pytest.raises(ValidationError):
            diagram.model_copy(update={"scale": 0}, deep=True)
