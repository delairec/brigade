from html import escape


def render_details(summary: str, content_html: str) -> str:
    return f"<details><summary>{escape(summary)}</summary>{content_html}</details>"
