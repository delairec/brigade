from html import escape


def render_status_sentence(sentence: str) -> str:
    return f'<p class="status-sentence">{escape(sentence)}</p>'
