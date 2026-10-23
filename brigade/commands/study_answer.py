import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.study_run_context import ANSWER_FILE
from brigade.studies.validate_answer import validate_answer
from brigade.system.read_text_file import read_text_file
from brigade.system.write_text_atomically import write_text_atomically

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"the answer of run {document['run']} recorded"


def study_answer(request: argparse.Namespace, runtime: Runtime) -> dict:
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / request.run
    study = read_study_of_run(runtime, run_directory)
    answer = read_text_file(Path(request.file))
    validate_answer(runtime, study, run_directory, answer)
    write_text_atomically(run_directory / ANSWER_FILE, answer)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "run": request.run, "answer": str(run_directory / ANSWER_FILE)}


COMMAND = Command(
    path=("study", "answer"),
    help="validate the answer of a judging run against the schema of its type and record it",
    arguments=(
        Argument(("run",), {"help": "the run of the study"}),
        Argument(("--file",), {"required": True, "help": "the file holding the answer entity"}),
    ),
    run=study_answer,
    render_text=_render_text,
)
