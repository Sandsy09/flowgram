"""Two linked groups of cards over a row of action cards.

This is the milestone 4 API check (#20): a presentation slide with eyebrow,
title and body text on left-aligned cards, rebuilt from a reference slide
with neutral text. The spec is 33 lines written one box or edge per line;
formatting at 88 columns spreads it further. Run this file to write
``card_flow.png`` next to it.

Body text is muted under a dark title with a role ``subtitle`` colour. Not
covered yet, and tracked as issues: text at the top of tall cards with looser
spacing (#66), a separately styled diagram subtitle (#67), a footnote (#68),
group panels with badges, headings and captions (#32), and shadows (#69).
"""

from pathlib import Path

from flowgram import Box, Column, Diagram, Edge, RoleStyle, Row, Spacer, Theme

INK, MUTED, BLUE, GREEN = "#0F172A", "#475569", "#2563EB", "#16A34A"
theme = Theme.light().model_copy(
    update={
        "background": "#F8FAFC",
        "title_size": 22,
        "label_size": 14,
        "eyebrow_size": 8.5,
        "text_align": "left",
        "line_width": 1.0,
        "roles": {
            "default": RoleStyle(
                fill="#F1F5F9", stroke="#E2E8F0", text=INK, subtitle=MUTED
            ),
            "health": RoleStyle(
                fill="#FFFFFF", stroke="#BFDBFE", text=INK, eyebrow=BLUE, subtitle=MUTED
            ),
            "repair": RoleStyle(
                fill="#FFFFFF",
                stroke="#BBF7D0",
                text=INK,
                eyebrow=GREEN,
                subtitle=MUTED,
            ),
        },
    }
)


def card(box_id: str, role: str, eyebrow: str, label: str, body: str) -> Box:
    """Return a card with an eyebrow, a title and a body."""
    return Box(id=box_id, role=role, eyebrow=eyebrow, label=label, subtitle=body)


def action(box_id: str, label: str, body: str) -> Box:
    """Return a short action card with a title and a body."""
    return Box(id=box_id, label=label, subtitle=body, height=0.9)


spec = Diagram(
    title="Two models, one maintenance plan",
    subtitle="Score each machine, then judge each repair before it is scheduled",
    theme=theme,
    root=Column(
        gap=1.2,
        align="start",
        children=[
            Row(
                gap=0.6,
                uniform=True,
                children=[
                    card(
                        "h1",
                        "health",
                        "SENSOR READINGS",
                        "Machine history",
                        "Vibration, temperature,\nrun hours and\nservice records",
                    ),
                    card(
                        "h2",
                        "health",
                        "HEALTH OUTPUT",
                        "Health score",
                        "A measure of wear that\nsets the inspection\ninterval",
                    ),
                    Spacer(size=1.2),
                    card(
                        "r1",
                        "repair",
                        "PROPOSED REPAIR",
                        "Work order",
                        "Health score, parts,\nlabour, downtime\nand repair cost",
                    ),
                    card(
                        "r2",
                        "repair",
                        "REPAIR OUTPUT",
                        "Failure risk",
                        "The predicted chance\nthat the repair fails\nwithin a year",
                    ),
                ],
            ),
            Row(
                gap=0.6,
                children=[
                    action(
                        "a1",
                        "01  Approve repair",
                        "Approve if risk and budget allow\nOtherwise defer or escalate",
                    ),
                    action(
                        "a2",
                        "02  Keep the interval",
                        "The inspection interval does not\nshorten for a larger repair",
                    ),
                    action(
                        "a3",
                        "03  Schedule downtime",
                        "Plan the work at the agreed\ninterval, within crew limits",
                    ),
                ],
            ),
        ],
    ),
    edges=[
        Edge(src="h1", dst="h2", color=BLUE),
        Edge(src="h2", dst="r1", color=BLUE),
        Edge(src="r1", dst="r2", color=GREEN),
        Edge(src="a1", dst="a2", color=GREEN),
        Edge(src="a2", dst="a3", color=GREEN),
    ],
)

if __name__ == "__main__":
    spec.render().savefig(Path(__file__).with_suffix(".png"), dpi=150)
