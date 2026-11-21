from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, AwawaSelector, render_awawa_form

REF_PARAMETER = "ref"
SHOWN_SHA_LENGTH = 8


def _render_sha(sha: str) -> str:
    if len(sha) <= SHOWN_SHA_LENGTH:
        return f"<code>{escape(sha)}</code>"
    return f'<code title="{escape(sha)}">{escape(sha[:SHOWN_SHA_LENGTH])}</code>'


def render_awawa_banner(document: dict, address: AwawaAddress) -> str:
    selector = AwawaSelector(
        name=REF_PARAMETER, label="ref", options=tuple(document["refs"]), chosen=document["ref"], address=address
    )
    form = AwawaForm(
        css_class="awawa-ref", address=address, controls=selector.render(), replaced=(REF_PARAMETER,), button=None
    )
    return (
        f'<header class="awawa-banner"><p class="awawa-reading"><strong>{escape(document["project"])}</strong>'
        f" at <code>{escape(document['ref'])}</code>, commit {_render_sha(document['sha'])}</p>"
        f"{render_awawa_form(form)}</header>"
    )
