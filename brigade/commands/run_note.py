import argparse
import json

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.format_instant import format_instant
from brigade.ledger.run_noted import RunNoted
from brigade.runs.run_locations import NOTES_FILE, RUNS_DIRECTORY
from brigade.runs.show_run import show_run
from brigade.runtime import Runtime
from brigade.system.append_line import append_line

DOCUMENT_SCHEMA_VERSION = 1
FINISHED = "finished"


def _render_text(document: dict) -> str:
    return (
        f"noted run {document['run']}: the note waits for the next segment of the run,"
        " a segment already launched taking no input"
    )


def run_note(request: argparse.Namespace, runtime: Runtime) -> dict:
    run = show_run(runtime.paths.state_root, request.run, with_journal=False)["run"]
    if run["state"] == FINISHED:
        raise BrigadeError(
            f"run {request.run} has already finished on {run['outcome']}: no segment of it is left to carry the note"
        )
    note = {"at": format_instant(runtime.now), "text": request.text}
    append_line(runtime.paths.state_root / RUNS_DIRECTORY / request.run / NOTES_FILE, json.dumps(note))
    append_event(runtime.paths, runtime.now, RunNoted(run=request.run, text=request.text))
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "run": request.run, "note": note}


COMMAND = Command(
    path=("run", "note"),
    help="hand a note to a run: the brief of its next segment carries it",
    group_help="start a procedure as a slot through the client adapter, list the runs, show one, stop one and prune them",
    arguments=(Argument(("run",)), Argument(("text",))),
    run=run_note,
    render_text=_render_text,
)
