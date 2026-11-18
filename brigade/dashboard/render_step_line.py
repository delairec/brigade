from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone

WIDTH = 100
HEIGHT = 40


@dataclass(frozen=True)
class StepLine:
    label: str
    state: str
    values: tuple[float, ...]
    ceiling: float


def _draw_path(line: StepLine) -> str:
    step = WIDTH / len(line.values)
    heights = [HEIGHT - value / line.ceiling * HEIGHT for value in line.values]
    moves = [f"M0 {heights[0]:g} H{step:g}"]
    moves.extend(f"V{height:g} H{step * (rank + 2):g}" for rank, height in enumerate(heights[1:]))
    return f'<path class="step-path tone-{read_state_tone(line.state)}" d="{" ".join(moves)}"></path>'


def render_step_line(line: StepLine) -> str:
    path = _draw_path(line) if line.values else ""
    return (
        f'<svg class="step-line" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(line.label)}">'
        f"{path}</svg>"
    )
