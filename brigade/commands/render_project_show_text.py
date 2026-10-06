FIELD_NAME_WIDTH = 12


def render_project_show_text(document: dict) -> str:
    project = document["project"]
    lines = [
        f"@PROJECT.{project['name']}",
        *(f"{field['name']:<{FIELD_NAME_WIDTH}}{field['value']}" for field in project["fields"]),
    ]
    return "\n".join(lines)
