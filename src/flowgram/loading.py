"""Load a diagram spec from a dict, JSON or YAML, and write one back out.

Each format has its own function, and file variants read UTF-8 text from a
path. Nothing is guessed from a file's extension. Every component in the
data names its ``kind``, such as ``"row"``, ``"column"``, ``"box"`` or
``"spacer"``, and loading runs the same checks as building the spec in
Python, so a bad spec reports every problem at once.

The ``to_*`` functions write a spec back out with only what differs from
the defaults, so a written spec is short and loads back equal. Each
component keeps its ``kind``, and the theme is left out when it is the
default light theme.

YAML needs PyYAML, which comes with the ``yaml`` extra:
``pip install "flowgram[yaml]"``. It is imported only when YAML is read or
written.
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


def _yaml(action: str = "loading") -> ModuleType:
    try:
        import yaml  # Optional extra, so imported on use.
    except ImportError as error:
        msg = f"{action} YAML needs PyYAML; install it with {YAML_EXTRA_HINT}"
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


def to_dict(diagram: Diagram) -> dict[str, Any]:
    """Return a diagram's spec as plain data, without its defaults.

    Only fields that differ from their defaults are kept, except that every
    component keeps its ``kind``, so the data loads back with ``from_dict``.
    A theme other than the default keeps its name and roles, so it loads on
    its own. Values are JSON types: lists, strings, numbers, booleans and
    ``None``.

    Args:
        diagram: The diagram to write.

    Returns:
        The spec as nested dicts and lists.
    """
    return diagram.model_dump(mode="json", exclude_defaults=True)


def to_json(diagram: Diagram, *, indent: int | None = 2) -> str:
    """Return a diagram's spec as a JSON document, without its defaults.

    Args:
        diagram: The diagram to write.
        indent: Spaces per level, or ``None`` for one compact line.

    Returns:
        The JSON text, as ``to_dict`` gives the data.
    """
    return diagram.model_dump_json(exclude_defaults=True, indent=indent)


def to_yaml(diagram: Diagram) -> str:
    """Return a diagram's spec as a YAML document, without its defaults.

    Keys keep the order of the spec's fields, with ``kind`` first. Text with
    line breaks is written as a ``|`` block, one line of YAML per line of
    text.

    Args:
        diagram: The diagram to write.

    Returns:
        The YAML text, as ``to_dict`` gives the data.

    Raises:
        ImportError: If PyYAML is not installed. The message names the
            command that installs it.
    """
    yaml = _yaml("writing")

    class Dumper(yaml.SafeDumper):  # type: ignore[name-defined,misc]
        """PyYAML's safe dumper, writing multi-line text as blocks."""

    def text_block(dumper: Any, value: str) -> Any:
        style = "|" if "\n" in value else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    Dumper.add_representer(str, text_block)
    text: str = yaml.dump(
        to_dict(diagram), Dumper=Dumper, sort_keys=False, allow_unicode=True
    )
    return text


def to_json_file(
    diagram: Diagram, path: str | os.PathLike[str], *, indent: int | None = 2
) -> None:
    """Write a diagram's spec to a JSON file, without its defaults.

    Args:
        diagram: The diagram to write.
        path: The file to write, as UTF-8. An existing file is replaced.
        indent: Spaces per level, or ``None`` for one compact line.

    Raises:
        OSError: If the file cannot be written.
    """
    text = to_json(diagram, indent=indent) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def to_yaml_file(diagram: Diagram, path: str | os.PathLike[str]) -> None:
    """Write a diagram's spec to a YAML file, without its defaults.

    Args:
        diagram: The diagram to write.
        path: The file to write, as UTF-8. An existing file is replaced.

    Raises:
        ImportError: If PyYAML is not installed.
        OSError: If the file cannot be written.
    """
    text = to_yaml(diagram)
    Path(path).write_text(text, encoding="utf-8", newline="\n")
