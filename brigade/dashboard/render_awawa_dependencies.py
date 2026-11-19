from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_card import render_awawa_card
from brigade.dashboard.render_nothing_matching import render_nothing_matching

CYCLE_FLAG = '<span class="awawa-flag tone-failed">cycle</span>'
ABOVE_FLAG = '<span class="awawa-flag">shown above</span>'


def _render_nodes(nodes: list[dict], address: AwawaAddress) -> str:
    return f'<ul class="awawa-nodes">{"".join(_render_node(node, address) for node in nodes)}</ul>'


def _render_node(node: dict, address: AwawaAddress) -> str:
    cycle = CYCLE_FLAG if node["in_cycle"] else ""
    above = ABOVE_FLAG if node["already_above"] else ""
    dependents = _render_nodes(node["dependents"], address) if node["dependents"] else ""
    return f"<li>{render_awawa_card(node, address)}{cycle}{above}{dependents}</li>"


def render_awawa_dependencies(document: dict, address: AwawaAddress) -> str:
    if not document["roots"]:
        return render_nothing_matching()
    return (
        '<div class="awawa-dependencies"><p class="awawa-reading">'
        f"Each entity stands above the entities naming it in {escape(document['field'])}.</p>"
        f"{_render_nodes(document['roots'], address)}</div>"
    )
