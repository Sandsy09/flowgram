"""Tests for measuring box text.

Exact sizes depend on the platform's font rendering, so these tests assert
relations and tolerances rather than exact numbers.
"""

import pytest

from flowgram import Theme
from flowgram._text import TIER_GAP, measure_text, text_size

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
    gap = THEME.label_size * TIER_GAP / 72
    assert sub.kind == "subtitle"
    assert sub.top == pytest.approx(plain.height + gap)
    assert with_sub.height == pytest.approx(plain.height + gap + sub.height)


def test_eyebrow_sits_above_the_label() -> None:
    block = measure_text("Customer PD", THEME, 1.0, eyebrow="MODEL A", subtitle="x")
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
    size = text_size("Model", THEME.label_size, THEME.label_weight, "DejaVu Sans", 2.0)
    assert size == (block.width, block.height)


def test_text_size_checks_the_font() -> None:
    with pytest.raises(ValueError, match="'No Such Sans' is not installed"):
        text_size("Model", 11, "normal", "No Such Sans", 1.0)
