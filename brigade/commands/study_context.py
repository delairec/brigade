import json

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.studies.build_study_context import build_study_context

PROSE_FIELD_SEPARATOR = ", "


def _read_request(options):
    return options


def _render_collected(entry: dict) -> str:
    return f"{entry['collector']}: {json.dumps(entry['summary'])}, {entry['document']}"


def _render_text(document: dict) -> str:
    head = [
        f"question: {document['question']}",
        *(_render_collected(entry) for entry in document["collected"]),
        f"prose fields left to the slot: {PROSE_FIELD_SEPARATOR.join(document['prose_fields'])}",
    ]
    return "\n\n".join(("\n".join(head), document["answer"].rstrip("\n"), document["schema"].rstrip("\n")))


def _decide_exit_code(document: dict) -> int:
    return 0


def study_context(request, runtime: Runtime) -> dict:
    return build_study_context(runtime, request.run)


COMMAND = Command(
    path=("study", "context"),
    help="print the package a judging run answers from, and write it to the run directory",
    arguments=(Argument(("run",), {"help": "the run of the study"}),),
    run=study_context,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
