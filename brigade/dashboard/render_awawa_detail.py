from html import escape

from brigade.corpus.corpus_reader import read_atoms
from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_dot import render_awawa_dot
from brigade.dashboard.render_fold import Fold, render_fold

ENTITY_PARAMETER = "entity"
TITLE_FIELD = "TITLE"
TEXT_FIELDS = ("SPEC", "RATIONALE", "SOURCE")
TEXT_FIELDS_DETAIL = "the text fields"


def _render_field_rows(fields: list[dict]) -> str:
    return "".join(
        f"<dt>{escape(field['name'])}</dt><dd>{escape(read_atoms(field['atoms']))}"
        f"{_render_fields(field['fields']) if field['fields'] else ''}</dd>"
        for field in fields
    )


def _render_fields(fields: list[dict]) -> str:
    return f'<dl class="awawa-fields">{_render_field_rows(fields)}</dl>'


def _render_key_facts(entity: dict) -> str:
    facts = [field for field in entity["fields"] if field["name"] not in (TITLE_FIELD, *TEXT_FIELDS)]
    place = f'<dt>written at</dt><dd class="mono">{escape(entity["file"])}:{entity["line"]}</dd>'
    return f'<dl class="awawa-fields">{_render_field_rows(facts)}{place}</dl>'


def _render_text_fields(entity: dict) -> str:
    texts = [field for field in entity["fields"] if field["name"] in TEXT_FIELDS]
    if not texts:
        return ""
    named = ", ".join(name for name in TEXT_FIELDS if any(field["name"] == name for field in texts))
    return render_fold(Fold(summary=named, detail=TEXT_FIELDS_DETAIL, body=_render_fields(texts)))


def _read_title(entity: dict) -> str:
    title = next((field for field in entity["fields"] if field["name"] == TITLE_FIELD), None)
    return "" if title is None else f" {escape(read_atoms(title['atoms']))}"


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
        '<aside class="awawa-detail"><header class="awawa-detail-head"><div>'
        f'<p class="eyebrow">{escape(entity["type"].replace("_", " ").capitalize())} · {escape(entity["status"])}</p>'
        f'<h2>{render_awawa_dot(entity["status"])}<span class="mono">{escape(entity["name"])}</span>{_read_title(entity)}</h2>'
        f'</div><a class="awawa-close" href="{close}">Close</a></header>'
        f"{_render_key_facts(entity)}{_render_text_fields(entity)}{_render_links(document)}"
        f"{_render_neighbours('Refers to', detail['references'], address)}"
        f"{_render_neighbours('Referred to by', detail['referenced_by'], address)}</aside>"
    )
