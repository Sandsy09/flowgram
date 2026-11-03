import struct
from pathlib import Path
from xml.etree import ElementTree

import matplotlib as mpl
import pytest
from matplotlib.image import imread

from flowgram import Box, Diagram, Row, Theme
from flowgram.export import DEFAULT_DPI, EXPORT_FORMATS, export_format
from tests.conftest import spec_pipeline

SVG = "{http://www.w3.org/2000/svg}"


def _one_box(**diagram: object) -> Diagram:
    """A 2 x 1 unit box with the default padding of 0.5: 3 x 2 inches."""
    root = Row(children=[Box(label="Hello", width=2, height=1)])
    return Diagram(root=root, **diagram)  # type: ignore[arg-type]


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _svg_root(path: Path) -> ElementTree.Element:
    return ElementTree.parse(path).getroot()


class TestExportFormat:
    @pytest.mark.parametrize(
        ("name", "fmt"),
        [("a.png", "png"), ("a.svg", "svg"), ("a.pdf", "pdf"), ("dir/A.SVG", "svg")],
    )
    def test_comes_from_the_extension(self, name: str, fmt: str) -> None:
        assert export_format(name) == fmt
        assert export_format(Path(name)) == fmt

    def test_unknown_extension_names_the_choices(self) -> None:
        with pytest.raises(
            ValueError, match=r"'a\.jpg'.*extension \.jpg.*\.png, \.svg, \.pdf"
        ):
            export_format("a.jpg")

    def test_missing_extension_says_so(self) -> None:
        with pytest.raises(ValueError, match="no file extension"):
            export_format("diagram")

    def test_formats(self) -> None:
        assert EXPORT_FORMATS == ("png", "svg", "pdf")


class TestSave:
    def test_png(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        _one_box().save(path)
        assert _png_size(path) == (3 * DEFAULT_DPI, 2 * DEFAULT_DPI)

    def test_svg_keeps_text_as_text(self, tmp_path: Path) -> None:
        path = tmp_path / "out.svg"
        _one_box().save(path)
        root = _svg_root(path)
        assert root.tag == f"{SVG}svg"
        assert (root.get("width"), root.get("height")) == ("216pt", "144pt")
        texts = [t.text for t in root.iter(f"{SVG}text")]
        assert texts == ["Hello"]

    def test_svg_embed_fonts_draws_text_as_paths(self, tmp_path: Path) -> None:
        path = tmp_path / "out.svg"
        _one_box().save(path, embed_fonts=True)
        root = _svg_root(path)
        assert list(root.iter(f"{SVG}text")) == []
        glyphs = [p.get("id") for p in root.iter(f"{SVG}path") if p.get("id")]
        assert any(str(g).startswith("DejaVuSans-") for g in glyphs)

    def test_pdf(self, tmp_path: Path) -> None:
        path = tmp_path / "out.pdf"
        _one_box().save(path)
        data = path.read_bytes()
        assert data.startswith(b"%PDF-")
        assert data.rstrip().endswith(b"%%EOF")
        assert b"/MediaBox [ 0 0 216 144 ]" in data

    def test_accepts_a_string_path(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        _one_box().save(str(path))
        assert path.exists()

    def test_extension_is_not_case_sensitive(self, tmp_path: Path) -> None:
        path = tmp_path / "OUT.PDF"
        _one_box().save(path)
        assert path.read_bytes().startswith(b"%PDF-")

    def test_unknown_extension_writes_nothing(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match=r"\.jpg"):
            _one_box().save(tmp_path / "out.jpg")
        assert list(tmp_path.iterdir()) == []

    def test_dpi_sets_the_png_size(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        _one_box(scale=0.5).save(path, dpi=100)
        assert _png_size(path) == (150, 100)

    @pytest.mark.parametrize("dpi", [0, -10, float("inf"), float("nan")])
    def test_bad_dpi_is_rejected(self, tmp_path: Path, dpi: float) -> None:
        with pytest.raises(ValueError, match="dpi must be a positive number"):
            _one_box().save(tmp_path / "out.png", dpi=dpi)

    def test_background_is_drawn(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        theme = Theme.light().model_copy(update={"background": "#FF0000"})
        _one_box(theme=theme).save(path, dpi=10)
        assert tuple(imread(path)[0, 0]) == (1, 0, 0, 1)

    def test_transparent_leaves_the_background_out(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        theme = Theme.light().model_copy(update={"background": "#FF0000"})
        _one_box(theme=theme).save(path, dpi=10, transparent=True)
        pixels = imread(path)
        assert pixels[0, 0, 3] == 0
        assert pixels[10, 15, 3] == 1  # the middle of the box stays solid

    def test_no_background_is_transparent(self, tmp_path: Path) -> None:
        path = tmp_path / "out.png"
        theme = Theme.light().model_copy(update={"background": None})
        _one_box(theme=theme).save(path, dpi=10)
        assert imread(path)[0, 0, 3] == 0

    def test_user_settings_do_not_change_the_file(self, tmp_path: Path) -> None:
        plain, styled = tmp_path / "plain.svg", tmp_path / "styled.svg"
        spec_pipeline().save(plain)
        user = {
            "svg.fonttype": "path",
            "savefig.facecolor": "red",
            "savefig.bbox": "tight",
            "savefig.transparent": True,
        }
        with mpl.rc_context(user):  # type: ignore[arg-type]
            spec_pipeline().save(styled)
            assert mpl.rcParams["svg.fonttype"] == "path"
        assert _strip_date(styled) == _strip_date(plain)

    def test_overwrites_an_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.svg"
        path.write_text("old", encoding="utf-8")
        _one_box().save(path)
        assert _svg_root(path).tag == f"{SVG}svg"


def _strip_date(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if "dc:date" not in line
    ]
