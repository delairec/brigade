from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_card import render_awawa_card


def render_awawa_cards(cards: list[dict], address: AwawaAddress) -> str:
    items = "".join(f"<li>{render_awawa_card(card, address)}</li>" for card in cards)
    return f'<ul class="awawa-cards">{items}</ul>'
