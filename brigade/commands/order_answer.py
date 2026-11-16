import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.orders.read_order_run import read_order_run
from brigade.recipes.validate_result import validate_result
from brigade.runtime import Runtime
from brigade.studies.study_run_context import ANSWER_FILE
from brigade.system.read_text_file import read_text_file
from brigade.system.write_text_atomically import write_text_atomically

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    return f"the answer of run {document['run']} recorded"


def order_answer(request: argparse.Namespace, runtime: Runtime) -> dict:
    run = read_order_run(runtime, request.run)
    answer = read_text_file(Path(request.file))
    validate_result(runtime, run, answer)
    write_text_atomically(run.run_directory / ANSWER_FILE, answer)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": request.run,
        "answer": str(run.run_directory / ANSWER_FILE),
    }


COMMAND = Command(
    path=("order", "answer"),
    help="validate the answer of the judge step of a run of an order against the schema it names and record it",
    arguments=(
        Argument(("run",), {"help": "the run of the order"}),
        Argument(("--file",), {"required": True, "help": "the file holding the answer entity"}),
    ),
    run=order_answer,
    render_text=_render_text,
)
