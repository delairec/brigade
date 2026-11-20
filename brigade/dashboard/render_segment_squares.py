from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


def _render_square(outcome: str) -> str:
    return f'<span class="segment-square tone-{read_state_tone(outcome)}" title="{escape(outcome)}"></span>'


def render_segment_squares(outcomes: list[str]) -> str:
    label = escape(f"segments: {', '.join(outcomes)}")
    squares = "".join(_render_square(outcome) for outcome in outcomes)
    return f'<span class="segment-squares" role="img" aria-label="{label}">{squares}</span>'
