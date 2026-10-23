import json


def render_inline_json(value: object) -> str:
    return json.dumps(value)
