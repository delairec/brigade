import argparse
import functools
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.commands._resolve_project_forge import resolve_project_forge
from brigade.errors import BrigadeError
from brigade.planning.read_planning_request import read_planning_request
from brigade.planning.record_plan import PlanRecording, record_plan
from brigade.registry.find_project import find_project
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"recorded @REQUEST.{document['request']} as @MILESTONE.{document['milestone']} on {document['branch']}"


def plan_record(request: argparse.Namespace, runtime: Runtime) -> dict:
    planning_request = read_planning_request(runtime, request.request)
    project = find_project(read_projects(runtime), planning_request.project)
    read_corpus_workspace(project)
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    forge_name = read_project_forge(project)
    recording = PlanRecording(
        request=planning_request,
        project=project,
        plan_file=Path(request.file).absolute(),
        forge=resolve_project_forge(project, runtime),
        read_environment=functools.cache(
            lambda key: read_forge_environment(configuration, ForgeSlot(forge_name, key), runtime)
        ),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **record_plan(runtime, recording)}


COMMAND = Command(
    path=("plan", "record"),
    help="record the plan of a request, one MILESTONE and its tasks, on plan/<request> and deliver it to the main branch",
    arguments=(Argument(("request",)), Argument(("--file",), {"required": True})),
    run=plan_record,
    render_text=_render_text,
)
