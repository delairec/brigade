import argparse

from brigade.command import Argument, Command
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.read_inbox import NEW_STATUS, read_inbox
from brigade.inbox.render_age import render_age
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
NO_SIGNAL = "no signal in the inbox"
NO_PROJECT = "-"
HEADER = ("id", "kind", "project", "count", "age", "status")


def _render_row(signal: dict) -> tuple[str, ...]:
    return (
        signal["id"][:SHOWN_ID_LENGTH],
        signal["kind"],
        signal["project"] or NO_PROJECT,
        str(signal["count"]),
        render_age(signal["age_s"]),
        signal["status"],
    )


def _render_text(document: dict) -> str:
    if not document["signals"]:
        return NO_SIGNAL
    return render_table(HEADER, [_render_row(signal) for signal in document["signals"]])


def inbox_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "signals": [
            {
                "id": signal.id,
                "fingerprint": signal.fingerprint,
                "kind": signal.kind,
                "project": signal.project,
                "count": signal.count,
                "age_s": signal.age_s,
                "status": signal.status,
            }
            for signal in read_inbox(runtime.paths.state_root, runtime.now)
            if request.all or signal.status == NEW_STATUS
        ],
    }


COMMAND = Command(
    path=("inbox", "list"),
    help="list the new signals of the inbox",
    group_help="list, show and dismiss the signals of the inbox",
    arguments=(Argument(("--all",), {"action": "store_true", "help": "add the dismissed signals"}),),
    run=inbox_list,
    render_text=_render_text,
)
