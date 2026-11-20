from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, AwawaSelector, render_awawa_form

VIEWS = (("tree", "Tree"), ("board", "Board"), ("dependencies", "Dependencies"), ("health", "Health"))
VIEWS_OF_A_TYPE = ("board", "dependencies")
SCHEMA_TYPES = ("SCHEMA", "FIELDSET", "SHAPE")
FIRST_VIEW = "tree"
SELECTED = ' aria-selected="true"'
FIELD_LABELS = {"board": "By", "dependencies": "Follow"}


def _render_tab(address: AwawaAddress, label: str, *, selected: bool) -> str:
    return f'<a role="tab" href="{escape(address.link())}"{SELECTED if selected else ""}>{escape(label)}</a>'


def _render_views(document: dict, address: AwawaAddress) -> str:
    shown = address.read("view") or FIRST_VIEW
    domain = [entity_type for entity_type in document["types"] if entity_type not in SCHEMA_TYPES]
    typed = address if address.read("type") or not domain else address.setting("type", domain[0])
    tabs = "".join(
        _render_tab(
            (typed if view in VIEWS_OF_A_TYPE else address).setting("view", view), label, selected=view == shown
        )
        for view, label in VIEWS
    )
    return f'<div class="tabs" role="tablist" aria-label="View">{tabs}</div>'


def _render_types(document: dict, address: AwawaAddress) -> str:
    selector = AwawaSelector(name="type", label="Type", options=tuple(document["types"]), chosen=address.read("type"))
    form = AwawaForm(
        css_class="awawa-type",
        address=address.removing("filter"),
        controls=selector.render(),
        replaced=("type",),
        button=None,
    )
    return render_awawa_form(form)


def _render_field(document: dict, address: AwawaAddress) -> str:
    label = FIELD_LABELS.get(document["view"])
    if label is None:
        return ""
    selector = AwawaSelector(name="field", label=label, options=tuple(document["fields"]), chosen=document["field"])
    form = AwawaForm(
        css_class="awawa-field", address=address, controls=selector.render(), replaced=("field",), button=None
    )
    return render_awawa_form(form)


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
