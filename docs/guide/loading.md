# Loading specs

A spec can live in a JSON or YAML file instead of Python code. Loading runs the
same checks as building the spec in Python, so a bad file reports every problem
at once.

## The format

The data mirrors the Python classes. Every component names its `kind`:
`"row"`, `"column"`, `"box"` or `"spacer"`. Fields you leave out take their
defaults. Edges need no `kind`.

```python
from pathlib import Path

Path("pipeline.yaml").write_text(
    """\
title: Model training pipeline
root:
  kind: row
  gap: 2
  children:
    - {kind: box, id: data, label: Raw data, role: muted}
    - kind: column
      children:
        - {kind: box, id: clean, label: Clean, subtitle: "impute, clip"}
        - {kind: box, id: feats, label: Features}
    - {kind: box, id: model, label: Model, role: accent}
edges:
  - {src: data, dst: clean}
  - {src: data, dst: feats}
  - {src: clean, dst: model, label: train}
  - {src: feats, dst: model, style: dashed}
""",
    encoding="utf-8",
)
```

## Loaders

Each format has its own function, and nothing is guessed from a file's
extension:

```python
from flowgram import Diagram

spec = Diagram.from_yaml_file("pipeline.yaml")
same = Diagram.from_yaml(Path("pipeline.yaml").read_text(encoding="utf-8"))
also = Diagram.from_dict(
    {"root": {"kind": "row", "children": [{"kind": "box", "label": "A"}]}}
)
```

| Loader | Reads |
| --- | --- |
| `from_dict(data)` | Nested dicts and lists, as `to_dict()` gives |
| `from_json(text)`, `from_json_file(path)` | A JSON document |
| `from_yaml(text)`, `from_yaml_file(path)` | A YAML document |

Files are read as UTF-8.

## YAML

YAML needs PyYAML, from the `yaml` extra:

```bash
pip install "flowgram[yaml]"
```

PyYAML is only imported when you read or write YAML. Without it, the error names
the command above. Files are read with PyYAML's safe loader, so a spec file
cannot run code.

## Writing specs out

Each loader has a matching writer. It writes only what differs from the
defaults, so a spec built in Python can be saved as a short, readable file, and
it loads back equal:

```python
text = spec.to_yaml()
assert Diagram.from_yaml(text) == spec

spec.to_json_file("pipeline.json")
spec.to_yaml_file("pipeline.yaml")
data = spec.to_dict()
```

| Writer | Writes |
| --- | --- |
| `to_dict()` | Nested dicts and lists of JSON types |
| `to_json(indent=2)`, `to_json_file(path)` | A JSON document; `indent=None` gives one line |
| `to_yaml()`, `to_yaml_file(path)` | A YAML document; needs the `yaml` extra |

- Every component keeps its `kind`, even though it is a default, because loading
  needs it.
- The theme is left out when it is the default light theme. A changed theme
  keeps its name and roles, so the file loads without the Python code that made
  it, plus the fields you changed.
- YAML keeps the order of the fields, with `kind` first, and writes text with
  line breaks as a `|` block.
- Files are written as UTF-8 and end with a newline.

`spec.model_dump_json()` still works and writes every field, defaults included.
`model_dump(exclude_defaults=True)` keeps `kind` too, so its output also loads.
