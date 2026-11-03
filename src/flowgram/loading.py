"""Load a diagram spec from a dict, JSON or YAML.

Each format has its own function, and file variants read UTF-8 text from a
path. Nothing is guessed from a file's extension. Every component in the
data names its ``kind``, such as ``"row"``, ``"column"``, ``"box"`` or
``"spacer"``, and loading runs the same checks as building the spec in
Python, so a bad spec reports every problem at once.

YAML needs PyYAML, which comes with the ``yaml`` extra:
``pip install "flowgram[yaml]"``. It is imported only when YAML is loaded.
"""

import os
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from flowgram.diagram import Diagram

YAML_EXTRA_HINT = 'pip install "flowgram[yaml]"'
"""The command that installs the YAML extra, named in the missing-extra error."""


def from_dict(data: Mapping[str, Any]) -> Diagram:
    """Build a diagram from plain Python data.

    Args:
        data: The spec as nested dicts and lists, as ``model_dump()`` gives.

    Returns:
        The checked diagram.

    Raises:
        pydantic.ValidationError: If the data is not a valid spec.
    """
    return Diagram.model_validate(data)


def from_json(text: str | bytes) -> Diagram:
    """Build a diagram from a JSON document.

    Args:
        text: The JSON text, as ``model_dump_json()`` gives.

    Returns:
        The checked diagram.

    Raises:
        pydantic.ValidationError: If the text is not valid JSON or not a
            valid spec.
    """
    return Diagram.model_validate_json(text)


def _yaml() -> ModuleType:
    try:
        import yaml  # Optional extra, so imported on use.
    except ImportError as error:
        msg = f"loading YAML needs PyYAML; install it with {YAML_EXTRA_HINT}"
        raise ImportError(msg) from error
    return yaml


def from_yaml(text: str) -> Diagram:
    """Build a diagram from a YAML document.

    The document is read with PyYAML's safe loader, so it cannot run code or
    build arbitrary Python objects.

    Args:
        text: The YAML text. Its top level is a mapping, like a JSON spec.

    Returns:
        The checked diagram.

    Raises:
        ImportError: If PyYAML is not installed. The message names the
            command that installs it.
        yaml.YAMLError: If the text is not valid YAML.
        pydantic.ValidationError: If the document is not a valid spec.
    """
    data = _yaml().safe_load(text)
    return Diagram.model_validate(data)


def from_json_file(path: str | os.PathLike[str]) -> Diagram:
    """Build a diagram from a JSON file.

    Args:
        path: The file to read, as UTF-8.

    Returns:
        The checked diagram.

    Raises:
        OSError: If the file cannot be read.
        pydantic.ValidationError: If the file is not a valid spec.
    """
    return from_json(Path(path).read_text(encoding="utf-8"))


def from_yaml_file(path: str | os.PathLike[str]) -> Diagram:
    """Build a diagram from a YAML file.

    Args:
        path: The file to read, as UTF-8.

    Returns:
        The checked diagram.

    Raises:
        ImportError: If PyYAML is not installed.
        OSError: If the file cannot be read.
        yaml.YAMLError: If the file is not valid YAML.
        pydantic.ValidationError: If the file is not a valid spec.
    """
    _yaml()
    return from_yaml(Path(path).read_text(encoding="utf-8"))
