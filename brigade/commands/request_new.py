import argparse

from brigade.command import Argument, Command
from brigade.commands._launch_planner import launch_planner
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.waves.record_request import NewRequest, record_request

DOCUMENT_SCHEMA_VERSION = 1
PAUSED_STATUS = "paused"


def _render_text(document: dict) -> str:
    return f"@REQUEST.{document['request']} planning, run {document['run']}\nbrigade runs show {document['run']} --log"


def _describe_diagnostics(document: dict) -> list[str]:
    return document.get("warnings", [])


def request_new(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), request.project)
    if read_project_field(project, "STATUS") == PAUSED_STATUS:
        raise BrigadeError(f"@PROJECT.{project.name} is {PAUSED_STATUS}")
    name = record_request(runtime, NewRequest(project=project.name, text=request.text))
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "request": name, **launch_planner(runtime, project.name, name)}


COMMAND = Command(
    path=("request", "new"),
    help="record a request and launch its planning",
    group_help="record the requests of the projects, list, show and cancel them",
    arguments=(
        Argument(("project",), {"help": "the registered project the request is for"}),
        Argument(("text",), {"help": "what the request asks, in the user's words"}),
    ),
    run=request_new,
    render_text=_render_text,
    describe_diagnostics=_describe_diagnostics,
)
