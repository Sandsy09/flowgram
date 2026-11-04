import json
import runpy
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from flowgram import Box, Column, Diagram, Edge, Row, Shadow, Spacer, Theme
from flowgram.loading import YAML_EXTRA_HINT, to_dict, to_json, to_yaml
from tests.conftest import spec_pipeline

EXAMPLES = Path(__file__).parent.parent / "examples"


def _card_flow() -> Diagram:
    spec = runpy.run_path(str(EXAMPLES / "card_flow.py"))["spec"]
    assert isinstance(spec, Diagram)
    return spec


def _styled() -> Diagram:
    """The spec pipeline with its theme and settings away from the defaults."""
    theme = Theme.mono().model_copy(
        update={"shadow": Shadow(dx=-0.1), "line_spacing": 1.4}
    )
    return spec_pipeline().model_copy(
        update={
            "theme": theme,
            "footnote": "Source: tests",
            "scale": 0.8,
            "display_format": "svg",
        }
    )


SPECS = [spec_pipeline, _styled, _card_flow]


@pytest.mark.parametrize("spec", SPECS)
class TestRoundTrip:
    def test_python_dict(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert Diagram.from_dict(diagram.model_dump()) == diagram

    def test_json_compatible_dict(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        data = json.loads(json.dumps(diagram.model_dump(mode="json")))
        assert Diagram.from_dict(data) == diagram

    def test_json(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        text = diagram.model_dump_json()
        assert Diagram.from_json(text) == diagram
        assert Diagram.from_json(text.encode()) == diagram

    def test_yaml(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        text = yaml.safe_dump(diagram.model_dump(mode="json"), sort_keys=False)
        assert Diagram.from_yaml(text) == diagram

    def test_files(self, spec: Callable[[], Diagram], tmp_path: Path) -> None:
        diagram = spec()
        json_path, yaml_path = tmp_path / "spec.json", tmp_path / "spec.yml"
        json_path.write_text(diagram.model_dump_json(indent=2), encoding="utf-8")
        yaml_path.write_text(
            yaml.safe_dump(diagram.model_dump(mode="json")), encoding="utf-8"
        )
        assert Diagram.from_json_file(json_path) == diagram
        assert Diagram.from_json_file(str(json_path)) == diagram
        assert Diagram.from_yaml_file(yaml_path) == diagram
        assert Diagram.from_yaml_file(str(yaml_path)) == diagram


class TestLoading:
    def test_example_yaml_file_is_the_spec_pipeline(self) -> None:
        assert Diagram.from_yaml_file(EXAMPLES / "pipeline.yaml") == spec_pipeline()

    def test_defaults_fill_in(self) -> None:
        diagram = Diagram.from_yaml(
            "root:\n  kind: row\n  children:\n    - {kind: box, label: A}\n"
        )
        assert diagram == Diagram(root=Row(children=[Box(label="A")]))

    def test_no_format_guessing_from_the_extension(self, tmp_path: Path) -> None:
        path = tmp_path / "spec.yaml"
        path.write_text(spec_pipeline().model_dump_json(), encoding="utf-8")
        assert Diagram.from_json_file(path) == spec_pipeline()

    def test_files_are_read_as_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "spec.yaml"
        text = "root: {kind: row, children: [{kind: box, label: Café → ünïcode}]}"
        path.write_bytes(text.encode("utf-8"))
        (box,) = Diagram.from_yaml_file(path).boxes()
        assert box.label == "Café → ünïcode"

    def test_missing_kind_names_the_field(self) -> None:
        with pytest.raises(ValidationError, match="kind"):
            Diagram.from_dict({"root": {"children": [{"label": "A"}]}})

    def test_missing_root_kind_lists_the_choices(self) -> None:
        with pytest.raises(ValidationError) as caught:
            Diagram.from_dict({"root": {"children": [{"kind": "box", "label": "A"}]}})
        message = str(caught.value)
        assert "1 validation error" in message
        assert "'kind' is missing or not one of: 'row', 'column'" in message
        assert "discriminator" not in message

    def test_missing_child_kind_lists_the_choices(self) -> None:
        with pytest.raises(ValidationError) as caught:
            Diagram.from_dict(
                {"root": {"kind": "row", "children": [{"label": "A"}, {"kind": "box"}]}}
            )
        message = str(caught.value)
        assert "2 validation errors" in message
        assert "root.row.children.0\n" in message
        assert "not one of: 'box', 'spacer', 'row', 'column'" in message
        assert "root.row.children.1.box.label\n" in message

    def test_unknown_kind_lists_the_choices(self) -> None:
        with pytest.raises(ValidationError) as caught:
            Diagram.from_dict({"root": {"kind": "grid", "children": []}})
        message = str(caught.value)
        assert "1 validation error" in message
        assert "'kind' is missing or not one of: 'row', 'column'" in message

    def test_built_components_need_no_tag(self) -> None:
        root = Row(children=[Box(label="A"), Column(children=[Spacer(size=1)])])
        assert Diagram(root=root).root is root
        assert Diagram.from_json(Diagram(root=root).to_json()).root == root

    def test_every_problem_is_reported_at_once(self) -> None:
        text = """
root:
  kind: row
  children:
    - {kind: box, id: a, label: A, role: nope}
edges:
  - {src: a, dst: b}
"""
        with pytest.raises(ValidationError, match=r"2 problem\(s\)") as caught:
            Diagram.from_yaml(text)
        assert "role 'nope'" in str(caught.value)
        assert "dst 'b' matches no box" in str(caught.value)

    def test_yaml_top_level_must_be_a_mapping(self) -> None:
        with pytest.raises(ValidationError, match="valid dictionary"):
            Diagram.from_yaml("- just\n- a list\n")

    def test_bad_yaml_raises_a_yaml_error(self) -> None:
        with pytest.raises(yaml.YAMLError):
            Diagram.from_yaml("root: [unclosed\n")

    def test_yaml_cannot_build_python_objects(self) -> None:
        with pytest.raises(yaml.YAMLError):
            Diagram.from_yaml("root: !!python/object/apply:os.getcwd []\n")

    def test_bad_json_is_a_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="Invalid JSON"):
            Diagram.from_json("{not json")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Diagram.from_json_file(tmp_path / "missing.json")


def _kinds(data: object) -> list[object]:
    """The ``kind`` of every component in nested data, ``None`` if missing."""
    found: list[object] = []
    if isinstance(data, dict):
        if "children" in data or "label" in data or "size" in data:
            found.append(data.get("kind"))
        for value in data.values():
            found.extend(_kinds(value))
    elif isinstance(data, list):
        for value in data:
            found.extend(_kinds(value))
    return found


@pytest.mark.parametrize("spec", SPECS)
class TestWriteRoundTrip:
    def test_dict(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert Diagram.from_dict(diagram.to_dict()) == diagram

    def test_dict_is_plain_json_data(self, spec: Callable[[], Diagram]) -> None:
        data = spec().to_dict()
        assert json.loads(json.dumps(data)) == data

    def test_json(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert Diagram.from_json(diagram.to_json()) == diagram
        assert Diagram.from_json(diagram.to_json(indent=None)) == diagram

    def test_yaml(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert Diagram.from_yaml(diagram.to_yaml()) == diagram

    def test_files(self, spec: Callable[[], Diagram], tmp_path: Path) -> None:
        diagram = spec()
        diagram.to_json_file(tmp_path / "spec.json")
        diagram.to_yaml_file(tmp_path / "spec.yaml")
        assert Diagram.from_json_file(tmp_path / "spec.json") == diagram
        assert Diagram.from_yaml_file(tmp_path / "spec.yaml") == diagram

    def test_shorter_than_a_full_dump(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert len(diagram.to_json(indent=None)) < len(diagram.model_dump_json())

    def test_every_component_keeps_its_kind(self, spec: Callable[[], Diagram]) -> None:
        kinds = _kinds(spec().to_dict()["root"])
        assert kinds
        assert None not in kinds

    def test_functions_match_methods(self, spec: Callable[[], Diagram]) -> None:
        diagram = spec()
        assert to_dict(diagram) == diagram.to_dict()
        assert to_json(diagram) == diagram.to_json()
        assert to_yaml(diagram) == diagram.to_yaml()


class TestWriting:
    def test_only_what_differs_from_the_defaults(self) -> None:
        diagram = Diagram(root=Row(children=[Box(id="a", label="A"), Spacer(size=1)]))
        assert diagram.to_dict() == {
            "root": {
                "kind": "row",
                "children": [
                    {"kind": "box", "label": "A", "id": "a"},
                    {"kind": "spacer", "size": 1.0},
                ],
            }
        }

    def test_default_theme_is_left_out(self) -> None:
        assert "theme" not in spec_pipeline().to_dict()

    def test_changed_theme_keeps_what_it_needs_to_load(self) -> None:
        theme = Theme.light().model_copy(update={"label_size": 14})
        diagram = spec_pipeline().model_copy(update={"theme": theme})
        written = diagram.to_dict()["theme"]
        assert written["label_size"] == 14
        assert written["name"] == "light"
        assert "roles" in written
        assert "title_size" not in written
        assert Diagram.from_dict(diagram.to_dict()) == diagram

    def test_spec_pipeline_matches_the_example_file(self) -> None:
        written = yaml.safe_load(spec_pipeline().to_yaml())
        example = yaml.safe_load((EXAMPLES / "pipeline.yaml").read_text("utf-8"))
        assert written == example

    def test_kind_comes_first(self) -> None:
        assert spec_pipeline().to_yaml().startswith("root:\n  kind: row\n")

    def test_multi_line_text_is_a_block(self) -> None:
        diagram = Diagram(root=Column(children=[Box(label="One\nTwo")]))
        text = diagram.to_yaml()
        assert "label: |-\n      One\n      Two\n" in text
        assert Diagram.from_yaml(text) == diagram

    @pytest.mark.parametrize("label", ["a\n", " x\n y ", "a\n\n", "tab\there"])
    def test_awkward_text_round_trips(self, label: str) -> None:
        diagram = Diagram(root=Row(children=[Box(label=label)]))
        assert Diagram.from_yaml(diagram.to_yaml()) == diagram

    def test_unicode_is_written_as_is(self) -> None:
        diagram = Diagram(root=Row(children=[Box(label="Café → 30 °C")]))
        assert "Café → 30 °C" in diagram.to_yaml()
        assert "Café → 30 °C" in diagram.to_json()

    def test_files_end_with_a_newline_and_use_utf8(self, tmp_path: Path) -> None:
        diagram = Diagram(root=Row(children=[Box(label="Café")]))
        diagram.to_json_file(tmp_path / "a.json", indent=None)
        diagram.to_yaml_file(tmp_path / "a.yaml")
        for name in ("a.json", "a.yaml"):
            data = (tmp_path / name).read_bytes()
            assert data.endswith(b"\n")
            assert b"\r\n" not in data
            assert "Café".encode() in data
        assert (tmp_path / "a.json").read_bytes().count(b"\n") == 1

    def test_edges_have_no_kind(self) -> None:
        diagram = Diagram(
            root=Row(children=[Box(id="a", label="A"), Box(id="b", label="B")]),
            edges=[Edge(src="a", dst="b")],
        )
        assert diagram.to_dict()["edges"] == [{"src": "a", "dst": "b"}]


class TestKindIsKept:
    def test_plain_exclude_defaults_loads(self) -> None:
        diagram = spec_pipeline()
        text = diagram.model_dump_json(exclude_defaults=True)
        assert Diagram.from_json(text) == diagram

    def test_exclude_unset_keeps_kind(self) -> None:
        data = Row(children=[Box(label="A")]).model_dump(exclude_unset=True)
        assert data == {"kind": "row", "children": ({"kind": "box", "label": "A"},)}

    def test_full_dump_is_unchanged(self) -> None:
        data = Box(label="A").model_dump()
        assert next(iter(data)) == "kind"
        assert data["kind"] == "box"

    def test_explicit_exclude_still_drops_kind(self) -> None:
        data = Box(label="A").model_dump(exclude_defaults=True, exclude={"kind"})
        assert data == {"label": "A"}

    def test_specs_without_kind_are_unchanged(self) -> None:
        data = Edge(src="a", dst="b").model_dump(exclude_defaults=True)
        assert data == {"src": "a", "dst": "b"}


class TestWithoutPyYAML:
    @pytest.fixture(autouse=True)
    def _hide_yaml(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "yaml", None)

    def test_from_yaml_names_the_extra(self) -> None:
        with pytest.raises(ImportError, match=r'pip install "flowgram\[yaml\]"'):
            Diagram.from_yaml("root: {}")

    def test_from_yaml_file_fails_before_reading(self, tmp_path: Path) -> None:
        with pytest.raises(ImportError, match="needs PyYAML"):
            Diagram.from_yaml_file(tmp_path / "missing.yaml")

    def test_dict_and_json_still_load(self) -> None:
        diagram = spec_pipeline()
        assert Diagram.from_json(diagram.model_dump_json()) == diagram
        assert Diagram.from_dict(diagram.model_dump()) == diagram

    def test_to_yaml_names_the_extra(self, tmp_path: Path) -> None:
        with pytest.raises(ImportError, match="writing YAML needs PyYAML"):
            spec_pipeline().to_yaml()
        with pytest.raises(ImportError, match=r'pip install "flowgram\[yaml\]"'):
            spec_pipeline().to_yaml_file(tmp_path / "spec.yaml")
        assert not (tmp_path / "spec.yaml").exists()

    def test_dict_and_json_still_write(self) -> None:
        diagram = spec_pipeline()
        assert Diagram.from_json(diagram.to_json()) == diagram
        assert Diagram.from_dict(diagram.to_dict()) == diagram

    def test_hint(self) -> None:
        assert YAML_EXTRA_HINT == 'pip install "flowgram[yaml]"'
