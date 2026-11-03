"""Tests for measuring box text.

Exact sizes depend on the platform's font rendering, so these tests assert
relations and tolerances rather than exact numbers.
"""

import struct
from pathlib import Path

import pytest
from matplotlib import font_manager

from flowgram import Theme, _text
from flowgram._text import baselines, measure_text, text_size

THEME = Theme.light()


def test_longer_label_is_wider() -> None:
    short = measure_text("Model", THEME, 1.0)
    long = measure_text("Model training", THEME, 1.0)
    assert long.width > short.width
    assert long.height == pytest.approx(short.height)


def test_subtitle_adds_height_and_a_gap() -> None:
    plain = measure_text("Clean", THEME, 1.0)
    with_sub = measure_text("Clean", THEME, 1.0, subtitle="impute")
    sub = with_sub.tiers[1]
    gap = THEME.label_size * THEME.tier_gap / 72
    assert sub.kind == "subtitle"
    assert sub.top == pytest.approx(plain.height + gap)
    assert with_sub.height == pytest.approx(plain.height + gap + sub.height)


def test_eyebrow_sits_above_the_label() -> None:
    block = measure_text("Health score", THEME, 1.0, eyebrow="STEP 2", subtitle="x")
    assert [tier.kind for tier in block.tiers] == ["eyebrow", "label", "subtitle"]
    assert block.tiers[0].top == 0
    tops = [tier.top for tier in block.tiers]
    assert tops == sorted(tops)


def test_width_is_the_widest_tier() -> None:
    block = measure_text("A", THEME, 1.0, subtitle="a much longer subtitle")
    assert block.width == pytest.approx(max(tier.width for tier in block.tiers))
    assert block.width == pytest.approx(block.tiers[1].width)


def test_newline_adds_a_line() -> None:
    one = measure_text("Raw data", THEME, 1.0)
    two = measure_text("Raw\ndata", THEME, 1.0)
    assert two.height > one.height * 1.8
    assert two.width < one.width


def test_doubling_scale_halves_the_units() -> None:
    at_one = measure_text("Features", THEME, 1.0, subtitle="scaled")
    at_two = measure_text("Features", THEME, 2.0, subtitle="scaled")
    assert at_two.width == pytest.approx(at_one.width / 2)
    assert at_two.height == pytest.approx(at_one.height / 2)


def test_label_size_drives_width() -> None:
    big = THEME.model_copy(update={"label_size": THEME.label_size * 2})
    normal = measure_text("Model", THEME, 1.0)
    assert measure_text("Model", big, 1.0).width == pytest.approx(
        normal.width * 2, rel=0.05
    )


def test_bold_is_wider_than_normal() -> None:
    light = THEME.model_copy(update={"label_weight": "normal"})
    bold = measure_text("Wide label", THEME, 1.0)
    assert bold.width > measure_text("Wide label", light, 1.0).width


def test_measuring_is_stable() -> None:
    first = measure_text("Model", THEME, 1.0, subtitle="again")
    assert measure_text("Model", THEME, 1.0, subtitle="again") == first


def test_a_point_of_text_is_a_seventy_second_of_an_inch() -> None:
    block = measure_text("Model", THEME, 1.0)
    # One line is about as tall as its font size: 11 pt is 11/72 inch.
    size = THEME.label_size / 72
    assert 0.8 * size <= block.height <= 1.25 * size


def test_line_height_does_not_depend_on_the_letters() -> None:
    flat = measure_text("aaa", THEME, 1.0)
    tall = measure_text("Égjy|", THEME, 1.0)
    assert tall.height == flat.height


@pytest.mark.parametrize("empty", [None, ""])
def test_missing_tiers_are_skipped(empty: str | None) -> None:
    block = measure_text("Model", THEME, 1.0, subtitle=empty, eyebrow=empty)
    assert [tier.kind for tier in block.tiers] == ["label"]
    assert block.height == pytest.approx(block.tiers[0].height)


def test_unknown_font_family_is_a_clear_error() -> None:
    theme = THEME.model_copy(update={"font_family": "No Such Sans"})
    with pytest.raises(ValueError, match="'No Such Sans' is not installed"):
        measure_text("Model", theme, 1.0)


def test_no_text_measures_as_empty() -> None:
    block = measure_text("", THEME, 1.0)
    assert (block.width, block.height, block.tiers) == (0, 0, ())


def test_text_size_matches_a_label_tier() -> None:
    block = measure_text("Model", THEME, 2.0)
    size = text_size(
        "Model",
        THEME.label_size,
        THEME.label_weight,
        "DejaVu Sans",
        2.0,
        line_spacing=THEME.line_spacing,
    )
    assert size == (block.width, block.height)


