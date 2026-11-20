from html import escape

from brigade.dashboard.read_lifecycle_tone import read_lifecycle_tone

NO_STATUS = "no status"


def render_awawa_dot(status: str | None) -> str:
    title = NO_STATUS if status is None else status
    return f'<span class="dot tone-{read_lifecycle_tone(status)}" title="{escape(title)}"></span>'
