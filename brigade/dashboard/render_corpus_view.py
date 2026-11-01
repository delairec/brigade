from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.render_corpus_selector import render_corpus_selector

KEPT_SELECTION = ("ref", "type", "field")


def _link_dependencies(target: str, document: dict) -> str:
    selection = {name: document[name] for name in KEPT_SELECTION if document.get(name)}
    return f"#corpus/{quote(document['project'], safe='')}?{urlencode(selection | {'entity': target})}"


def _render_line(entity: dict) -> str:
    place = escape(f"{entity['file']}:{entity['line']}")
    if entity["ide_link"] is None:
        return place
    return f'<a href="{escape(entity["ide_link"])}">{place}</a>'


def _render_entity(entity: dict, document: dict) -> str:
    awawa_web = document["awawa_web"]
    editor = "" if awawa_web is None else f' <a href="{escape(awawa_web)}">awawa-web</a>'
    return (
        f'<li><a href="{escape(_link_dependencies(entity["target"], document))}">{escape(entity["target"])}</a>'
        f" {escape(str(entity['status']))} {_render_line(entity)}{editor}</li>"
    )


def _render_targets(targets: list[str]) -> str:
    return "".join(f"<li>{escape(target)}</li>" for target in targets)


def _render_tree(document: dict) -> str:
    entities = "".join(_render_entity(entity, document) for entity in document["entities"])
    return f'<section class="tree"><h2>{escape(document["type"])}</h2><ul>{entities}</ul></section>'


def _render_board(document: dict) -> str:
    field = escape(document["field"])
    columns = "".join(
        f"<div><h3>{escape(column['value']) if column['value'] is not None else f'no {field}'}</h3>"
        f"<ul>{_render_targets(column['targets'])}</ul></div>"
        for column in document["board"]
    )
    return f'<section class="board"><h2>{field}</h2>{columns}</section>'


def _render_dependencies(document: dict) -> str:
    dependencies = document["dependencies"]
    reached = "".join(_render_entity(entity, document) for entity in dependencies["reaches"])
    return (
        f'<section class="dependencies"><h2>{escape(dependencies["entity"])}</h2>'
        f"<h3>reaches</h3><ul>{reached}</ul>"
        f"<h3>referenced by</h3><ul>{_render_targets(dependencies['referenced_by'])}</ul></section>"
    )


def render_corpus_view(document: dict) -> str:
    return "".join(
        (
            render_corpus_selector(document),
            f"<p>{escape(document['project'])} {escape(document['sha'])}</p>",
            _render_tree(document) if "entities" in document else "",
            _render_board(document) if "board" in document else "",
            _render_dependencies(document) if "dependencies" in document else "",
        )
    )
