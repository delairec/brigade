import functools
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME, read_forge_environment
from brigade.errors import BrigadeError
from brigade.planning.read_planning_request import read_planning_request
from brigade.planning.record_plan import PlanRecording, record_plan
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"recorded @REQUEST.{document['request']} as @MILESTONE.{document['milestone']} on {document['branch']}"


def plan_record(request, runtime: Runtime) -> dict:
    planning_request = read_planning_request(runtime, request.request)
    project = find_project(read_projects(runtime), planning_request.project)
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    configuration = read_configuration(runtime.paths.configuration_file)
    recording = PlanRecording(
        request=planning_request,
        project=project,
        plan_file=Path(request.file).absolute(),
        forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME),
        read_environment=functools.cache(lambda key: read_forge_environment(configuration, key, runtime)),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_plan(runtime, recording)}


COMMAND = Command(
    path=("plan", "record"),
    help="record the plan of a request, one MILESTONE and its tasks, on plan/<request> and deliver it to the main branch",
    arguments=(Argument(("request",)), Argument(("--file",), {"required": True})),
    run=plan_record,
    render_text=_render_text,
)
