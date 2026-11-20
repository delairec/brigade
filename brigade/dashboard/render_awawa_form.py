from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.awawa_address import AwawaAddress

TAB_VIEW = "awawa/"


@dataclass(frozen=True)
class AwawaForm:
    css_class: str
    address: AwawaAddress
    controls: str
    replaced: tuple[str, ...]
    button: str


def render_awawa_form(form: AwawaForm) -> str:
    hidden = "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in form.address.parameters
        if name not in form.replaced
    )
    view = f"{TAB_VIEW}{quote(form.address.project, safe='')}"
    return (
        f'<form class="{form.css_class}" method="get" data-view="{escape(view)}">'
        f"{hidden}{form.controls}<button>{form.button}</button></form>"
    )
