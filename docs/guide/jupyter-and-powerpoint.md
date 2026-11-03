# Jupyter and PowerPoint

## In Jupyter

Put a diagram last in a cell and it shows itself:

```python
from flowgram import Box, Diagram, Edge, Row

spec = Diagram(
    title="Shown in a notebook",
    root=Row(children=[Box(id="a", label="Spec"), Box(id="b", label="Picture")]),
    edges=[Edge(src="a", dst="b")],
)
spec
```

By default the notebook shows a PNG. It is drawn at twice the size it is shown,
so it stays sharp on high-resolution screens, and it is shown at the size
matplotlib's inline plots use. Set `display_format="svg"` on the diagram to show
an SVG instead:

```python
spec = spec.model_copy(update={"display_format": "svg"})
```

`display_format` only changes what the notebook shows; files from `save` are not
affected. PNG is the default because notebook front ends, and pasting from them
into slides, handle it most reliably. SVG keeps text sharp at any zoom.

## Into PowerPoint

Save a file and insert it with **Insert > Pictures**:

- **PNG** works everywhere. The default 300 dpi is sharp on a full-width
  16:9 slide, even on a 4K screen. Use `dpi=600` if the slide will be printed
  large.
- **SVG** stays sharp at any size. Recent versions of PowerPoint can insert SVG
  and convert it to editable shapes. SVG text names the theme's font, so on a
  machine without DejaVu Sans PowerPoint substitutes another font, which can be
  wider than the box. Save with `embed_fonts=True` to draw the text as shapes
  instead, at the cost of editable text.
- **PDF** keeps its fonts but is harder to place on a slide than an image.

```python
spec.save("slide.png", transparent=True)  # sits on a coloured slide background
spec.save("slide.svg", embed_fonts=True)
```

How SVG behaves in PowerPoint is still being checked by hand
([#85](https://github.com/Sandsy09/flowgram/issues/85)). Until then, PNG is the
safe choice.

## Sizing for a 16:9 slide

A widescreen slide is 13.33 by 7.5 inches. Text sizes in the theme are in points,
so the diagram's text matches the slide's own text only when the picture is shown
at the figure's size. Choose `scale` so the figure fits the slide, rather than
stretching the picture afterwards:

```python
def fit_width(spec: Diagram, inches: float) -> Diagram:
    """Return the spec with its scale set so the figure is about ``inches`` wide."""
    for _ in range(2):  # text does not scale, so a second pass gets closer
        width, _ = spec.render().get_size_inches()
        spec = spec.model_copy(update={"scale": spec.scale * inches / width})
    return spec


slide = fit_width(spec, 12)  # leave about two-thirds of an inch each side
width, height = slide.render().get_size_inches()
```

Scaling only changes the space between and around the text; text that is too big
for the slide needs smaller font sizes in the theme. When you insert the picture,
check in **Format Picture > Size** that it is shown at the figure's width.
