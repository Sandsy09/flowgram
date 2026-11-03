# Themes

A `Theme` holds the colours, fonts and spacing for a whole diagram. Boxes name a
**role** instead of a colour, so swapping the theme restyles everything.

## Presets and roles

`Theme.light()` is the default. `Theme.mono()` is greyscale, for black-and-white
printing. Both define these roles:

| Role | In the light theme |
| --- | --- |
| `default` | White box, dark outline |
| `accent` | Blue |
| `muted` | Pale grey with grey text |
| `positive` | Green |
| `negative` | Red |

A role is a `RoleStyle`: `fill`, `stroke` and `text` colours, plus optional
`eyebrow` and `subtitle` colours that otherwise follow `text`. Every theme must
define `default`. A box with a role the theme does not define is an error that
lists the roles it does define.

## Making your own

Start from a preset and change what you need:

```python
from flowgram import Box, Diagram, RoleStyle, Row, Shadow, Theme

theme = Theme.light().model_copy(
    update={
        "background": "#F8FAFC",
        "label_size": 13,
        "text_align": "left",
        "shadow": Shadow(dy=0.08, alpha=0.08),
        "roles": {
            **Theme.light().roles,
            "warning": RoleStyle(fill="#FEF3C7", stroke="#F59E0B", text="#78350F"),
        },
    }
)

spec = Diagram(theme=theme, root=Row(children=[Box(label="Check", role="warning")]))
```

The theme's fields fall into these groups. The [API reference](../reference.md#theme)
describes each one.

- **Type:** `font_family` and the `font_fallbacks` an SVG names after it, the
  sizes and weights of the title, label, subtitle,
  eyebrow, edge labels and footnote, plus `line_spacing` and `tier_gap`.
- **Text placement:** `text_align` (`"left"`, `"center"` or `"right"`),
  `text_valign` (`"center"` or `"top"`) and `title_align`.
- **Boxes:** `line_width`, `corner_radius`, `shadow`, `text_padding` and the
  minimum box size.
- **Spacing:** `gap`, the default space between children.
- **Edges:** `edge_color`, `edge_line_width` and `arrow_size`.
- **Figure:** `background`, or `None` for a transparent one.

## Per-box overrides

A box can override its role's look with `fill`, `stroke`, `text_color`,
`eyebrow_color`, `subtitle_color`, `line_width`, `corner_radius`, `text_align`,
`text_valign` and `shadow`. When several boxes share a look, a new role is
easier to keep consistent.

```python
alert = Box(label="Alert", fill="#DC2626", text_color="white", corner_radius=0)
```
