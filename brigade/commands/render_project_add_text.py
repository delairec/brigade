FIELD_NAME_WIDTH = 12
GUESSED_MARK = "  (guessed)"
NO_CONFIGURATION = "no supported configuration was found"


def _render_field(field: dict) -> str:
    mark = GUESSED_MARK if field["guessed"] else ""
    return f"{field['name']:<{FIELD_NAME_WIDTH}}{field['value']}{mark}"


def render_project_add_text(document: dict) -> str:
    project = document["project"]
    lines = [
        f"{document['action']} @PROJECT.{project['name']}",
        *(_render_field(field) for field in project["fields"]),
    ]
    if not document["configurations"]:
        lines.append(NO_CONFIGURATION)
    return "\n".join(lines)
