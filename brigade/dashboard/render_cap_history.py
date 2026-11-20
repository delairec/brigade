from html import escape

WIDTH = 400
ROLE_BASELINE = 12
CHART_TOP = 20
CHART_HEIGHT = 40
LABEL_LINE = 14
LABEL_DESCENT = 4
MARK_RADIUS = 3
LINE_TONE = "work"
DIRECTION_TONES = {"raised": "limit", "lowered": "done"}


def _list_caps(budget: dict) -> list[int]:
    if budget["stable"]:
        return [budget["applied"]]
    history = budget["history"]
    return [history[0]["before"], *(change["after"] for change in history)]


def _place_cap(cap: int, ceiling: int) -> float:
    return CHART_TOP + CHART_HEIGHT * (1 - cap / ceiling)


def _draw_path(heights: list[float], step: float) -> str:
    moves = [f"M0 {heights[0]:g} H{step:g}"]
    moves.extend(f"V{height:g} H{step * rank:g}" for rank, height in enumerate(heights[1:], start=2))
    return f'<path class="step-path tone-{LINE_TONE}" d="{" ".join(moves)}"></path>'


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
    ceiling = max(caps)
    heights = [_place_cap(cap, ceiling) for cap in caps]
    step = WIDTH / len(caps)
    marks = "".join(
        _draw_mark(change, step * rank, heights[rank]) for rank, change in enumerate(budget["history"], start=1)
    )
    labels = _describe_changes(budget)
    height = CHART_TOP + CHART_HEIGHT + LABEL_LINE * len(labels) + LABEL_DESCENT
    return (
        f'<svg class="cap-history" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(f"turn cap of {role}")}">'
        f'<text class="cap-role" x="0" y="{ROLE_BASELINE}">{escape(role)}</text>'
        f"{_draw_path(heights, step)}{marks}"
        + "".join(_write_label(rank, text) for rank, text in enumerate(labels, start=1))
        + "</svg>"
    )
