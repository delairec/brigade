from html import escape

SELECTED = " selected"


def _render_option(name: str, chosen: str | None) -> str:
    selected = SELECTED if name == chosen else ""
    return f'<option value="{escape(name)}"{selected}>{escape(name)}</option>'


def render_project_selector(document: dict, chosen: str | None) -> str:
    projects = document["projects"]
    options = "".join(_render_option(project["name"], chosen) for project in projects)
    return (
        '<label for="project">Project</label><select id="project" name="project">'
        f'<option value="">All projects ({len(projects)})</option>{options}</select>'
    )
