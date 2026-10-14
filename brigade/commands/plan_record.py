from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.planning.read_planning_request import read_planning_request
from brigade.planning.record_plan import PlanRecording, record_plan
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return f"recorded @REQUEST.{document['request']} as @MILESTONE.{document['milestone']} on {document['branch']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def plan_record(request, runtime: Runtime) -> dict:
    planning_request = read_planning_request(runtime, request.request)
    project = find_project(read_projects(runtime), planning_request.project)
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    recording = PlanRecording(request=planning_request, project=project, plan_file=Path(request.file).absolute())
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_plan(runtime, recording)}


COMMAND = Command(
    path=("plan", "record"),
    help="record the plan of a wave, one MILESTONE and its tasks, on its integration branch",
    arguments=(Argument(("request",)), Argument(("--file",), {"required": True})),
    run=plan_record,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
