from dataclasses import dataclass
from html import escape

CHOSEN = ' aria-current="true"'


@dataclass(frozen=True)
class FilterChip:
    label: str
    view: str
    chosen: bool
    count: int | None = None


def _render_chip(chip: FilterChip) -> str:
    current = CHOSEN if chip.chosen else ""
    address = escape(f"#{chip.view}")
    count = "" if chip.count is None else f" <b>{chip.count}</b>"
    return f'<a class="chip" href="{address}"{current}>{escape(chip.label)}{count}</a>'


def render_filter_chips(chips: list[FilterChip]) -> str:
    return f'<nav class="chips">{"".join(_render_chip(chip) for chip in chips)}</nav>'
