from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


def render_callout(state: str, text: str) -> str:
    return f'<div class="callout tone-{read_state_tone(state)}"><p>{escape(text)}</p></div>'
