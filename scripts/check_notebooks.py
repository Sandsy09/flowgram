"""Validate tracked notebook sources without rewriting them."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError
from nbformat.notebooknode import NotebookNode

_CELL_TIMEOUT_SECONDS = 300
_PRUNED_DIRECTORY_NAMES = {".git", ".ipynb_checkpoints", ".venv"}
_ROOT_WORKING_TREES = {
    PurePosixPath("artifacts"),
    PurePosixPath("data/interim"),
    PurePosixPath("data/processed"),
    PurePosixPath("data/raw"),
    PurePosixPath("models"),
}
_SAFE_EXCEPTION_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MESSAGES = {
    "cell-execution-failed": "Notebook cell execution failed.",
    "cell-execution-timeout": "Notebook cell exceeded the 300-second timeout.",
    "cell-output-present": "Code cell has stored output.",
    "execution-count-present": "Code cell has a stored execution count.",
    "invalid-notebook-json": "Notebook is not valid JSON.",
    "invalid-notebook-schema": "Notebook does not satisfy its declared schema.",
    "kernel-unavailable": "The project Python kernel could not be started.",
    "temporary-copy-failed": "Temporary notebook copy or cleanup failed.",
    "unreadable-notebook": "Notebook could not be read as UTF-8.",
    "widget-state-present": "Notebook has stored widget state.",
}


@dataclass(frozen=True)
class Failure:
    """One deterministic, safe notebook-validation failure."""

    path: str
    code: str
    cell_index: int | None = None
    exception_type: str | None = None

    def sort_key(self) -> tuple[str, int, int, str]:
        """Return the canonical path/cell/code ordering key."""
        absent = 0 if self.cell_index is None else 1
        index = -1 if self.cell_index is None else self.cell_index
        return (self.path, absent, index, self.code)

    def render(self) -> str:
        """Render one line without unsafe exception or filesystem detail."""
        location = _escape_control_characters(self.path)
        if self.cell_index is not None:
            location = f"{location}:cell {self.cell_index}"
        message = _MESSAGES[self.code]
        if self.exception_type is not None:
            exception_type = _safe_exception_type(self.exception_type)
            message = f"{message} Exception type: {exception_type}."
        return f"{location}: {self.code}: {message}"


def _escape_control_characters(value: str) -> str:
    """Escape control characters so one failure always occupies one line."""
    return "".join(
        character if character.isprintable() else f"\\u{ord(character):04x}"
        for character in value
    )


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_notebooks(root: Path) -> tuple[Path, ...]:
    """Return every in-scope notebook in project-relative lexical order."""
    notebooks: list[Path] = []
    for directory, child_directories, filenames in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(directory)
        current_relative = PurePosixPath(_relative_posix(current, root))
        if current_relative == PurePosixPath("."):
            current_relative = PurePosixPath()

        retained: list[str] = []
        for child in sorted(child_directories):
            relative = current_relative / child
            if child in _PRUNED_DIRECTORY_NAMES or relative in _ROOT_WORKING_TREES:
                continue
            retained.append(child)
        child_directories[:] = retained

        notebooks.extend(
            current / filename
            for filename in sorted(filenames)
            if filename.endswith(".ipynb")
        )

    return tuple(sorted(notebooks, key=lambda path: _relative_posix(path, root)))


def _parse_notebook(
    path: Path, relative: str
) -> tuple[NotebookNode | None, Failure | None]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, Failure(relative, "unreadable-notebook")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return None, Failure(relative, "unreadable-notebook")

    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        return None, Failure(relative, "invalid-notebook-json")

    try:
        if not isinstance(payload, dict):
            raise TypeError
        notebook = nbformat.reads(  # type: ignore[no-untyped-call]
            text, as_version=nbformat.NO_CONVERT
        )
        nbformat.validate(notebook)
    except Exception:  # nbformat wraps multiple schema-validator exception types.
        return None, Failure(relative, "invalid-notebook-schema")
    return notebook, None


def _cleanliness_failures(notebook: NotebookNode, relative: str) -> list[Failure]:
    failures: list[Failure] = []
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        if cell.execution_count is not None:
            failures.append(Failure(relative, "execution-count-present", index))
        if cell.outputs:
            failures.append(Failure(relative, "cell-output-present", index))
    if "widgets" in notebook.metadata:
        failures.append(Failure(relative, "widget-state-present"))
    return failures


def _safe_exception_type(value: str | None) -> str:
    if value is not None and _SAFE_EXCEPTION_TYPE.fullmatch(value):
        return value
    return "Exception"


def _execute_copy(copy: Path, tracked: Path, relative: str) -> Failure | None:
    notebook, failure = _parse_notebook(copy, relative)
    if failure is not None or notebook is None:
        return Failure(relative, "temporary-copy-failed")

    active_cell: int | None = None

    def record_cell_start(*, cell: NotebookNode, cell_index: int) -> None:
        del cell
        nonlocal active_cell
        active_cell = cell_index

    client = NotebookClient(
        notebook,
        timeout=_CELL_TIMEOUT_SECONDS,
        kernel_name="python3",
        allow_errors=False,
        resources={"metadata": {"path": str(tracked.parent)}},
        on_cell_start=record_cell_start,
    )
    try:
        client.execute(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except CellTimeoutError:
        return Failure(relative, "cell-execution-timeout", active_cell)
    except CellExecutionError as error:
        return Failure(
            relative,
            "cell-execution-failed",
            active_cell,
            _safe_exception_type(getattr(error, "ename", None)),
        )
    except Exception as error:
        if active_cell is None:
            return Failure(relative, "kernel-unavailable")
        return Failure(
            relative,
            "cell-execution-failed",
            active_cell,
            _safe_exception_type(type(error).__name__),
        )
    return None


def validate_notebooks(root: Path) -> tuple[Failure, ...]:
    """Validate notebooks beneath ``root`` and return ordered failures."""
    notebooks = discover_notebooks(root)
    if not notebooks:
        return ()

    structural: list[Failure] = []
    for notebook_path in notebooks:
        relative = _relative_posix(notebook_path, root)
        notebook, failure = _parse_notebook(notebook_path, relative)
        if failure is not None:
            structural.append(failure)
        elif notebook is not None:
            structural.extend(_cleanliness_failures(notebook, relative))

    if structural:
        return tuple(sorted(structural, key=Failure.sort_key))

    current_relative = _relative_posix(notebooks[0], root)
    failures: list[Failure] = []
    try:
        with tempfile.TemporaryDirectory(prefix="forge-notebooks-") as temporary:
            temporary_root = Path(temporary).resolve()
            if temporary_root.is_relative_to(root.resolve()):
                return (Failure(current_relative, "temporary-copy-failed"),)

            copies: dict[Path, Path] = {}
            for notebook_path in notebooks:
                current_relative = _relative_posix(notebook_path, root)
                copy = temporary_root / Path(current_relative)
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(notebook_path, copy)
                copies[notebook_path] = copy

            for notebook_path in notebooks:
                current_relative = _relative_posix(notebook_path, root)
                failure = _execute_copy(
                    copies[notebook_path], notebook_path, current_relative
                )
                if failure is not None:
                    failures.append(failure)
                    break
    except OSError:
        failures.append(Failure(current_relative, "temporary-copy-failed"))

    return tuple(sorted(failures, key=Failure.sort_key))


def main() -> int:
    """Run the fixed project-root validation and return a process status."""
    failures = validate_notebooks(Path.cwd())
    if not failures:
        return 0
    for failure in failures:
        print(failure.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
