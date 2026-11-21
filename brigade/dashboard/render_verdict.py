from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


@dataclass(frozen=True)
class Verdict:
    sentence: str
    explanation: str
    state: str


def _render_explanation(explanation: str) -> str:
    if not explanation:
        return ""
    return f"<p>{escape(explanation)}</p>"


def render_verdict(verdict: Verdict) -> str:
    return (
        f'<div class="verdict tone-{read_state_tone(verdict.state)}">'
        f'<p class="status-sentence">{escape(verdict.sentence)}</p>{_render_explanation(verdict.explanation)}</div>'
    )
