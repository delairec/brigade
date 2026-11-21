from html import escape


def render_key_values(pairs: tuple[tuple[str, str], ...]) -> str:
    facts = "".join(f"<div><dt>{escape(name)}</dt><dd>{value}</dd></div>" for name, value in pairs)
    return f'<dl class="panel pad kv">{facts}</dl>'
