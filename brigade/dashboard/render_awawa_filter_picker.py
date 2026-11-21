from dataclasses import dataclass
from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, render_awawa_form

PICK_PARAMETER = "pick"
FILTER_PARAMETER = "filter"
HASH = "#"
CHOSEN = " selected"
VALUE_SEPARATOR = "="


@dataclass(frozen=True)
class _Choice:
    value: str
    label: str
    leads_to: AwawaAddress
    chosen: bool


def _render_choice(choice: _Choice) -> str:
    leads_to = escape(choice.leads_to.link().removeprefix(HASH))
    chosen = CHOSEN if choice.chosen else ""
    return f'<option value="{escape(choice.value)}" data-href="{leads_to}"{chosen}>{escape(choice.label)}</option>'


def _render_selector(control: str, label: str, prompt: str, choices: list[_Choice], name: str) -> str:
    prompted = "" if any(choice.chosen for choice in choices) else CHOSEN
    options = "".join(map(_render_choice, choices))
    return (
        f'<span class="field"><label for="{control}">{escape(label)}</label>'
        f'<select id="{control}" name="{name}"><option value=""{prompted}>{prompt}</option>{options}</select></span>'
    )


def _render_values(values: list[str], field: str, address: AwawaAddress) -> str:
    unpicked = address.removing(PICK_PARAMETER)
    in_force = address.read_all(FILTER_PARAMETER)
    choices = [
        _Choice(written, value, unpicked.adding(FILTER_PARAMETER, written), chosen=False)
        for value in values
        if (written := f"{field}{VALUE_SEPARATOR}{value}") not in in_force
    ]
    return _render_selector("awawa-value", field, "Choose a value", choices, FILTER_PARAMETER)


def render_awawa_filter_picker(values: dict[str, list[str]], address: AwawaAddress) -> str:
    if not values:
        return ""
    picked = address.read(PICK_PARAMETER)
    fields = [_Choice(field, field, address.setting(PICK_PARAMETER, field), chosen=field == picked) for field in values]
    controls = _render_selector("awawa-pick", "Filter", "Add a filter", fields, PICK_PARAMETER)
    if picked in values:
        controls += _render_values(values[picked], picked, address)
    form = AwawaForm(
        css_class="awawa-filter", address=address, controls=controls, replaced=(PICK_PARAMETER,), button=None
    )
    return render_awawa_form(form)
