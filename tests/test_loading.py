import json
import runpy
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from flowgram import Box, Diagram, Row, Shadow, Theme
from flowgram.loading import YAML_EXTRA_HINT
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

    def test_hint(self) -> None:
        assert YAML_EXTRA_HINT == 'pip install "flowgram[yaml]"'
