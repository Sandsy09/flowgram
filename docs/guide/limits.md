# Known limits in 0.1

- **Edges do not avoid boxes.** An edge between two boxes takes the direct
  straight or elbow route, even when a third box is in the way. The box hides
  the part of the line that crosses it. Rearrange the layout, or set `exit`,
  `entry` and `routing` to send the edge another way.
- **Edges on one side of a box share one anchor**, at the middle of that side.
  Several edges leaving the same side start from the same point and overlap
  until they turn, and their labels can land on the shared part. Give one of
  them another side with `exit` or `entry`.
- **Edges are straight lines or elbows.** There are no curved edges.
- **Text does not wrap.** Put `\n` in a label or subtitle where a line should
  break.
- **Font sizes do not follow `scale`.** They are in points, so a larger scale
  gives more room around the same text.
- **Containers draw nothing.** Rows and columns have no fill, border or title,
  so there are no group panels yet.
- **Boxes are rectangles,** with rounded or square corners. There are no other
  shapes or legends.

The [roadmap](../design/roadmap.md) plans group panels and grids for 0.2, more
shapes and legends for 0.3, and better edges for 0.4.
