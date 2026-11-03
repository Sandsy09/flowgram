"""Tests that the README's examples run as written."""

import re
from pathlib import Path

import pytest

from flowgram import Diagram

README = Path(__file__).parent.parent / "README.md"
FENCE = re.compile(r"^```(\w+)\n(.*?)^```", re.DOTALL | re.MULTILINE)


def _blocks(language: str) -> list[str]:
    text = README.read_text(encoding="utf-8")
    return [code for lang, code in FENCE.findall(text) if lang == language]


def test_quick_start_saves_a_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    quick_start, *_ = _blocks("python")
    namespace: dict[str, object] = {}
    exec(quick_start, namespace)
    assert isinstance(namespace["spec"], Diagram)
    assert (tmp_path / "pipeline.png").read_bytes().startswith(b"\x89PNG")


def test_yaml_spec_loads_with_the_loading_snippet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (yaml_spec,) = _blocks("yaml")
    (tmp_path / "pipeline.yaml").write_text(yaml_spec, encoding="utf-8")
    spec = Diagram.from_yaml(yaml_spec)
    (tmp_path / "pipeline.json").write_text(spec.model_dump_json(), encoding="utf-8")
    _, loading = _blocks("python")
    namespace: dict[str, object] = {}
    exec(loading, namespace)
    assert namespace["spec"] == spec


def test_gallery_images_and_links_exist() -> None:
    text = README.read_text(encoding="utf-8")
    root = README.parent
    prefixes = (
        "https://raw.githubusercontent.com/Sandsy09/flowgram/main/",
        "https://github.com/Sandsy09/flowgram/blob/main/",
    )
    paths = {
        url.removeprefix(prefix)
        for url in re.findall(r"\((https://[^)\s]+)\)", text)
        for prefix in prefixes
        if url.startswith(prefix)
    }
    assert {"docs/gallery/branching_flow.svg", "examples/nested_layout.py"} <= paths
    missing = sorted(path for path in paths if not (root / path).exists())
    assert not missing
