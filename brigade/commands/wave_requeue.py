import argparse

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import read_forge_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.locate_project_main import locate_project_main
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_task_state import PARKED_STATE
from brigade.waves.read_task_states import read_task_states
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
QUEUED_STATE = "queued"
TASK_TYPE = "TASK"
NO_WORKTREE = None


def _render_text(document: dict) -> str:
    return f"task {document['task']} of {document['wave']} {document['state']}"


def _read_task_on_main(runtime: Runtime, configuration: Configuration, started: WaveStarted, task: str):
    project = find_project(read_projects(runtime), started.project)
    main = locate_project_main(
        runtime.run_process, project, lambda key: read_forge_environment(configuration, key, runtime)
    )
    query = argparse.Namespace(project=started.project, ref=main, worktree=NO_WORKTREE)
    try:
        tree = prepare_project_tree(query, configuration, runtime)
        return main, read_entity(runtime.run_process, tree.root, TASK_TYPE, task)
    except EntityNotDefined:
        return main, None


def _require_unruled_on_main(runtime: Runtime, configuration: Configuration, started: WaveStarted, on_wave: Entity):
    main, on_main = _read_task_on_main(runtime, configuration, started, on_wave.name)
    if on_main is not None and on_main != on_wave:
        raise BrigadeError(
            f"the task {on_wave.name} of the wave {started.wave} differs between {main} and {started.branch}:"
            f" the ruling on main reaches it through brigade wave cancel {started.wave} and a new wave cut from {main}"
        )


def wave_requeue(request: argparse.Namespace, runtime: Runtime) -> dict:
    summary = require_wave_summary(read_ledger(runtime.paths.state_root).entries, request.wave)
    if request.task not in summary.started.tasks:
        raise BrigadeError(f"the task {request.task} is not a task of the wave {request.wave}")
    state = read_task_states(runtime.paths.state_root, request.wave).get(request.task, QUEUED_STATE)
    if state != PARKED_STATE:
        raise BrigadeError(f"the task {request.task} of the wave {request.wave} is {state}, not parked")
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tree = prepare_wave_tree(runtime, configuration, summary.started)
    if request.task in read_implemented_tasks(runtime.run_process, tree.root):
        raise BrigadeError(
            f"the task {request.task} of the wave {request.wave} is already implemented on {summary.started.branch}"
        )
    on_wave = read_entity(runtime.run_process, tree.root, TASK_TYPE, request.task)
    _require_unruled_on_main(runtime, configuration, summary.started, on_wave)
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
