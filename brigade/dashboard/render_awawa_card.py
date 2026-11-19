from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_dot import render_awawa_dot

ENTITY_PARAMETER = "entity"
VALUE_SEPARATOR = ", "
WAITING_MARK = '<span class="awawa-waiting" title="waits on an entity of its type not past its status">waiting</span>'


def _render_value(value: dict) -> str:
    dot = "" if value["target"] is None else render_awawa_dot(value["status"])
    return f"{dot}{escape(value['text'])}"


def _render_facts(facts: list[dict]) -> str:
    if not facts:
        return ""
    rendered = "".join(
        f'<span class="awawa-fact">{escape(fact["field"])} '
        f"{VALUE_SEPARATOR.join(_render_value(value) for value in fact['values'])}</span>"
        for fact in facts
    )
    return f'<span class="awawa-facts">{rendered}</span>'


def render_awawa_card(card: dict, address: AwawaAddress) -> str:
    link = address.setting(ENTITY_PARAMETER, card["target"]).link()
    value = f'<span class="awawa-value">{escape(card["value"])}</span>' if "value" in card else ""
    waiting = WAITING_MARK if card["waiting"] else ""
    return (
        f'<div class="awawa-card">{render_awawa_dot(card["status"])}<a href="{escape(link)}">'
        f'<span class="awawa-code">{escape(card["code"])}</span> '
        f'<span class="awawa-label">{escape(card["label"])}</span></a>'
        f"{value}{waiting}{_render_facts(card['facts'])}</div>"
    )
