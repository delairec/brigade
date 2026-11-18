from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone

TRACK_WIDTH = 100
NO_FILL = 0


@dataclass(frozen=True)
class SvgBar:
    label: str
    state: str
    value: float
    total: float


def _measure_fill(bar: SvgBar) -> float:
    if bar.total <= 0:
        return NO_FILL
    return min(bar.value / bar.total, 1) * TRACK_WIDTH


def render_svg_bar(bar: SvgBar) -> str:
    return (
        f'<svg class="bar" viewBox="0 0 {TRACK_WIDTH} 8" role="img" aria-label="{escape(bar.label)}">'
        f'<rect class="bar-track" width="{TRACK_WIDTH}" height="8"></rect>'
        f'<rect class="bar-fill tone-{read_state_tone(bar.state)}" width="{_measure_fill(bar):g}" height="8"></rect>'
        "</svg>"
    )
