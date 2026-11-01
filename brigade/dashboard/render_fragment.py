from html import escape


def render_fragment(document: object) -> str:
    if isinstance(document, dict):
        fields = "".join(
            f"<dt>{escape(str(name))}</dt><dd>{render_fragment(value)}</dd>" for name, value in document.items()
        )
        return f"<dl>{fields}</dl>"
    if isinstance(document, list):
        return f"<ol>{''.join(f'<li>{render_fragment(item)}</li>' for item in document)}</ol>"
    return escape(str(document))
