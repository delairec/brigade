import argparse
import functools
import os
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME
from brigade.commands.run import run
from brigade.runs.create_run_id import create_run_id
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_study import Study, read_study
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.run_study import DONE, run_study
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.collector_places import locate_collectors
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
PARKED_EXIT_CODE = 1
COLLECTOR_KIND = "collector"
DOCUMENT_KIND = "document"
ANSWER_DOCUMENT = "awawa"


def _render_text(document: dict) -> str:
    if document["state"] == DONE:
        return f"@STUDY.{document['study']} run {document['run']} done"
    return f"@STUDY.{document['study']} run {document['run']} parked at {document['step']}: {document['reason']}"


def _decide_exit_code(document: dict) -> int:
    if document["state"] == DONE:
        return 0
    return PARKED_EXIT_CODE


def _read_study_of_request(request: argparse.Namespace, runtime: Runtime) -> Study:
    if request.run_id is None:
        return read_study(runtime, request.name)
    return read_study_of_run(runtime, runtime.paths.state_root / RUNS_DIRECTORY / request.run_id)


def study_run(request: argparse.Namespace, runtime: Runtime) -> dict:
    equipment = StudyEquipment(
        collector_equipment=CollectorEquipment(
            configuration=read_configuration(runtime, CONFIGURATION_OPTIONAL),
            forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME),
            forge_name=FORGE_NAME,
        ),
        resolve_collector=lambda name, project: runtime.resolve_plugin(
            COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths)
        ),
        document=runtime.resolve_plugin(DOCUMENT_KIND, ANSWER_DOCUMENT),
        resolve_forge=lambda name: runtime.resolve_plugin(FORGE_KIND, name),
        launch_run=run,
        name_run=create_run_id,
        working_directory=Path.cwd(),
        is_run_alive=is_recorded_process_alive,
        record_own_pid=functools.partial(record_run_pid, pid=os.getpid()),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **run_study(runtime, _read_study_of_request(request, runtime), equipment, request.run_id),
    }


COMMAND = Command(
    path=("study", "run"),
    help="run a study: its collectors, its judging run, its output; resume it where it parked",
    arguments=(
        Argument(("name",), {"help": "the name of the STUDY entity"}),
        Argument(("--run-id",), {"help": argparse.SUPPRESS}),
    ),
    run=study_run,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
