from brigade.command import Argument, Command
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 12


def _render_text(document: dict) -> str:
    project = document["project"]
    lines = [
        f"@PROJECT.{project['name']}",
        *(f"{field['name']:<{FIELD_NAME_WIDTH}}{field['value']}" for field in project["fields"]),
    ]
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def project_show(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), request.name)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": {
            "name": project.name,
            "fields": [{"name": field.name, "value": field.value} for field in project.fields],
        },
    }


COMMAND = Command(
    path=("project", "show"),
    help="print the fields of a project",
    group_help="register the projects brigade works on, list and show them",
    arguments=(Argument(("name",)),),
    run=project_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
