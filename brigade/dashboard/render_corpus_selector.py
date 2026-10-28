from html import escape
from urllib.parse import quote

TYPES_LIST = ' list="corpus-types"'


def _render_input(label: str, name: str, value: str | None, extra: str = "") -> str:
    return f'<label>{label} <input name="{name}"{extra} value="{escape(value or "")}"></label>'


def render_corpus_selector(selection: dict) -> str:
    view = f"corpus/{quote(selection['project'], safe='')}"
    types = "".join(f'<option value="{escape(entity_type)}"></option>' for entity_type in selection.get("types", ()))
    return (
        f'<form class="corpus-selector" data-view="{escape(view)}" method="get">'
        f"{_render_input('ref', 'ref', selection.get('ref'))}"
        f"{_render_input('type', 'type', selection.get('type'), TYPES_LIST)}"
        f'<datalist id="corpus-types">{types}</datalist>'
        f"{_render_input('board field', 'field', selection.get('field'))}"
        "<button>read</button></form>"
    )
