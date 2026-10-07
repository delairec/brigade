from brigade.command import Command
from brigade.corpus.read_entities import Entity
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
NO_VALUE = ""
NO_PROJECT = "no project registered"
COLUMNS = ("name", "status", "path")


def _read_field(project: Entity, name: str) -> str:
    return next((field.value for field in project.fields if field.name == name), NO_VALUE)


def _render_text(document: dict) -> str:
    projects = document["projects"]
    if not projects:
        return NO_PROJECT
    return render_table(COLUMNS, [tuple(project[column] for column in COLUMNS) for project in projects])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def project_list(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths.config_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "projects": [
            {"name": project.name, "path": _read_field(project, "PATH"), "status": _read_field(project, "STATUS")}
            for project in read_projects(runtime)
        ],
    }


COMMAND = Command(
    path=("project", "list"),
    help="list every registered project",
    group_help="register the projects brigade works on, list and show them",
    run=project_list,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
