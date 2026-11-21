from brigade.dashboard.awawa_addon_supervisor import NOT_FOUND, OK, UNAVAILABLE, AddonAnswer
from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_banner import render_awawa_banner
from brigade.dashboard.render_awawa_board import render_awawa_board
from brigade.dashboard.render_awawa_chips import render_awawa_chips
from brigade.dashboard.render_awawa_dependencies import render_awawa_dependencies
from brigade.dashboard.render_awawa_detail import render_awawa_detail
from brigade.dashboard.render_awawa_health import render_awawa_health
from brigade.dashboard.render_awawa_toolbar import render_awawa_toolbar
from brigade.dashboard.render_awawa_tree import render_awawa_tree
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_page_head import PageHead, render_page_head

HEAD = PageHead(
    title="awawa",
    lede="The specification of the project, read-only: its entities as a tree, a board and a dependency tree,"
    " and what awawa lint finds.",
)
VIEW_RENDERERS = {
    "tree": render_awawa_tree,
    "board": render_awawa_board,
    "dependencies": render_awawa_dependencies,
    "health": render_awawa_health,
}


def _render_unanswered(answer: AddonAnswer, address: AwawaAddress) -> str:
    if answer.status == NOT_FOUND:
        return render_empty_state(
            f"{address.project} has no awawa corpus.",
            "A corpus awawa finds in the folder of the project would fill this tab.",
        )
    if answer.status == UNAVAILABLE:
        return render_empty_state("The awawa addon stopped.", answer.document["error"])
    return render_empty_state("The corpus could not be read at this address.", answer.document["error"])


def render_awawa_tab(answer: AddonAnswer, address: AwawaAddress) -> str:
    if answer.status != OK:
        return _render_unanswered(answer, address)
    document = answer.document
    view = VIEW_RENDERERS[document["view"]](document, address)
    return (
        f"{render_page_head(HEAD)}{render_awawa_banner(document, address)}{render_awawa_toolbar(document, address)}"
        f"{render_awawa_chips(address)}"
        f'<div class="awawa-body"><div class="awawa-view">{view}</div>{render_awawa_detail(document, address)}</div>'
    )
