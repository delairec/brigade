from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_filter_picker import render_awawa_filter_picker
from brigade.dashboard.render_awawa_form import AwawaForm, AwawaSelector, render_awawa_form

VIEWS = (("tree", "Tree"), ("board", "Board"), ("dependencies", "Dependencies"), ("health", "Health"))
VIEWS_OF_A_TYPE = ("board", "dependencies")
SCHEMA_TYPES = ("SCHEMA", "FIELDSET", "SHAPE")
FIRST_VIEW = "tree"
SELECTED = ' aria-selected="true"'
FIELD_LABELS = {"board": "By", "dependencies": "Follow"}
NO_SELECTOR = ""
NO_COUNT = ""
VIEWS_OF_NO_TYPE = ("health",)
EVERY_TYPE = "Every type"
SEARCH_PROMPT = "Search the label, the name or a fact"


def _render_tab(address: AwawaAddress, label: str, count: str, *, selected: bool) -> str:
    return f'<a role="tab" href="{escape(address.link())}"{SELECTED if selected else ""}>{escape(label)}{count}</a>'


def _render_views(document: dict, address: AwawaAddress) -> str:
    shown = address.read("view") or FIRST_VIEW
    domain = [entity_type for entity_type in document["types"] if entity_type not in SCHEMA_TYPES]
    typed = address if address.read("type") or not domain else address.setting("type", domain[0])
    counts = {"health": f' <span class="num">{document["diagnostics"]}</span>'}
    tabs = "".join(
        _render_tab(
            (typed if view in VIEWS_OF_A_TYPE else address).setting("view", view),
            label,
            counts.get(view, NO_COUNT),
            selected=view == shown,
        )
        for view, label in VIEWS
    )
    return f'<div class="tabs" role="tablist" aria-label="View">{tabs}</div>'


def _render_types(document: dict, address: AwawaAddress) -> str:
    if document["view"] in VIEWS_OF_NO_TYPE:
        return NO_SELECTOR
    unfiltered = address.removing("filter")
    selector = AwawaSelector(
        name="type",
        label="Type",
        options=tuple(document["types"]),
        chosen=address.read("type"),
        address=unfiltered,
        prompt=None if document["view"] in VIEWS_OF_A_TYPE else EVERY_TYPE,
    )
    form = AwawaForm(
        css_class="awawa-type",
        address=unfiltered,
        controls=selector.render(),
        replaced=("type",),
        button=None,
    )
    return render_awawa_form(form)


def _render_field(document: dict, address: AwawaAddress) -> str:
    label = FIELD_LABELS.get(document["view"])
    if label is None:
        return NO_SELECTOR
    selector = AwawaSelector(
        name="field", label=label, options=tuple(document["fields"]), chosen=document["field"], address=address
    )
    form = AwawaForm(
        css_class="awawa-field", address=address, controls=selector.render(), replaced=("field",), button=None
    )
    return render_awawa_form(form)


def _render_search(address: AwawaAddress) -> str:
    controls = (
        '<span class="field"><label for="awawa-search" class="mono">search</label><input type="search"'
        f' id="awawa-search" name="search" value="{escape(address.read("search") or "")}"'
        f' placeholder="{SEARCH_PROMPT}" data-pauses-poll></span>'
    )
    return render_awawa_form(
        AwawaForm(css_class="awawa-search", address=address, controls=controls, replaced=("search",), button=None)
    )


def render_awawa_toolbar(document: dict, address: AwawaAddress) -> str:
    return (
        f'<div class="awawa-toolbar">{_render_views(document, address)}{_render_types(document, address)}'
        f"{_render_field(document, address)}{_render_search(address)}"
        f"{render_awawa_filter_picker(document['filter_values'], address)}</div>"
    )
