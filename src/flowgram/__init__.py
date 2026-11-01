"""Reusable components, modular diagram builder."""

from importlib.metadata import PackageNotFoundError, version

from flowgram.components import Box, Column, Edge, Row, Side, Spacer
from flowgram.diagram import Diagram
from flowgram.theme import RoleStyle, Theme

try:
    __version__ = version("flowgram")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "Box",
    "Column",
    "Diagram",
    "Edge",
    "RoleStyle",
    "Row",
    "Side",
    "Spacer",
    "Theme",
    "__version__",
]
