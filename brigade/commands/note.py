import argparse

from brigade.command import Argument, Command
from brigade.corpus.read_entities import Entity
from brigade.inbox.fingerprint_note import fingerprint_note
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.name_signal import name_signal
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
NOTE_KIND = "note"
NO_REGISTERED_PROJECT: tuple[Entity, ...] = ()


def _render_text(document: dict) -> str:
    return f"recorded {document['signal'][:SHOWN_ID_LENGTH]} {document['fingerprint']}"


def _read_registered_projects(runtime: Runtime) -> tuple[Entity, ...]:
    if not runtime.paths.schema_file.exists():
        return NO_REGISTERED_PROJECT
    return read_projects(runtime)


def note(request: argparse.Namespace, runtime: Runtime) -> dict:
    if request.project is not None:
        find_project(_read_registered_projects(runtime), request.project)
    fingerprint = fingerprint_note(request.project, request.text)
    record_signal(
        runtime.paths,
        runtime.now,
        NewSignal(kind=NOTE_KIND, project=request.project, fingerprint=fingerprint, evidence={"text": request.text}),
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "signal": name_signal(fingerprint), "fingerprint": fingerprint}


COMMAND = Command(
    path=("note",),
    help="record a note in the inbox",
    arguments=(
        Argument(("text",), {"help": "the note"}),
        Argument(("--project",), {"help": "the registered project the note is about"}),
    ),
    run=note,
    render_text=_render_text,
)
