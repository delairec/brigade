from html import escape


def _render_row(tag: str, cells: tuple[str, ...]) -> str:
    return f"<tr>{''.join(f'<{tag}>{cell}</{tag}>' for cell in cells)}</tr>"


def render_html_table(header: tuple[str, ...], rows: list[tuple[str, ...]], empty: str) -> str:
    if not rows:
        return f"<p>{escape(empty)}</p>"
    body = "".join(_render_row("td", row) for row in rows)
    return f"<table><thead>{_render_row('th', header)}</thead><tbody>{body}</tbody></table>"
