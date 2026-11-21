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


@dataclass(frozen=True)
class _Selector:
    control: str
    label: str
    prompt: str
    name: str
    choices: list[_Choice]

    def render(self) -> str:
        prompted = "" if any(choice.chosen for choice in self.choices) else CHOSEN
        options = "".join(map(_render_choice, self.choices))
        return (
            f'<span class="field"><label for="{self.control}">{escape(self.label)}</label>'
            f'<select id="{self.control}" name="{self.name}"><option value=""{prompted}>{self.prompt}</option>'
            f"{options}</select></span>"
        )


def _render_values(values: list[str], field: str, address: AwawaAddress) -> str:
    unpicked = address.removing(PICK_PARAMETER)
    in_force = address.read_all(FILTER_PARAMETER)
    choices = [
        _Choice(written, value, unpicked.adding(FILTER_PARAMETER, written), chosen=False)
        for value in values
        if (written := f"{field}{VALUE_SEPARATOR}{value}") not in in_force
    ]
    return _Selector("awawa-value", field, "Choose a value", FILTER_PARAMETER, choices).render()


def render_awawa_filter_picker(values: dict[str, list[str]], address: AwawaAddress) -> str:
    if not values:
        return ""
    picked = address.read(PICK_PARAMETER)
    fields = [_Choice(field, field, address.setting(PICK_PARAMETER, field), chosen=field == picked) for field in values]
    controls = _Selector("awawa-pick", "Filter", "Add a filter", PICK_PARAMETER, fields).render()
    if picked in values:
        controls += _render_values(values[picked], picked, address)
    form = AwawaForm(
        css_class="awawa-filter", address=address, controls=controls, replaced=(PICK_PARAMETER,), button=None
    )
    return render_awawa_form(form)
