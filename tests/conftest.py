"""Shared test fixtures: image snapshot comparison.

Snapshot tests are marked ``snapshot`` and are opt-in: the default test run
deselects them, and ``uv run poe test:snapshots`` runs them. They only run on
Linux, because baselines are rendered there with the bundled DejaVu Sans and
other platforms rasterise text slightly differently.

Set ``FLOWGRAM_UPDATE_SNAPSHOTS=1`` (or run ``uv run poe snapshots:update``)
to write the current images as the new baselines instead of comparing.
"""

import os
import platform
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from matplotlib.figure import Figure
from matplotlib.testing.compare import compare_images

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
"""Where baseline images are stored, one PNG per snapshot name."""

FAILURE_DIR = Path(
    os.environ.get("FLOWGRAM_SNAPSHOT_FAILURES", "build/snapshot-failures")
)
"""Where expected, actual and diff images go when a comparison fails."""

SNAPSHOT_DPI = 100
"""Resolution of every snapshot, fixed so baselines stay comparable."""

SnapshotCheck = Callable[[Figure, str], None]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip snapshot tests off Linux, with a reason that says why.

    ``FLOWGRAM_SNAPSHOTS_ANY_OS=1`` runs them anyway, which is useful for
    checking the harness itself; expect differences against Linux baselines.
    """
    if platform.system() == "Linux" or os.environ.get("FLOWGRAM_SNAPSHOTS_ANY_OS"):
        return
    skip = pytest.mark.skip(
        reason="snapshot baselines are rendered on Linux; text rasterises "
        "differently on other platforms"
    )
    for item in items:
        if "snapshot" in item.keywords:
            item.add_marker(skip)


def _save(figure: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # No Software key, so the PNG bytes do not depend on the matplotlib version.
    figure.savefig(path, format="png", dpi=SNAPSHOT_DPI, metadata={"Software": None})


def _fail(name: str, actual: Path, expected: Path | None, message: str) -> None:
    out = FAILURE_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(actual, out / "actual.png")
    if expected is not None:
        shutil.copy(expected, out / "expected.png")
        diff = actual.with_name(f"{actual.stem}-failed-diff.png")
        if diff.exists():
            shutil.copy(diff, out / "diff.png")
    pytest.fail(f"{message}; images written to {out}", pytrace=False)


@pytest.fixture
def snapshot(tmp_path: Path) -> SnapshotCheck:
    """Compare a figure with its stored baseline image.

    Call the fixture with a figure and a snapshot name. The name becomes the
    baseline file ``tests/snapshots/<name>.png``.

    Returns:
        A function that saves the figure, compares it with the baseline and
        fails the test, writing expected, actual and diff images, if they
        differ or the baseline is missing.
    """
    update = os.environ.get("FLOWGRAM_UPDATE_SNAPSHOTS") == "1"

    def check(figure: Figure, name: str) -> None:
        baseline = SNAPSHOT_DIR / f"{name}.png"
        if update:
            _save(figure, baseline)
            return
        actual = tmp_path / f"{name}.png"
        _save(figure, actual)
        if not baseline.exists():
            _fail(
                name,
                actual,
                None,
                f"no baseline for snapshot {name!r}; run `uv run poe snapshots:update` "
                "on Linux, or take actual.png from the CI artifact",
            )
        result = compare_images(str(baseline), str(actual), tol=0, in_decorator=True)
        if result is not None:
            _fail(
                name,
                actual,
                baseline,
                f"snapshot {name!r} differs from its baseline "
                f"(RMS {result['rms']:.3f})",
            )

    return check
