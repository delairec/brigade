import argparse

from brigade.command import Argument, Command
from brigade.inbox.dismiss_signal import dismiss_signal
from brigade.inbox.find_signal import find_signal
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.read_inbox import DISMISSED_STATUS, read_inbox
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    named = f"{document['signal'][:SHOWN_ID_LENGTH]} {document['fingerprint']}"
    if document["changed"]:
        return f"dismissed {named}"
    return f"{named} is already dismissed"


def inbox_dismiss(request: argparse.Namespace, runtime: Runtime) -> dict:
    signal = find_signal(read_inbox(runtime.paths.state_root, runtime.now), request.id)
    changed = signal.status != DISMISSED_STATUS
    if changed:
        dismiss_signal(runtime.paths, runtime.now, signal)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "signal": signal.id,
        "fingerprint": signal.fingerprint,
        "changed": changed,
    }


COMMAND = Command(
    path=("inbox", "dismiss"),
    help="dismiss a signal",
    arguments=(Argument(("id",), {"help": "the id of the signal, 4 characters or more"}),),
    run=inbox_dismiss,
    render_text=_render_text,
)
