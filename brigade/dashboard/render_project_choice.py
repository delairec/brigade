from html import escape
from urllib.parse import quote


def _render_project_link(project: str) -> str:
    view = f"#corpus/{quote(project, safe='')}"
    return f'<li><a href="{escape(view)}">{escape(project)}</a></li>'


def render_project_choice(document: dict) -> str:
    return f"<ul>{''.join(_render_project_link(project['name']) for project in document['projects'])}</ul>"
