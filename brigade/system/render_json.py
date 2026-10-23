import json

INDENT = 2


def render_json(document: object) -> str:
    return json.dumps(document, indent=INDENT)
