"""Write the files for checking flowgram exports in PowerPoint by hand.

Run ``uv run poe powerpoint:pack``. It writes ``build/powerpoint-check/``,
which git ignores: each example as a default SVG, an SVG with its text as
paths, a PDF and a 300 dpi PNG, all sized to fit a 16:9 slide, plus
``CHECKLIST.md`` with what to look at. Copy the folder to each machine that
takes part in the check.
"""

from __future__ import annotations

import runpy
from pathlib import Path

from flowgram import Diagram

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "powerpoint-check"
EXAMPLES = ("card_flow", "branching_flow")
"""The text-heaviest examples: left-aligned cards, and labelled edges."""
SLIDE_WIDTH = 12.0
"""Inches a diagram fills on a 13.33-inch-wide 16:9 slide."""

CHECKLIST = """\
# PowerPoint export check

Files, for each example:

- `<name>.svg`: text kept as text, naming DejaVu Sans, then Verdana, then sans-serif.
- `<name>-paths.svg`: the same, saved with `embed_fonts=True`, so text is shapes.
- `<name>.pdf`: fonts embedded.
- `<name>.png`: 300 dpi.

All are {width:g} inches wide, to sit on a 16:9 slide with a margin.

On Windows and on macOS, in current PowerPoint, on a machine **without** DejaVu
Sans installed (check Font Book or Settings > Fonts), insert each file with
Insert > Pictures and note:

1. Default SVG: which font is the text shown in? Does it stay inside its boxes?
   After "Convert to Shape", is the text editable, and in which font?
2. Paths SVG: does it look the same as the PNG? Is it sharp when zoomed in?
3. PDF: can it be inserted as a picture? Does it look like the PNG?
4. PNG: inserted at its own size, is it {width:g} inches wide? Is it sharp in
   Slide Show on the presenting screen?

Record the answers on issue #85.
"""


def fit_width(spec: Diagram, inches: float) -> Diagram:
    """Return the spec with its scale set so the figure is about ``inches`` wide."""
    # Width is spacing, which grows with scale, plus text, which does not.
    # Two renders find both parts, then one step lands on the target.
    first = spec.scale
    width_1 = spec.render().get_size_inches()[0]
    second = first * inches / width_1
    spec = spec.model_copy(update={"scale": second})
    width_2 = spec.render().get_size_inches()[0]
    if width_2 != width_1:
        slope = (width_2 - width_1) / (second - first)
        spec = spec.model_copy(update={"scale": second + (inches - width_2) / slope})
    return spec


def main() -> None:
    """Write every check file and the checklist."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name in EXAMPLES:
        spec = runpy.run_path(str(ROOT / "examples" / f"{name}.py"))["spec"]
        if not isinstance(spec, Diagram):
            msg = f"examples/{name}.py must set spec to a Diagram"
            raise TypeError(msg)
        slide = fit_width(spec, SLIDE_WIDTH)
        slide.save(OUT / f"{name}.svg")
        slide.save(OUT / f"{name}-paths.svg", embed_fonts=True)
        slide.save(OUT / f"{name}.pdf")
        slide.save(OUT / f"{name}.png")
    checklist = CHECKLIST.format(width=SLIDE_WIDTH)
    (OUT / "CHECKLIST.md").write_text(checklist, encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
