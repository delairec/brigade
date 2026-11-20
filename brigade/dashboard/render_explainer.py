from html import escape


def render_explainer(what: str, use: str) -> str:
    return (
        f'<aside class="explainer"><p class="explainer-what">{escape(what)}</p>'
        f'<p class="explainer-use">{escape(use)}</p></aside>'
    )
