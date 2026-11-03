"""Tests that the docs' code runs and the API reference covers every public name."""

import re
from pathlib import Path

import pytest

from flowgram import Diagram

DOCS = Path(__file__).parent.parent / "docs"
SRC = Path(__file__).parent.parent / "src"
FENCE = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
PAGES = sorted(
    path.relative_to(DOCS).as_posix()
    for path in [DOCS / "index.md", *DOCS.glob("guide/*.md")]
)


def _run_page(page: str) -> dict[str, object]:
    namespace: dict[str, object] = {"__name__": "docs"}
    text = (DOCS / page).read_text(encoding="utf-8")
    for block in FENCE.findall(text):
        exec(block, namespace)
    return namespace


@pytest.mark.parametrize("page", PAGES)
def test_page_code_runs(
    page: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    namespace = _run_page(page)
    if "spec" in namespace:
        assert isinstance(namespace["spec"], Diagram)


def test_export_page_writes_every_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _run_page("guide/export.md")
    assert {path.name for path in tmp_path.iterdir()} == {
        "diagram.png",
        "diagram.svg",
        "diagram.pdf",
    }


def test_fit_width_comes_close(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    namespace = _run_page("guide/jupyter-and-powerpoint.md")
    assert namespace["width"] == pytest.approx(12, rel=0.005)


def test_every_guide_page_is_in_the_nav() -> None:
    nav = (DOCS.parent / "mkdocs.yml").read_text(encoding="utf-8")
    for page in DOCS.glob("guide/*.md"):
        assert f"guide/{page.name}" in nav


@pytest.fixture(scope="module")
def package() -> object:
    griffe = pytest.importorskip("griffe")
    return griffe.load("flowgram", search_paths=[str(SRC)])


class TestReference:
    def _documented(self) -> list[str]:
        text = (DOCS / "reference.md").read_text(encoding="utf-8")
        return re.findall(r"^::: (\S+)$", text, re.MULTILINE)

    def test_every_public_module_is_documented(self, package: object) -> None:
        modules = {
            f"flowgram.{name}"
            for name, member in package.modules.items()  # type: ignore[attr-defined]
            if not name.startswith("_") and not member.is_alias
        }
        assert modules == set(self._documented())

    def test_every_public_name_has_a_docstring(self, package: object) -> None:
        missing = []
        for path in self._documented():
            module = package[path.removeprefix("flowgram.")]  # type: ignore[index]
            for name, member in module.members.items():
                if name.startswith("_") or member.is_alias:
                    continue
                if member.docstring is None:
                    missing.append(f"{path}.{name}")
        assert not missing
