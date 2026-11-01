"""Tests for themes and role styles."""

from typing import Any

import pytest
from pydantic import ValidationError

from flowgram import RoleStyle, Theme


def _role() -> RoleStyle:
    return RoleStyle(fill="#FFFFFF", stroke="#000000", text="#111111")


def _theme(**fields: Any) -> Theme:
    return Theme.model_validate({"roles": {"default": _role()}, **fields})


@pytest.mark.parametrize("theme", [Theme.light(), Theme.mono()])
def test_presets_define_the_standard_roles(theme: Theme) -> None:
    assert {"default", "accent", "muted", "positive", "negative"} <= set(theme.roles)


def test_presets_have_distinct_names() -> None:
    assert Theme.light().name == "light"
    assert Theme.mono().name == "mono"


def test_default_background_is_transparent() -> None:
    assert Theme.light().background is None


def test_custom_theme_needs_only_a_default_role() -> None:
    theme = Theme(roles={"default": _role()})
    assert theme.name == "custom"
    assert theme.font_family == "DejaVu Sans"


def test_theme_without_default_role_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must define a 'default' role"):
        Theme(name="broken", roles={"accent": _role()})


def test_theme_with_no_roles_is_rejected() -> None:
    with pytest.raises(ValidationError, match="no roles"):
        Theme(roles={})


def test_role_with_bad_colour_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not a colour matplotlib understands"):
        RoleStyle(fill="not-a-colour", stroke="#000000", text="#111111")


def test_named_colours_are_accepted() -> None:
    assert RoleStyle(fill="tab:blue", stroke="black", text="white").fill == "tab:blue"


@pytest.mark.parametrize(
    "field", ["title_size", "label_size", "line_width", "min_box_width", "arrow_size"]
)
def test_positive_fields_reject_zero_and_negative(field: str) -> None:
    for bad in (0, -1):
        with pytest.raises(ValidationError):
            _theme(**{field: bad})


@pytest.mark.parametrize("field", ["gap", "text_padding", "corner_radius"])
def test_non_negative_fields_allow_zero_but_not_negative(field: str) -> None:
    assert getattr(_theme(**{field: 0}), field) == 0
    with pytest.raises(ValidationError):
        _theme(**{field: -0.1})


def test_non_finite_numbers_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _theme(gap=float("inf"))


def test_theme_is_frozen() -> None:
    theme = Theme.light()
    with pytest.raises(ValidationError):
        theme.gap = 2.0


def test_unknown_theme_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _theme(gapp=2.0)


def test_model_copy_builds_a_variant() -> None:
    wide = Theme.light().model_copy(update={"gap": 3.0})
    assert wide.gap == 3.0
    assert Theme.light().gap == 1.0
