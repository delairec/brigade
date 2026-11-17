import argparse

from brigade.command import Argument, Command
from brigade.commands._equip_study import equip_study
from brigade.commands._find_study_project import find_study_project
from brigade.recipes.run_order import DONE
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_study import Study, read_study
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.run_study import run_study

DOCUMENT_SCHEMA_VERSION = 1
PARKED_EXIT_CODE = 1
CLIENT_KIND = "client"
COLLECTOR_KIND = "collector"
DOCUMENT_KIND = "progress_form"
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
    study = _read_study_of_request(request, runtime)
    project = find_study_project(study, runtime)
    equipment = equip_study(project, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **run_study(runtime, study, equipment, request.run_id),
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
