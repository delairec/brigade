from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


@dataclass(frozen=True)
class VerdictLink:
    label: str
    address: str


@dataclass(frozen=True)
class Verdict:
    sentence: str
    explanation: tuple[str | VerdictLink, ...]
    state: str


def _render_part(part: str | VerdictLink) -> str:
    if isinstance(part, VerdictLink):
        return f'<a class="mono" href="{escape(part.address)}">{escape(part.label)}</a>'
    return escape(part)


def _render_explanation(explanation: tuple[str | VerdictLink, ...]) -> str:
    if not explanation:
        return ""
    return f"<p>{''.join(map(_render_part, explanation))}</p>"


def render_verdict(verdict: Verdict) -> str:
    return (
        f'<div class="verdict tone-{read_state_tone(verdict.state)}">'
        f'<p class="status-sentence">{escape(verdict.sentence)}</p>{_render_explanation(verdict.explanation)}</div>'
    )
