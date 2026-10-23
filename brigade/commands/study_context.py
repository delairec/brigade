from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.studies.build_study_context import build_study_context
from brigade.system.render_inline_json import render_inline_json

PROSE_FIELD_SEPARATOR = ", "


def _render_collected(entry: dict) -> str:
    return f"{entry['collector']}: {render_inline_json(entry['summary'])}, {entry['document']}"


def _render_text(document: dict) -> str:
    head = [
        f"question: {document['question']}",
        *(_render_collected(entry) for entry in document["collected"]),
        f"prose fields left to the slot: {PROSE_FIELD_SEPARATOR.join(document['prose_fields'])}",
    ]
    return "\n\n".join(("\n".join(head), document["answer"].rstrip("\n"), document["schema"].rstrip("\n")))


def study_context(request, runtime: Runtime) -> dict:
    return build_study_context(runtime, request.run)


COMMAND = Command(
    path=("study", "context"),
    help="print the package a judging run answers from, and write it to the run directory",
    arguments=(Argument(("run",), {"help": "the run of the study"}),),
    run=study_context,
    render_text=_render_text,
)
