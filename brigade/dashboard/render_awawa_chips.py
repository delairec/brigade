from html import escape

from brigade.dashboard.awawa_address import AwawaAddress

FILTER_PARAMETER = "filter"
SEARCH_PARAMETER = "search"


def _render_chip(address: AwawaAddress, label: str) -> str:
    return f'<a class="chip" href="{escape(address.link())}">{escape(label)}</a>'


def render_awawa_chips(address: AwawaAddress) -> str:
    filters = address.read_all(FILTER_PARAMETER)
    search = address.read(SEARCH_PARAMETER)
    if not filters and search is None:
        return ""
    chips = [_render_chip(address.removing(FILTER_PARAMETER, written), f"{written} ✕") for written in filters]
    if search is not None:
        chips.append(_render_chip(address.removing(SEARCH_PARAMETER), f"Search: {search} ✕"))
    cleared = address.removing(FILTER_PARAMETER).removing(SEARCH_PARAMETER)
    return f'<nav class="chips">{"".join(chips)}{_render_chip(cleared, "Clear all")}</nav>'
