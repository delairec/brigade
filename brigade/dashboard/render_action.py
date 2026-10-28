from html import escape
from urllib.parse import quote


def render_action(segments: tuple[str, ...], label: str) -> str:
    action = "/api/" + "/".join(quote(segment, safe="") for segment in segments)
    return f' <button type="button" data-post="{escape(action)}">{escape(label)}</button>'
