from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_filter_picker import FILTER_PARAMETER, VALUE_SEPARATOR

SEARCH_PARAMETER = "search"
TYPE_PARAMETER = "type"
REMOVE = "Remove this filter"


def _render_chip(address: AwawaAddress, label: str) -> str:
    return f'<a class="chip" href="{escape(address.link())}" title="{REMOVE}">{escape(label)} ✕</a>'


def _group_by_field(filters: tuple[str, ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for written in filters:
        field, _, value = written.partition(VALUE_SEPARATOR)
        grouped.setdefault(field, []).append(value)
    return grouped


def _render_field_chip(address: AwawaAddress, field: str, values: list[str]) -> str:
    kept = address
    for value in values:
        kept = kept.removing(FILTER_PARAMETER, f"{field}{VALUE_SEPARATOR}{value}")
    entity_type = address.read(TYPE_PARAMETER)
    named = f"{field.capitalize()}: {', '.join(values)}"
    return _render_chip(kept, named if entity_type is None else f"{entity_type.capitalize()} · {named}")


def render_awawa_chips(address: AwawaAddress) -> str:
    filters = address.read_all(FILTER_PARAMETER)
    search = address.read(SEARCH_PARAMETER)
    if not filters and search is None:
        return ""
    chips = [_render_field_chip(address, field, values) for field, values in _group_by_field(filters).items()]
    if search is not None:
        chips.append(_render_chip(address.removing(SEARCH_PARAMETER), f"Search: {search}"))
    cleared = address.removing(FILTER_PARAMETER).removing(SEARCH_PARAMETER)
    return f'<nav class="chips">{"".join(chips)}<a class="muted" href="{escape(cleared.link())}">Clear all</a></nav>'
