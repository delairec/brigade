from brigade.command import Argument, Command
from brigade.commands._launch_planner import launch_planner
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.waves.describe_request import describe_request
from brigade.waves.read_planner_run import read_planner_run
from brigade.waves.read_wave_request import read_wave_request

DOCUMENT_SCHEMA_VERSION = 1
PLANNING_STATUS = "planning"
PAUSED_STATUS = "paused"
LIVE_STATE = "live"


def _render_text(document: dict) -> str:
    return f"@REQUEST.{document['request']} planning, run {document['run']}\nbrigade runs show {document['run']} --log"


def _describe_diagnostics(document: dict) -> list[str]:
    return document.get("warnings", [])


def _refuse_a_live_planner(runtime: Runtime, name: str) -> None:
    planner = read_planner_run(runtime.paths.state_root, name)
    if planner is not None and planner["state"] == LIVE_STATE:
        raise BrigadeError(f"@REQUEST.{name} has its planner run {planner['run']} {LIVE_STATE}")


def request_replan(request, runtime: Runtime) -> dict:
    described = describe_request(read_wave_request(runtime, request.request))
    name = described["name"]
    if described["status"] != PLANNING_STATUS:
        raise BrigadeError(f"@REQUEST.{name} is {described['status']}")
    _refuse_a_live_planner(runtime, name)
    project = find_project(read_projects(runtime), described["project"])
    if read_project_field(project, "STATUS") == PAUSED_STATUS:
        raise BrigadeError(f"@PROJECT.{project.name} is {PAUSED_STATUS}")
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "request": name, **launch_planner(runtime, project.name, name)}


COMMAND = Command(
    path=("request", "replan"),
    help="relaunch the planner of a planning request whose planner run is no longer live",
    arguments=(Argument(("request",), {"help": "the name of a REQUEST planning"}),),
    run=request_replan,
    render_text=_render_text,
    describe_diagnostics=_describe_diagnostics,
)
