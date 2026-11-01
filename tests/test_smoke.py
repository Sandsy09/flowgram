"""Smoke tests for flowgram."""

from flowgram import __version__


def test_version_is_available() -> None:
    assert __version__
