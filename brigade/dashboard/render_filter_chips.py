from dataclasses import dataclass
from html import escape

CHOSEN = ' aria-current="true"'


@dataclass(frozen=True)
class FilterChip:
    label: str
    view: str
    chosen: bool


def _render_chip(chip: FilterChip) -> str:
    current = CHOSEN if chip.chosen else ""
    address = escape(f"#{chip.view}")
    return f'<a class="chip" href="{address}"{current}>{escape(chip.label)}</a>'


def render_filter_chips(chips: list[FilterChip]) -> str:
    return f'<nav class="chips">{"".join(_render_chip(chip) for chip in chips)}</nav>'
