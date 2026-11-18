from html import escape


def render_empty_state(why: str, what_would_fill: str) -> str:
    return (
        f'<div class="empty-state"><p class="empty-why">{escape(why)}</p>'
        f'<p class="empty-fill">{escape(what_would_fill)}</p></div>'
    )
