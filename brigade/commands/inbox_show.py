import argparse
import dataclasses

from brigade.command import Argument, Command
from brigade.inbox.find_signal import find_signal
from brigade.inbox.read_inbox import read_inbox
from brigade.inbox.read_study_answers import read_study_answers
from brigade.inbox.render_age import render_age
from brigade.reports.render_report_markdown import render_report_markdown
from brigade.runtime import Runtime
from brigade.system.render_inline_json import render_inline_json

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "progress_form"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
FIELD_NAME_WIDTH = 13
NO_PROJECT = "-"
ANSWER_KEY = "answer"


def _render_evidence_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return render_inline_json(value)


def _render_text(document: dict) -> str:
    if ANSWER_KEY in document:
        answer = document[ANSWER_KEY]
        return render_report_markdown({"type": answer["type"], "name": answer["id"], "fields": answer["fields"]})
    signal = document["signal"]
    fields = (
        ("id", signal["id"]),
        ("fingerprint", signal["fingerprint"]),
        ("kind", signal["kind"]),
        ("project", signal["project"] or NO_PROJECT),
        ("count", str(signal["count"])),
        ("age", render_age(signal["age_s"])),
        ("status", signal["status"]),
    )
    return "\n".join(
        [
            *(f"{name:<{FIELD_NAME_WIDTH}}{value}" for name, value in fields),
            "evidence",
            *(f"  {key}: {_render_evidence_value(value)}" for key, value in signal["evidence"].items()),
        ]
    )


def inbox_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    answer = next(
        (
            answer
            for answer in read_study_answers(
                runtime, lambda: runtime.resolve_plugin(DOCUMENT_KIND, OPERATIONAL_CORPUS_DOCUMENT)
            )
            if answer["id"] == request.id
        ),
        None,
    )
    if answer is not None:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, ANSWER_KEY: answer}
    signal = find_signal(read_inbox(runtime.paths.state_root, runtime.now), request.id)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "signal": dataclasses.asdict(signal)}


COMMAND = Command(
    path=("inbox", "show"),
    help="print a signal with its evidence, or a study answer rendered from its entity",
    arguments=(Argument(("id",), {"help": "the id of the signal, 4 characters or more, or of the study answer"}),),
    run=inbox_show,
    render_text=_render_text,
)
