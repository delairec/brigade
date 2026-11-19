from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, render_awawa_form

REF_PARAMETER = "ref"


def render_awawa_banner(document: dict, address: AwawaAddress) -> str:
    options = "".join(f'<option value="{escape(ref)}"></option>' for ref in document["refs"])
    controls = (
        f'<label>Ref <input name="ref" list="awawa-refs" value="{escape(document["ref"])}"></label>'
        f'<datalist id="awawa-refs">{options}</datalist>'
    )
    form = AwawaForm(
        css_class="awawa-ref", address=address, controls=controls, replaced=(REF_PARAMETER,), button="Read"
    )
    return (
        f'<header class="awawa-banner"><p class="awawa-reading"><strong>{escape(document["project"])}</strong>'
        f" at <code>{escape(document['ref'])}</code>, commit <code>{escape(document['sha'])}</code></p>"
        f"{render_awawa_form(form)}</header>"
    )
