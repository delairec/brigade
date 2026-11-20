from dataclasses import dataclass
from html import escape

from brigade.dashboard.draw_step_path import StepFrame, draw_step_path
from brigade.dashboard.read_state_tone import read_state_tone

WIDTH = 100
HEIGHT = 40
FRAME = StepFrame(width=WIDTH, top=0, height=HEIGHT)


@dataclass(frozen=True)
class StepLine:
    label: str
    state: str
    values: tuple[float, ...]
    ceiling: float


def _draw_path(line: StepLine) -> str:
    return draw_step_path(line.values, line.ceiling, read_state_tone(line.state), FRAME).markup


def render_step_line(line: StepLine) -> str:
    path = _draw_path(line) if line.values else ""
    return (
        f'<svg class="step-line" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(line.label)}">'
        f"{path}</svg>"
    )
