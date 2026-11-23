from html import escape


def render_field(label: str, name: str, control: str) -> str:
    return f'<span class="field"><label for="{escape(name)}">{escape(label)}</label>{control}</span>'
