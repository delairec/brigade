from html import escape

from brigade.dashboard.draw_step_path import StepFrame, draw_step_path

WIDTH = 400
ROLE_BASELINE = 12
CHART_TOP = 20
CHART_HEIGHT = 40
LABEL_LINE = 14
LABEL_DESCENT = 4
MARK_RADIUS = 3
LINE_TONE = "work"
DIRECTION_TONES = {"raised": "limit", "lowered": "done"}
FRAME = StepFrame(width=WIDTH, top=CHART_TOP, height=CHART_HEIGHT)


def _list_caps(budget: dict) -> tuple[int, ...]:
    if budget["stable"]:
        return (budget["applied"],)
    history = budget["history"]
    return (history[0]["before"], *(change["after"] for change in history))


def _draw_mark(change: dict, x: float, y: float) -> str:
    tone = DIRECTION_TONES[change["direction"]]
    return f'<circle class="cap-change tone-{tone}" cx="{x:g}" cy="{y:g}" r="{MARK_RADIUS}"></circle>'


def _write_label(rank: int, text: str) -> str:
    y = CHART_TOP + CHART_HEIGHT + LABEL_LINE * rank
    return f'<text class="cap-label" x="0" y="{y}">{escape(text)}</text>'


def _describe_changes(budget: dict) -> list[str]:
    if budget["stable"]:
        return [f"stable at {budget['applied']}"]
    return [
        f"{change['direction']} at {change['ts']}: {change['before']} to {change['after']}"
        for change in budget["history"]
    ]


def render_cap_history(role: str, budget: dict) -> str:
    caps = _list_caps(budget)
    path = draw_step_path(caps, max(caps), LINE_TONE, FRAME)
    marks = "".join(
        _draw_mark(change, *corner) for change, corner in zip(budget["history"], path.corners[1:], strict=True)
    )
    labels = _describe_changes(budget)
    height = CHART_TOP + CHART_HEIGHT + LABEL_LINE * len(labels) + LABEL_DESCENT
    return (
        f'<svg class="cap-history" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(f"turn cap of {role}")}">'
        f'<text class="cap-role" x="0" y="{ROLE_BASELINE}">{escape(role)}</text>'
        f"{path.markup}{marks}"
        + "".join(_write_label(rank, text) for rank, text in enumerate(labels, start=1))
        + "</svg>"
    )
