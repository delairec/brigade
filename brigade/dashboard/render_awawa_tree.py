from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_cards import render_awawa_cards
from brigade.dashboard.render_nothing_matching import render_nothing_matching

NO_STATUS = "no status"


def _render_group(group: dict, address: AwawaAddress) -> str:
    opened = "" if group["collapsed"] else " open"
    status = NO_STATUS if group["status"] is None else group["status"]
    return (
        f'<details class="awawa-group"{opened}><summary>{escape(status)} '
        f'<span class="awawa-count">{len(group["entities"])}</span></summary>'
        f"{render_awawa_cards(group['entities'], address)}</details>"
    )


def _render_type(described: dict, address: AwawaAddress) -> str:
    if "groups" in described:
        content = "".join(_render_group(group, address) for group in described["groups"])
        kept = sum(len(group["entities"]) for group in described["groups"])
    else:
        content = render_awawa_cards(described["entities"], address)
        kept = len(described["entities"])
    heading = described["type"].replace("_", " ").capitalize()
    count = str(kept) if kept == described["total"] else f"{kept} of {described['total']}"
    return f'<section class="awawa-type"><h2>{escape(heading)} <small>{count}</small></h2>{content}</section>'


def render_awawa_tree(document: dict, address: AwawaAddress) -> str:
    if not document["domain"] and not document["schema"]:
        return render_nothing_matching()
    domain = "".join(_render_type(described, address) for described in document["domain"])
    schema = "".join(_render_type(described, address) for described in document["schema"])
    folded = f'<details class="awawa-schema"><summary>Schema</summary>{schema}</details>' if schema else ""
    return f'<div class="awawa-tree">{domain}{folded}</div>'
