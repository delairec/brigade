import json

TEXT_INDENT = 2


def render_adapter_text(document: dict) -> str:
    return json.dumps(document, indent=TEXT_INDENT)
