import argparse
import dataclasses

from brigade.command import Argument, Command
from brigade.corpus.read_entities import Entity
from brigade.inbox.find_signal import find_signal
from brigade.inbox.read_inbox import read_inbox
from brigade.inbox.read_proposed_patterns import read_proposed_patterns
from brigade.inbox.read_study_answers import read_study_answers
from brigade.inbox.render_age import render_age
from brigade.registry.read_project_field import read_project_field
from brigade.reports.render_report_markdown import render_report_markdown
from brigade.runtime import Runtime
from brigade.system.render_inline_json import render_inline_json

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "progress_form"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
FIELD_NAME_WIDTH = 13
NO_PROJECT = "-"
ANSWER_KEY = "answer"
PATTERN_KEY = "pattern"
NO_TARGET = "-"
EVIDENCE_FIELD = "EVIDENCE"


def _render_evidence_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return render_inline_json(value)


def _render_pattern(pattern: dict) -> str:
    fields = (
        ("pattern", pattern["name"]),
        ("title", pattern["title"]),
        ("action", pattern["action"] or NO_TARGET),
        ("target", pattern["target"] or NO_TARGET),
    )
    return "\n".join(
        [
            *(f"{name:<{FIELD_NAME_WIDTH}}{value}" for name, value in fields),
            "evidence",
            *(f"  {evidence}" for evidence in pattern["evidence"]),
        ]
    )


def _describe_pattern(pattern: Entity) -> dict:
    return {
        "name": pattern.name,
        "title": read_project_field(pattern, "TITLE"),
        "action": read_project_field(pattern, "ACTION"),
        "target": read_project_field(pattern, "TARGET"),
        "evidence": [field.value for field in pattern.fields if field.name == EVIDENCE_FIELD],
    }


def _render_text(document: dict) -> str:
    if ANSWER_KEY in document:
        answer = document[ANSWER_KEY]
        return render_report_markdown({"type": answer["type"], "name": answer["id"], "fields": answer["fields"]})
    if PATTERN_KEY in document:
        return _render_pattern(document[PATTERN_KEY])
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
    pattern = next((pattern for pattern in read_proposed_patterns(runtime) if pattern.name == request.id), None)
    if pattern is not None:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, PATTERN_KEY: _describe_pattern(pattern)}
    signal = find_signal(read_inbox(runtime.paths.state_root, runtime.now), request.id)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "signal": dataclasses.asdict(signal)}


COMMAND = Command(
    path=("inbox", "show"),
    help="print a signal with its evidence, a proposed pattern with its evidence, or a study answer rendered from its entity",
    arguments=(
        Argument(
            ("id",),
            {
                "help": "the id of the signal, 4 characters or more, the name of the proposed pattern, or the id of the study answer"
            },
        ),
    ),
    run=inbox_show,
    render_text=_render_text,
)
