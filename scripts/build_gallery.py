"""Write the gallery's images and notebook from the example scripts.

Each gallery example in ``examples/`` becomes an SVG in ``docs/gallery/``,
for the README and the docs, and a section of ``examples/gallery.ipynb``. The
SVGs draw their text as paths, so they look the same on any machine. The
notebook is written with its outputs cleared. Run ``uv run poe gallery``
after changing an example, and commit what it writes.
"""

from __future__ import annotations

import ast
import json
import runpy
from pathlib import Path

from flowgram import Diagram

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
IMAGES = ROOT / "docs" / "gallery"
NOTEBOOK = EXAMPLES / "gallery.ipynb"

GALLERY = ("linear_pipeline", "branching_flow", "nested_layout")
"""The gallery's examples, in the order they are shown."""


def load(name: str) -> Diagram:
    """Run an example script and return the ``spec`` it builds."""
    spec = runpy.run_path(str(EXAMPLES / f"{name}.py"))["spec"]
    if not isinstance(spec, Diagram):
        msg = f"examples/{name}.py must set spec to a Diagram"
        raise TypeError(msg)
    return spec


def svg(name: str) -> str:
    """Return the gallery SVG for an example, with its text as paths.

    Trailing spaces are cut from each line, as the repository's whitespace
    hook would. They only separate path coordinates, as the newline does.
    """
    text = load(name).to_svg(embed_fonts=True)
    return "".join(line.rstrip() + "\n" for line in text.splitlines())


def parts(name: str) -> tuple[str, str]:
    """Split an example into its docstring and the code that builds the spec.

    The code leaves out the ``if __name__ == "__main__":`` block, which would
    write a file when run in a notebook.
    """
    source = (EXAMPLES / f"{name}.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    first, *_ = tree.body
    lines = source.splitlines()
    end = next(
        (node.lineno - 1 for node in tree.body if isinstance(node, ast.If)),
        len(lines),
    )
    code = "\n".join(lines[first.end_lineno or 0 : end]).strip()
    return docstring, code


def _cell(kind: str, cell_id: str, text: str) -> dict[str, object]:
    cell: dict[str, object] = {
        "cell_type": kind,
        "id": cell_id,
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }
    if kind == "code":
        cell |= {"execution_count": None, "outputs": []}
    return cell


def notebook() -> str:
    """Return the gallery notebook as JSON, with no outputs."""
    cells = [
        _cell(
            "markdown",
            "intro",
            "# flowgram gallery\n\nEach cell builds a diagram and shows it. "
            "The same code is in the matching script in this folder.",
        )
    ]
    for name in GALLERY:
        docstring, code = parts(name)
        title, _, body = docstring.partition("\n")
        text = f"## {title}\n{body}".rstrip()
        cells.append(_cell("markdown", f"{name}-text", text))
        cells.append(_cell("code", f"{name}-code", f"{code}\n\nspec"))
    document = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


def main() -> None:
    """Write every gallery SVG and the notebook."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    for name in GALLERY:
        (IMAGES / f"{name}.svg").write_text(svg(name), encoding="utf-8", newline="\n")
    NOTEBOOK.write_text(notebook(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
