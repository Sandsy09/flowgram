# Export

## Saving files

`save` writes PNG, SVG or PDF, chosen by the file's extension:

```python
from flowgram import Box, Diagram, Edge, Row

spec = Diagram(
    title="Export",
    root=Row(children=[Box(id="a", label="Spec"), Box(id="b", label="File")]),
    edges=[Edge(src="a", dst="b")],
)

spec.save("diagram.png")  # 300 dpi
spec.save("diagram.svg")
spec.save("diagram.pdf")
```

| Option | What it does |
| --- | --- |
| `dpi` | Pixels per inch for PNG. The default, 300, is sharp on a full-width slide and in print. SVG and PDF ignore it. |
| `transparent` | Leaves out the background, so only the diagram is drawn. |
| `embed_fonts` | Draws SVG text as shapes. It looks the same on every machine, but can no longer be edited as text. |

The page is the whole figure, nothing cropped: the content, `Diagram.padding`,
and the title and footnote. Its size in inches is the layout's size in units
times `Diagram.scale`.

SVG text is kept as text by default, so you can edit it in a vector editor or
slide software. The file names the theme's font and then its
`font_fallbacks`: `'DejaVu Sans', 'Verdana', sans-serif` by default. A viewer
without DejaVu Sans uses the first font in the list it has. Verdana comes with
Windows and macOS and sets text within about 2% of DejaVu Sans's width, so
labels still fit their boxes. Browsers and PowerPoint for the web follow the
list. Whether text stays editable after PowerPoint's **Convert to Shape**, which
only the desktop app has, is still to be checked
([#98](https://github.com/Sandsy09/flowgram/issues/98)).
PDF always embeds its fonts, so it looks the same everywhere.

| Font | Width of the same text, against DejaVu Sans |
| --- | --- |
| Verdana | 98.5% to 100.7% |
| Arial | 83% to 92% |
| Segoe UI | 80% to 90% |
| Calibri | 72% to 82% |

Every common font other than Verdana is narrower, so a substitute leaves more
room inside the boxes rather than spilling out of them. With your own
`font_family`, set `font_fallbacks` to fonts close to it.

## Identical files

Saving the same spec twice writes the same bytes, in any process. The files
carry no dates or version numbers; their metadata names only flowgram. A
matplotlib or FreeType upgrade can still change the output.

Your own matplotlib settings do not change the file. flowgram applies its own
settings while it draws and saves.

## Bytes and figures

To get the file's contents without writing a file:

```python
png = spec.to_png(dpi=150)
svg = spec.to_svg()
```

`render()` returns a matplotlib `Figure` to save or change yourself. `draw(ax)`
draws into an `Axes` you already have, such as one panel of a larger figure. It
does not resize the figure, and font sizes stay in points, so text fits its
boxes exactly only when the axes is `scale` inches per unit. The theme's
background is not drawn there.

```python
from matplotlib.figure import Figure

figure = Figure(figsize=(8, 3))
left, right = figure.subplots(1, 2)
spec.draw(left)
right.plot([1, 2, 3])
```
