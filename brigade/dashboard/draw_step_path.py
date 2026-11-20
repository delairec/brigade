from dataclasses import dataclass


@dataclass(frozen=True)
class StepFrame:
    width: float
    top: float
    height: float


@dataclass(frozen=True)
class StepPath:
    markup: str
    corners: tuple[tuple[float, float], ...]


def draw_step_path(values: tuple[float, ...], ceiling: float, tone: str, frame: StepFrame) -> StepPath:
    step = frame.width / len(values)
    heights = [frame.top + frame.height * (1 - value / ceiling) for value in values]
    moves = [f"M0 {heights[0]:g} H{step:g}"]
    moves.extend(f"V{height:g} H{step * rank:g}" for rank, height in enumerate(heights[1:], start=2))
    return StepPath(
        markup=f'<path class="step-path tone-{tone}" d="{" ".join(moves)}"></path>',
        corners=tuple((step * rank, height) for rank, height in enumerate(heights)),
    )
