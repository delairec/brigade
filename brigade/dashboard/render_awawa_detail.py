from html import escape

from brigade.corpus.corpus_reader import read_atoms
from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_dot import render_awawa_dot

ENTITY_PARAMETER = "entity"


def _render_fields(fields: list[dict]) -> str:
    rendered = "".join(
        f"<dt>{escape(field['name'])}</dt><dd>{escape(read_atoms(field['atoms']))}"
        f"{_render_fields(field['fields']) if field['fields'] else ''}</dd>"
        for field in fields
    )
    return f'<dl class="awawa-fields">{rendered}</dl>'


def _render_neighbours(title: str, neighbours: list[dict], address: AwawaAddress) -> str:
    items = "".join(
        f'<li><a href="{escape(address.setting(ENTITY_PARAMETER, neighbour["target"]).link())}">'
        f'{render_awawa_dot(neighbour["status"])}<span class="awawa-code">{escape(neighbour["code"])}</span>'
        f' <span class="awawa-label">{escape(neighbour["label"])}</span></a></li>'
        for neighbour in neighbours
    )
    return f'<h3>{title}</h3><ul class="awawa-neighbours">{items}</ul>'


def _render_links(document: dict) -> str:
    links = [
        f'<a href="{escape(address)}">{label}</a>'
        for address, label in (
            (document["detail"]["ide_link"], "Open in the IDE"),
            (document["awawa_web"], "Edit in awawa-web"),
        )
        if address is not None
    ]
    return f'<p class="awawa-links">{" ".join(links)}</p>' if links else ""


def render_awawa_detail(document: dict, address: AwawaAddress) -> str:
    if "detail" not in document:
        return ""
    detail = document["detail"]
    entity = detail["entity"]
    close = escape(address.removing(ENTITY_PARAMETER).link())
    return (
        '<aside class="awawa-detail"><header class="awawa-detail-head">'
        f"<h2>{render_awawa_dot(entity['status'])}{escape(entity['type'])} {escape(entity['name'])}</h2>"
        f'<a class="awawa-close" href="{close}">Close</a></header>'
        f'<p class="awawa-place">{escape(entity["file"])}:{entity["line"]}</p>'
        f"{_render_links(document)}{_render_fields(entity['fields'])}"
        f"{_render_neighbours('Refers to', detail['references'], address)}"
        f"{_render_neighbours('Referred to by', detail['referenced_by'], address)}</aside>"
    )