def test_text_size_checks_the_font() -> None:
    with pytest.raises(ValueError, match="'No Such Sans' is not installed"):
        text_size("Model", 11, "normal", "No Such Sans", 1.0, line_spacing=1.2)


def test_looser_line_spacing_adds_height_between_lines() -> None:
    loose = THEME.model_copy(update={"line_spacing": 1.8})
    tight = measure_text("Raw\ndata", THEME, 1.0)
    spaced = measure_text("Raw\ndata", loose, 1.0)
    # Each of the two lines grows by the extra spacing. DejaVu Sans's ascent
    # plus descent is exactly one font size.
    extra = (1.8 - THEME.line_spacing) * THEME.label_size / 72
    assert spaced.height - tight.height == pytest.approx(2 * extra)
    assert spaced.width == pytest.approx(tight.width)


def test_lines_are_the_same_height_whatever_their_letters() -> None:
    heights = {measure_text(text, THEME, 1.0).height for text in ["x", "Ág", ",", "|"]}
    assert len(heights) == 1
    assert heights.pop() == pytest.approx(THEME.line_spacing * THEME.label_size / 72)


@pytest.mark.parametrize("line_spacing", [1.0, 1.2, 1.8])
@pytest.mark.parametrize("scale", [0.5, 1.0])
def test_baselines_are_evenly_spaced_inside_the_measured_height(
    line_spacing: float, scale: float
) -> None:
    text = "one\ntwo\nthree"
    size = 11.0
    ys = baselines(
        text, size, "normal", "DejaVu Sans", scale, line_spacing=line_spacing
    )
    height = text_size(
        text, size, "normal", "DejaVu Sans", scale, line_spacing=line_spacing
    )[1]
    ascent, descent = _text._font_metrics("DejaVu Sans", "normal")
    to_units = 1 / (72 * scale)
    pitch = line_spacing * size * to_units
    half_leading = (line_spacing - 1) * size * to_units / 2
    assert ys == pytest.approx(
        [half_leading + ascent * size * to_units + k * pitch for k in range(3)]
    )
    # The last line's descent and half its leading end the text.
    assert ys[-1] + descent * size * to_units + half_leading == pytest.approx(height)


def test_baselines_check_the_font() -> None:
    with pytest.raises(ValueError, match="'No Such Sans' is not installed"):
        baselines("x", 11, "normal", "No Such Sans", 1.0, line_spacing=1.2)


def test_dejavu_metrics_come_from_its_os2_table() -> None:
    ascent, descent = _text._font_metrics("DejaVu Sans", "bold")
    assert (ascent * 2048, descent * 2048) == pytest.approx((1556, 492))


def _font_file(path: Path, tables: dict[bytes, bytes], *, collection: bool) -> str:
    """Write a minimal font file holding just ``tables``."""
    body = b""
    start = 16 if collection else 0
    offset = start + 12 + 16 * len(tables)
    records = b""
    for tag, table in tables.items():
        records += struct.pack(">4sIII", tag, 0, offset + len(body), len(table))
        body += table
    font = struct.pack(">IHHHH", 0x00010000, len(tables), 0, 0, 0) + records + body
    if collection:
        font = struct.pack(">4sIII", b"ttcf", 0x00010000, 1, start) + font
    path.write_bytes(font)
    return str(path)


@pytest.mark.parametrize("collection", [False, True])
def test_typo_metrics_are_read_from_the_os2_table(
    tmp_path: Path, collection: bool
) -> None:
    os2 = bytes(68) + struct.pack(">hh", 800, -200) + bytes(20)
    tables = {b"head": bytes(54), b"OS/2": os2}
    font = _font_file(tmp_path / "font.ttf", tables, collection=collection)
    assert _text._typo_metrics(font) == (800, -200)


def test_typo_metrics_are_none_without_an_os2_table(tmp_path: Path) -> None:
    font = _font_file(tmp_path / "font.ttf", {b"head": bytes(54)}, collection=False)
    assert _text._typo_metrics(font) is None


class _FreeTypeFont:
    ascender = 900
    descender = -300
    units_per_EM = 1000  # noqa: N815 (FreeType's name)


def test_metrics_fall_back_to_freetype_without_an_os2_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(font_manager, "get_font", lambda path: _FreeTypeFont())
    monkeypatch.setattr(_text, "_typo_metrics", lambda path: None)
    _text._font_metrics.cache_clear()
    try:
        assert _text._font_metrics("DejaVu Sans", "normal") == pytest.approx((0.9, 0.3))
    finally:
        _text._font_metrics.cache_clear()
