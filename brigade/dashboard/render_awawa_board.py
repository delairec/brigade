from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_cards import render_awawa_cards


def _render_column(column: dict, address: AwawaAddress) -> str:
    return (
        f'<section class="awawa-column"><h3>{escape(column["label"])} '
        f'<span class="awawa-count">{len(column["entities"])}</span></h3>'
        f"{render_awawa_cards(column['entities'], address)}</section>"
    )


def render_awawa_board(document: dict, address: AwawaAddress) -> str:
    columns = "".join(_render_column(column, address) for column in document["columns"])
    return f'<div class="awawa-board">{columns}</div>'
