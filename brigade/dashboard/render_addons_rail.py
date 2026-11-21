from html import escape
from urllib.parse import quote

TAB = "#awawa/"


def _render_link(project: str, label: str) -> str:
    return f'<a href="{escape(TAB + quote(project, safe=""))}" data-rail-view="awawa">{escape(label)}</a>'


def render_addons_rail(holders: frozenset[str], project: str | None) -> str:
    if project is not None:
        return _render_link(project, "awawa") if project in holders else ""
    return "".join(_render_link(holder, f"awawa · {holder}") for holder in sorted(holders))
