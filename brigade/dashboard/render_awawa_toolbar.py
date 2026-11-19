from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, render_awawa_form

VIEWS = (("tree", "Tree"), ("board", "Board"), ("dependencies", "Dependencies"), ("health", "Health"))
VIEWS_OF_A_TYPE = ("board", "dependencies")
SCHEMA_TYPES = ("SCHEMA", "FIELDSET", "SHAPE")
FIRST_VIEW = "tree"
CHOSEN = ' aria-current="true"'
BOARD_VIEW = "board"


def _render_link(address: AwawaAddress, label: str, *, chosen: bool) -> str:
    return f'<a href="{escape(address.link())}"{CHOSEN if chosen else ""}>{escape(label)}</a>'


def _render_views(document: dict, address: AwawaAddress) -> str:
    shown = address.read("view") or FIRST_VIEW
    domain = [entity_type for entity_type in document["types"] if entity_type not in SCHEMA_TYPES]
    typed = address if address.read("type") or not domain else address.setting("type", domain[0])
    links = "".join(
        _render_link((typed if view in VIEWS_OF_A_TYPE else address).setting("view", view), label, chosen=view == shown)
        for view, label in VIEWS
    )
    return f'<nav class="awawa-views">{links}</nav>'


def _render_types(document: dict, address: AwawaAddress) -> str:
    unfiltered = address.removing("filter")
    links = "".join(
        _render_link(unfiltered.setting("type", entity_type), entity_type, chosen=entity_type == address.read("type"))
        for entity_type in document["types"]
    )
    return f'<nav class="awawa-types">{links}</nav>'


def _render_field(document: dict, address: AwawaAddress) -> str:
    if document["view"] != BOARD_VIEW:
        return ""
    controls = f'<label>Field <input name="field" value="{escape(document["field"])}"></label>'
    return render_awawa_form(
        AwawaForm(css_class="awawa-field", address=address, controls=controls, replaced=("field",), button="Group")
    )


def _render_search(address: AwawaAddress) -> str:
    controls = (
        f'<label>Search <input type="search" name="search" value="{escape(address.read("search") or "")}"></label>'
        '<label>Filter <input name="filter" placeholder="FIELD=value"></label>'
    )
    return render_awawa_form(
        AwawaForm(css_class="awawa-search", address=address, controls=controls, replaced=("search",), button="Apply")
    )


def render_awawa_toolbar(document: dict, address: AwawaAddress) -> str:
    return (
        f'<div class="awawa-toolbar">{_render_views(document, address)}{_render_types(document, address)}'
        f"{_render_field(document, address)}{_render_search(address)}</div>"
    )
