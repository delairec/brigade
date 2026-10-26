import argparse

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_task_state import PARKED_STATE
from brigade.waves.read_task_states import read_task_states
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
QUEUED_STATE = "queued"


def _render_text(document: dict) -> str:
    return f"task {document['task']} of {document['wave']} {document['state']}"


def wave_requeue(request: argparse.Namespace, runtime: Runtime) -> dict:
    summary = require_wave_summary(read_ledger(runtime.paths.state_root).entries, request.wave)
    if request.task not in summary.started.tasks:
        raise BrigadeError(f"the task {request.task} is not a task of the wave {request.wave}")
    state = read_task_states(runtime.paths.state_root, request.wave).get(request.task, QUEUED_STATE)
    if state != PARKED_STATE:
        raise BrigadeError(f"the task {request.task} of the wave {request.wave} is {state}, not parked")
    tree = prepare_wave_tree(runtime, read_configuration(runtime, CONFIGURATION_OPTIONAL), summary.started)
    if request.task in read_implemented_tasks(runtime.run_process, tree.root):
        raise BrigadeError(
            f"the task {request.task} of the wave {request.wave} is already implemented on {summary.started.branch}"
        )
    append_event(runtime.paths, runtime.now, TaskState(wave=request.wave, task=request.task, state=QUEUED_STATE))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": request.wave,
        "task": request.task,
        "state": QUEUED_STATE,
    }


COMMAND = Command(
    path=("wave", "requeue"),
    help="queue again a parked task of the wave named, for the next tick to launch it",
    arguments=(
        Argument(("wave",), {"help": "the name of the wave"}),
        Argument(("task",), {"help": "the task of the wave to queue again"}),
    ),
    run=wave_requeue,
    render_text=_render_text,
)
