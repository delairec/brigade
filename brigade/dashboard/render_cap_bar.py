from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone

TRACK_WIDTH = 100


@dataclass(frozen=True)
class CapBar:
    label: str
    state: str
    value: float
    cap: float


def _place(measure: float, bar: CapBar) -> float:
    return measure / max(bar.value, bar.cap) * TRACK_WIDTH


def render_cap_bar(bar: CapBar) -> str:
    cap = _place(bar.cap, bar)
    return (
        f'<svg class="bar" viewBox="0 0 {TRACK_WIDTH} 8" role="img" aria-label="{escape(bar.label)}">'
        f'<rect class="bar-track" width="{TRACK_WIDTH}" height="8"></rect>'
        f'<rect class="bar-fill tone-{read_state_tone(bar.state)}" width="{_place(bar.value, bar):g}" height="8"></rect>'
        f'<line class="bar-cap" x1="{cap:g}" y1="0" x2="{cap:g}" y2="8"></line>'
        "</svg>"
    )
