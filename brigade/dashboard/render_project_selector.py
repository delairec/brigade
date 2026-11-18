from html import escape

SELECTED = " selected"


def _render_option(name: str, chosen: str | None) -> str:
    selected = SELECTED if name == chosen else ""
    return f'<option value="{escape(name)}"{selected}>{escape(name)}</option>'


def render_project_selector(document: dict, chosen: str | None) -> str:
    options = "".join(_render_option(project["name"], chosen) for project in document["projects"])
    return (
        f'<label>Project <select name="project"><option value="">All projects</option>{options}</select></label>'
        "<button>show</button>"
    )
