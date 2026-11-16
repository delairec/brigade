import argparse
from dataclasses import dataclass
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.git.find_merge_base import find_merge_base
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_state import REQUEUE_REASON, TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.locate_project_main import locate_project_main
from brigade.waves.prepare_wave_tree import WaveTreeReading, prepare_wave_tree
from brigade.waves.read_task_state import PARKED_STATE
from brigade.waves.read_task_states import read_task_states
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
QUEUED_STATE = "queued"
PR_OPEN_STATE = "pr_open"
TASK_TYPE = "TASK"
REPOSITORY_FIELD = "PATH"
NO_WORKTREE = None


def _render_text(document: dict) -> str:
    return f"task {document['task']} of {document['wave']} {document['state']}"


def _prepare_tree_at(runtime: Runtime, configuration: Configuration, started: WaveStarted, ref: str) -> Tree:
    query = argparse.Namespace(project=started.project, ref=ref, worktree=NO_WORKTREE)
    return prepare_project_tree(query, configuration, runtime)


def _read_task_or_none(runtime: Runtime, tree: Tree, task: str) -> Entity | None:
    try:
        return read_entity(runtime.run_process, tree.root, TASK_TYPE, task)
    except EntityNotDefined:
        return None


@dataclass(frozen=True)
class TaskOfWave:
    started: WaveStarted
    tree: Tree
    entity: Entity


def _read_task_at_the_fork(
    runtime: Runtime, configuration: Configuration, task: TaskOfWave, main_tree: Tree, repository: Path
) -> Entity | None:
    fork = find_merge_base(runtime.run_process, repository, main_tree.sha, task.tree.sha)
    return _read_task_or_none(runtime, _prepare_tree_at(runtime, configuration, task.started, fork), task.entity.name)


def _require_unruled_on_main(runtime: Runtime, configuration: Configuration, task: TaskOfWave):
    started = task.started
    project = find_project(read_projects(runtime), started.project)
    main = locate_project_main(
        runtime.run_process,
        project,
        lambda key: read_forge_environment(configuration, ForgeSlot(read_project_forge(project), key), runtime),
    )
    main_tree = _prepare_tree_at(runtime, configuration, started, main)
    on_main = _read_task_or_none(runtime, main_tree, task.entity.name)
    if on_main is None or on_main == task.entity:
        return
    repository = Path(read_project_field(project, REPOSITORY_FIELD))
    if _read_task_at_the_fork(runtime, configuration, task, main_tree, repository) != on_main:
        raise BrigadeError(
            f"the task {task.entity.name} of the wave {started.wave} differs between {main} and {task.tree.ref}:"
            f" the ruling on main reaches it through brigade wave cancel {started.wave} and a new wave cut from {main}"
        )


def _decide_requeued_state(entries: tuple[LedgerEntry, ...], wave: str, task: str) -> str:
    if any(
        isinstance(entry.event, TaskPrOpened) and entry.event.wave == wave and entry.event.task == task
        for entry in entries
    ):
        return PR_OPEN_STATE
    return QUEUED_STATE


def _prepare_tree(runtime: Runtime, configuration: Configuration, started: WaveStarted) -> Tree:
    project = find_project(read_projects(runtime), started.project)
    reading = WaveTreeReading(
        configuration=configuration,
        read_environment=lambda key: read_forge_environment(
            configuration, ForgeSlot(read_project_forge(project), key), runtime
        ),
    )
    return prepare_wave_tree(runtime, reading, started)


def wave_requeue(request: argparse.Namespace, runtime: Runtime) -> dict:
    entries = read_ledger(runtime.paths.state_root).entries
    summary = require_wave_summary(entries, request.wave)
    if request.task not in summary.started.tasks:
        raise BrigadeError(f"the task {request.task} is not a task of the wave {request.wave}")
    state = read_task_states(entries, request.wave).get(request.task, QUEUED_STATE)
    if state != PARKED_STATE:
        raise BrigadeError(f"the task {request.task} of the wave {request.wave} is {state}, not parked")
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tree = _prepare_tree(runtime, configuration, summary.started)
    if request.task in read_implemented_tasks(runtime.run_process, tree.root):
        raise BrigadeError(f"the task {request.task} of the wave {request.wave} is already implemented on {tree.ref}")
    on_wave = read_entity(runtime.run_process, tree.root, TASK_TYPE, request.task)
    if summary.is_open:
        _require_unruled_on_main(runtime, configuration, TaskOfWave(started=summary.started, tree=tree, entity=on_wave))
    requeued = _decide_requeued_state(entries, request.wave, request.task)
    append_event(
        runtime.paths,
        runtime.now,
        TaskState(wave=request.wave, task=request.task, state=requeued, reason=REQUEUE_REASON),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": request.wave,
        "task": request.task,
        "state": requeued,
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
