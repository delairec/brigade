NO_PROJECT = "no project registered"


def render_project_list_text(document: dict) -> str:
    projects = document["projects"]
    if not projects:
        return NO_PROJECT
    name_width = max(len(project["name"]) for project in projects)
    return "\n".join(f"{project['name']:<{name_width}}  {project['status']}  {project['path']}" for project in projects)
