from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, AwawaSelector, render_awawa_form

REF_PARAMETER = "ref"


def render_awawa_banner(document: dict, address: AwawaAddress) -> str:
    selector = AwawaSelector(name=REF_PARAMETER, label="ref", options=tuple(document["refs"]), chosen=document["ref"])
    form = AwawaForm(
        css_class="awawa-ref", address=address, controls=selector.render(), replaced=(REF_PARAMETER,), button=None
    )
    return (
        f'<header class="awawa-banner"><p class="awawa-reading"><strong>{escape(document["project"])}</strong>'
        f" at <code>{escape(document['ref'])}</code>, commit <code>{escape(document['sha'])}</code></p>"
        f"{render_awawa_form(form)}</header>"
    )
