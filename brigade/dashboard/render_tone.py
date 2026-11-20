from html import escape

from brigade.dashboard.read_state_tone import read_state_tone

TONE_SHAPES = {
    "you": "▲",
    "work": "●",
    "review": "◆",
    "done": "✓",
    "limit": "■",
    "failed": "✕",
    "off": "○",
    "faint": "·",
}


def render_tone(state: str) -> str:
    tone = read_state_tone(state)
    shape = f'<span class="tone-shape" aria-hidden="true">{TONE_SHAPES[tone]}</span>'
    return f'<span class="tone tone-{tone}">{shape}{escape(state)}</span>'
