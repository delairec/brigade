import argparse

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME
from brigade.runtime import Runtime
from brigade.studies.read_study import read_study
from brigade.studies.run_study import DONE, run_study
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.collector_places import locate_collectors
from brigade.system.read_optional_configuration import read_optional_configuration

DOCUMENT_SCHEMA_VERSION = 1
PARKED_EXIT_CODE = 1
COLLECTOR_KIND = "collector"
DOCUMENT_KIND = "document"
ANSWER_DOCUMENT = "awawa"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    if document["state"] == DONE:
        return f"@STUDY.{document['study']} run {document['run']} done"
    return f"@STUDY.{document['study']} run {document['run']} parked at {document['step']}: {document['reason']}"


def _decide_exit_code(document: dict) -> int:
    if document["state"] == DONE:
        return 0
    return PARKED_EXIT_CODE


def study_run(request, runtime: Runtime) -> dict:
    equipment = StudyEquipment(
        collector_equipment=CollectorEquipment(
            configuration=read_optional_configuration(runtime.paths.configuration_file),
            forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME),
            forge_name=FORGE_NAME,
        ),
        resolve_collector=lambda name, project: runtime.resolve_plugin(
            COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths)
        ),
        document=runtime.resolve_plugin(DOCUMENT_KIND, ANSWER_DOCUMENT),
        resolve_forge=lambda name: runtime.resolve_plugin(FORGE_KIND, name),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **run_study(runtime, read_study(runtime, request.name), equipment, request.run_id),
    }


COMMAND = Command(
    path=("study", "run"),
    help="run a study: its collectors, its judging run, its output; resume it where it parked",
    arguments=(
        Argument(("name",), {"help": "the name of the STUDY entity"}),
        Argument(("--run-id",), {"help": argparse.SUPPRESS}),
    ),
    run=study_run,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
