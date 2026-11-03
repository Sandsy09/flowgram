"""Tests for the gallery examples and the files built from them.

The SVGs in ``docs/gallery/`` and ``examples/gallery.ipynb`` are written by
``uv run poe gallery``. The notebook check runs everywhere; the image checks
are snapshot tests, so they run on Linux only.
"""

import importlib.util
import os
import runpy
import shutil
import warnings
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from matplotlib.figure import Figure

from flowgram import Diagram

ROOT = Path(__file__).parent.parent
MAX_LINES = 35
"""Most lines of code an example may take, imports included."""

SnapshotCheck = Callable[[Figure, str], None]


def _build_gallery() -> ModuleType:
    path = ROOT / "scripts" / "build_gallery.py"
    spec = importlib.util.spec_from_file_location("build_gallery", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = _build_gallery()
GALLERY: tuple[str, ...] = build.GALLERY


def _load(name: str) -> Diagram:
    spec = build.load(name)
    assert isinstance(spec, Diagram)
    return spec


@pytest.mark.parametrize("name", GALLERY)
class TestExample:
    def test_renders_without_warnings(self, name: str) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            figure = _load(name).render()
        assert isinstance(figure, Figure)

    def test_is_short(self, name: str) -> None:
        _, code = build.parts(name)
        lines = [line for line in code.splitlines() if line.strip()]
        assert len(lines) <= MAX_LINES

    def test_has_a_docstring_with_a_title_line(self, name: str) -> None:
        docstring, _ = build.parts(name)
        title, _, body = docstring.partition("\n")
        assert title.endswith(".")
        assert body.strip()

    def test_running_it_writes_a_png(self, name: str, tmp_path: Path) -> None:
        script = tmp_path / f"{name}.py"
        shutil.copy(build.EXAMPLES / f"{name}.py", script)
        runpy.run_path(str(script), run_name="__main__")
        assert script.with_suffix(".png").read_bytes().startswith(b"\x89PNG")


class TestNotebook:
    def test_is_current(self) -> None:
        committed = build.NOTEBOOK.read_text(encoding="utf-8")
        assert committed == build.notebook(), "run `uv run poe gallery`"

    def test_code_cells_leave_out_the_main_block(self) -> None:
        for name in GALLERY:
            _, code = build.parts(name)
            assert "__main__" not in code
            assert code.startswith(("from ", "import "))

    def test_bad_example_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "broken.py").write_text("spec = 1\n", encoding="utf-8")
        monkeypatch.setattr(build, "EXAMPLES", tmp_path)
        with pytest.raises(TypeError, match=r"broken\.py must set spec"):
            build.load("broken")


@pytest.mark.snapshot
@pytest.mark.parametrize("name", GALLERY)
def test_gallery_image(snapshot: SnapshotCheck, name: str) -> None:
    snapshot(_load(name).render(), f"gallery_{name}")


@pytest.mark.snapshot
@pytest.mark.parametrize("name", GALLERY)
def test_gallery_svg_is_current(name: str) -> None:
    path = build.IMAGES / f"{name}.svg"
    fresh = build.svg(name)
    if os.environ.get("FLOWGRAM_UPDATE_SNAPSHOTS") == "1":
        path.write_text(fresh, encoding="utf-8", newline="\n")
        return
    committed = path.read_text(encoding="utf-8")
    assert committed == fresh, f"{path.name} is stale; run `uv run poe gallery`"
