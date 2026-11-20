from html import escape


def render_status_sentence(sentence: str) -> str:
    return f'<div class="verdict"><p class="status-sentence">{escape(sentence)}</p></div>'
