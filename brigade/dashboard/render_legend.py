from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


@dataclass(frozen=True)
class LegendItem:
    label: str
    state: str
    soft: bool = False


def _render_item(item: LegendItem) -> str:
    soft = " soft" if item.soft else ""
    return f'<span class="tone-{read_state_tone(item.state)}{soft}">{escape(item.label)}</span>'


def render_legend(items: tuple[LegendItem, ...]) -> str:
    return f'<figcaption class="legend">{"".join(_render_item(item) for item in items)}</figcaption>'
