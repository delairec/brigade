from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.awawa_address import AwawaAddress

TAB_VIEW = "awawa/"
CHOSEN = " selected"
HASH = "#"


@dataclass(frozen=True)
class AwawaSelector:
    name: str
    label: str
    options: tuple[str, ...]
    chosen: str | None
    address: AwawaAddress

    def _render_option(self, option: str) -> str:
        leads_to = self.address.setting(self.name, option).link().removeprefix(HASH)
        chosen = CHOSEN if option == self.chosen else ""
        return f'<option value="{escape(option)}" data-href="{escape(leads_to)}"{chosen}>{escape(option)}</option>'

    def render(self) -> str:
        control = f"awawa-{escape(self.name)}"
        options = "".join(self._render_option(option) for option in self.options)
        return (
            f'<span class="field"><label for="{control}">{escape(self.label)}</label>'
            f'<select id="{control}" name="{escape(self.name)}">{options}</select></span>'
        )


@dataclass(frozen=True)
class AwawaForm:
    css_class: str
    address: AwawaAddress
    controls: str
    replaced: tuple[str, ...]
    button: str | None


def render_awawa_form(form: AwawaForm) -> str:
    hidden = "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in form.address.parameters
        if name not in form.replaced
    )
    view = f"{TAB_VIEW}{quote(form.address.project, safe='')}"
    button = "" if form.button is None else f"<button>{form.button}</button>"
    return (
        f'<form class="{form.css_class}" method="get" data-view="{escape(view)}">{hidden}{form.controls}{button}</form>'
    )
