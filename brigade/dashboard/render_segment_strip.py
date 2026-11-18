from dataclasses import dataclass
from html import escape
from itertools import accumulate

from brigade.dashboard.read_state_tone import read_state_tone

STRIP_WIDTH = 100


@dataclass(frozen=True)
class Segment:
    label: str
    state: str
    length: float


def _render_segment(segment: Segment, start: float, scale: float) -> str:
    return (
        f'<rect class="segment tone-{read_state_tone(segment.state)}" x="{start * scale:g}"'
        f' width="{segment.length * scale:g}" height="8"><title>{escape(segment.label)}</title></rect>'
    )


def render_segment_strip(label: str, segments: list[Segment]) -> str:
    lengths = [segment.length for segment in segments]
    starts = [0, *accumulate(lengths)]
    scale = STRIP_WIDTH / starts[-1] if segments else 0
    rects = "".join(_render_segment(segment, start, scale) for segment, start in zip(segments, starts, strict=False))
    return (
        f'<svg class="segment-strip" viewBox="0 0 {STRIP_WIDTH} 8" role="img" aria-label="{escape(label)}">'
        f"{rects}</svg>"
    )
