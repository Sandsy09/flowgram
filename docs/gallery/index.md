# Gallery

Three diagrams, each built by a short script in
[`examples/`](https://github.com/Sandsy09/flowgram/tree/main/examples). Run a script
to write its diagram as a PNG next to it, or open `examples/gallery.ipynb` to build
them all in Jupyter.

## Linear pipeline

![Five steps in a row, each feeding the next](linear_pipeline.svg)

<!-- fmt: off -->
```python
--8<-- "examples/linear_pipeline.py"
```
<!-- fmt: on -->

## Branching model flow

![Two models fork from shared features and meet again](branching_flow.svg)

<!-- fmt: off -->
```python
--8<-- "examples/branching_flow.py"
```
<!-- fmt: on -->

## Nested layout

![Service columns in a row, under a gateway and two clients](nested_layout.svg)

<!-- fmt: off -->
```python
--8<-- "examples/nested_layout.py"
```
<!-- fmt: on -->

The images are written by `uv run poe gallery`, with their text drawn as shapes so
they look the same in any browser.
