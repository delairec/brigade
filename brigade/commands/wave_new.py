import argparse

from brigade.command import Argument, Command
from brigade.commands.run import run
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.waves.record_request import NewRequest, record_request

DOCUMENT_SCHEMA_VERSION = 1
PAUSED_STATUS = "paused"
PLANNER_PROCEDURE = "wave-plan"
PLANNER_SLOT = "plan"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return f"@REQUEST.{document['request']} planning, run {document['run']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def _describe_diagnostics(document: dict) -> list[str]:
    return document.get("warnings", [])


def _launch_planner(runtime: Runtime, project: str, name: str) -> dict:
    planning = argparse.Namespace(
        procedure=PLANNER_PROCEDURE,
        slot=PLANNER_SLOT,
        project=project,
        cwd=None,
        brief=None,
        arguments=(f"request={name}",),
        run_id=None,
        detach=True,
    )
    return run(planning, runtime)


def wave_new(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), request.project)
    if read_project_field(project, "STATUS") == PAUSED_STATUS:
        raise BrigadeError(f"@PROJECT.{project.name} is {PAUSED_STATUS}")
    name = record_request(runtime, NewRequest(project=project.name, text=request.text))
    launched = _launch_planner(runtime, project.name, name)
    document = {"schema_version": DOCUMENT_SCHEMA_VERSION, "request": name, "run": launched["run"]}
    if "warnings" not in launched:
        return document
    return {**document, "warnings": launched["warnings"]}


COMMAND = Command(
    path=("wave", "new"),
    help="record a request and launch its planning",
    group_help="record the requests of the projects, start their waves, list and show them",
    arguments=(
        Argument(("project",), {"help": "the registered project the request is for"}),
        Argument(("text",), {"help": "what the request asks, in the user's words"}),
    ),
    run=wave_new,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=_describe_diagnostics,
)
