import argparse
import json
from datetime import UTC, datetime

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.system.instant_formats import ISO_INSTANT_FORMAT

DOCUMENT_SCHEMA_VERSION = 1
NO_STOP = ""


def _render_text(document: dict) -> str:
    if document["stop"] is None:
        return NO_STOP
    return json.dumps(document["stop"])


def _describe_stop(soft_limit: datetime) -> dict:
    return {"continue": False, "stopReason": f"the soft limit {soft_limit.strftime(ISO_INSTANT_FORMAT)} has passed"}


def runs_stop_hook(request: argparse.Namespace, runtime: Runtime) -> dict:
    soft_limit = datetime.fromtimestamp(request.at, UTC)
    passed = runtime.read_clock() >= soft_limit
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "stop": _describe_stop(soft_limit) if passed else None}


COMMAND = Command(
    path=("runs", "stop-hook"),
    help="print the document that stops a client session once the soft limit of its run has passed",
    arguments=(
        Argument(("--at",), {"required": True, "type": int, "help": "the soft limit, in seconds since the epoch"}),
    ),
    run=runs_stop_hook,
    render_text=_render_text,
)
