from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class StatTile:
    label: str
    value: str
    perimeter: str


def render_stat_tile(tile: StatTile) -> str:
    return (
        f'<div class="stat-tile"><span class="stat-value">{escape(tile.value)}</span>'
        f'<span class="stat-label">{escape(tile.label)}</span>'
        f'<span class="stat-perimeter">{escape(tile.perimeter)}</span></div>'
    )
