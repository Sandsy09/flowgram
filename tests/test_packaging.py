"""Tests that the package metadata stays in step with the code and CI."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]


def _classified_pythons() -> list[str]:
    prefix = "Programming Language :: Python :: 3."
    return [
        f"3.{c.removeprefix(prefix)}"
        for c in PROJECT["classifiers"]
        if c.startswith(prefix)
    ]


def test_python_classifiers_match_the_ci_matrix() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(r"python-version: \[([^\]]*)\]", ci)
    assert match
    tested = re.findall(r'"(3\.\d+)"', match[1])
    assert _classified_pythons() == tested


def test_oldest_classified_python_is_the_minimum() -> None:
    minimum = PROJECT["requires-python"].removeprefix(">=")
    assert _classified_pythons()[0] == minimum


def test_package_is_marked_typed() -> None:
    assert "Typing :: Typed" in PROJECT["classifiers"]
    assert (ROOT / "src" / "flowgram" / "py.typed").is_file()


def test_yaml_extra_matches_the_test_dependency() -> None:
    (extra,) = PROJECT["optional-dependencies"]["yaml"]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert extra in pyproject["dependency-groups"]["test"]


def test_urls_point_at_this_project() -> None:
    urls = PROJECT["urls"]
    assert {"Documentation", "Repository", "Issues", "Changelog"} <= set(urls)
    for url in urls.values():
        assert url.startswith("https://")
        assert "sandsy09" in url.lower()
    assert (ROOT / "CHANGELOG.md").is_file()
