import argparse
import dataclasses

from brigade.command import Argument, Command
from brigade.inbox.find_signal import find_signal
from brigade.inbox.read_inbox import read_inbox
from brigade.inbox.render_age import render_age
from brigade.runtime import Runtime
from brigade.system.render_inline_json import render_inline_json

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 13
NO_PROJECT = "-"


def _render_evidence_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return render_inline_json(value)


def _render_text(document: dict) -> str:
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
    signal = find_signal(read_inbox(runtime.paths.state_root, runtime.now), request.id)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "signal": dataclasses.asdict(signal)}


COMMAND = Command(
    path=("inbox", "show"),
    help="print a signal with its evidence",
    arguments=(Argument(("id",), {"help": "the id of the signal, 4 characters or more"}),),
    run=inbox_show,
    render_text=_render_text,
)
