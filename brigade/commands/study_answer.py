from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.study_run_context import ANSWER_FILE
from brigade.studies.validate_answer import validate_answer
from brigade.system.write_text_atomically import write_text_atomically

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"the answer of run {document['run']} recorded"


def _read_answer(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise BrigadeError(f"cannot read {path}: {error.strerror}") from None


def study_answer(request, runtime: Runtime) -> dict:
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / request.run
    study = read_study_of_run(runtime, run_directory)
    answer = _read_answer(Path(request.file))
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
