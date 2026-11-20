import argparse
import functools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.corpus.prepare_tree import Tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.git.describe_merge_command import describe_merge_command
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.render_wave_lines import render_wave_lines
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_policy_field import read_policy_field
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.render_table import render_table
from brigade.tick.read_branch_of_task import read_branch_of_task
from brigade.waves.describe_milestone_merge import describe_milestone_merge
from brigade.waves.describe_wave_halt import describe_wave_halt
from brigade.waves.find_integration_pull_request import find_integration_pull_request
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_milestone_report_committed import is_milestone_report_committed
from brigade.waves.locate_merge_worktree import locate_merge_worktree
from brigade.waves.prepare_wave_tree import WaveTreeReading, prepare_wave_tree
from brigade.waves.read_task_state import TASK_EVENTS
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_milestone import read_wave_milestone
from brigade.waves.read_wave_pause import WavePause, read_wave_pause
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
TASK_HEADER = ("task", "state", "pull request", "run", "reason")
TASK_COLUMNS = ("task", "state", "pull_request", "run", "reason")
FIXING_STATE = "fixing"
TASK_TYPE = "TASK"
POLICY_TYPE = "POLICY"
PATH_FIELD = "PATH"
AUTO_MERGE_FIELD = "AUTO_MERGE"
NO_AUTO_MERGE = "none"
NO_POLICY = None
VERIFIED_STATE = "verified"
EVENTS_KEY = "ledger"
JSON_OPTION = "json"


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_halt(document: dict) -> list[str]:
    halt = document["halt"]
    if halt is None:
        return []
    resume_at = None if halt["resume_at"] is None else datetime.fromisoformat(halt["resume_at"])
    return [describe_wave_halt(document["wave"], WavePause(reason=halt["reason"], resume_at=resume_at))]


def _render_text(document: dict) -> str:
    rows = [tuple(_show(task[column]) for column in TASK_COLUMNS) for task in document["tasks"]]
    heading = (
        f"wave {document['wave']} of @PROJECT.{document['project']} on {document['branch']},"
        f" started {document['started_at']}, last event {document['last_event']},"
        f" pull request {_show(document['pull_request'])}"
    )
    commands = (*document["task_merge_commands"], document["merge_command"])
    merges = [f"to merge: {command}" for command in commands if command is not None]
    ledger = render_wave_lines(document["ledger"]) if EVENTS_KEY in document else []
    return "\n".join([heading, *_render_halt(document), render_table(TASK_HEADER, rows), *merges, *ledger])


def _is_explained(event) -> bool:
    return isinstance(event, TaskParked) or (isinstance(event, TaskState) and event.state == FIXING_STATE)


def _describe_task(events: tuple, states: dict[str, str], wave: str, task: str) -> dict:
    opened = find_last_task_event(events, TaskPrOpened, wave, task)
    finished = find_last_task_event(events, RunFinished, wave, task)
    last_state = find_last_task_event(events, TASK_EVENTS, wave, task)
    return {
        "task": task,
        "state": states.get(task),
        "pull_request": None if opened is None else opened.pr,
        "run": None if finished is None else finished.run,
        "reason": last_state.reason if _is_explained(last_state) else None,
    }


def _prepare_tree(runtime: Runtime, configuration: Configuration, started: WaveStarted) -> Tree:
    project = find_project(read_projects(runtime), started.project)
    reading = WaveTreeReading(
        configuration=configuration,
        read_environment=lambda key: read_forge_environment(
            configuration, ForgeSlot(read_project_forge(project), key), runtime
        ),
        reaches_the_forge=False,
    )
    return prepare_wave_tree(runtime, reading, started)


def _read_merge_command(
    runtime: Runtime, entries: tuple[LedgerEntry, ...], started: WaveStarted, read_tree: Callable[[], "WaveTree"]
) -> str | None:
    if not any(
        isinstance(entry.event, MilestoneReported) and entry.event.project == started.project for entry in entries
    ):
        return None
    return describe_milestone_merge(
        entries, find_project(read_projects(runtime), started.project), read_tree().milestone
    )


def _name_milestone_report(entries: tuple[LedgerEntry, ...], started: WaveStarted, milestone: str | None) -> str | None:
    if not is_milestone_report_committed(entries, started.project, milestone):
        return None
    return f"{started.project}_{milestone}"


def _name_milestone(
    request: argparse.Namespace,
    entries: tuple[LedgerEntry, ...],
    started: WaveStarted,
    read_tree: Callable[[], "WaveTree"],
) -> dict:
    if not getattr(request, JSON_OPTION, False):
        return {}
    milestone = read_tree().milestone
    return {"milestone": milestone, "milestone_report": _name_milestone_report(entries, started, milestone)}


def _read_wave_tasks(runtime: Runtime, configuration: Configuration, started: WaveStarted) -> dict[str, Entity]:
    tasks = read_entities(runtime.run_process, _prepare_tree(runtime, configuration, started).root, TASK_TYPE)
    return {task.name: task for task in tasks if task.name in started.tasks}


def _leaves_the_milestone_merge_to_the_user(runtime: Runtime, project: Entity) -> bool:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    return read_policy_field(policies, project.name, AUTO_MERGE_FIELD, NO_POLICY) == NO_AUTO_MERGE


def _locate_task_merge(runtime: Runtime, project: Entity, worktree_root: str | None, branch: str | None) -> Path:
    repository = Path(read_project_field(project, PATH_FIELD))
    if branch is None:
        return repository
    return locate_merge_worktree(runtime.run_process, repository, worktree_root, branch).path


@dataclass(frozen=True)
class WaveTree:
    configuration: Configuration
    tasks: dict[str, Entity]
    milestone: str | None


def _read_task_merge_commands(
    runtime: Runtime, entries: tuple[LedgerEntry, ...], started: WaveStarted, read_tree: Callable[[], WaveTree]
) -> list[str]:
    states = read_task_states(entries, started.wave)
    verified = [task for task in started.tasks if states.get(task) == VERIFIED_STATE]
    if not verified:
        return []
    project = find_project(read_projects(runtime), started.project)
    if is_on_a_forge(project):
        return []
    tree = read_tree()
    if tree.milestone is not None and not _leaves_the_milestone_merge_to_the_user(runtime, project):
        return []
    branch = find_milestone_branch(entries, started.project, tree.milestone)
    target = _locate_task_merge(runtime, project, tree.configuration.worktree_root, branch)
    events = tuple(entry.event for entry in entries)
    return [
        describe_merge_command(target, read_branch_of_task(events, started.project, tree.tasks[task]))
        for task in verified
    ]


def _read_wave_tree(runtime: Runtime, started: WaveStarted) -> WaveTree:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tasks = _read_wave_tasks(runtime, configuration, started)
    return WaveTree(
        configuration=configuration, tasks=tasks, milestone=read_wave_milestone(started.wave, tasks.values())
    )


def _describe_events(reading: LedgerReading, request: argparse.Namespace) -> dict:
    return {EVENTS_KEY: describe_wave(reading, request.wave)} if request.events else {}


def _describe_halt(halt: WavePause | None) -> dict | None:
    return None if halt is None else halt.to_document()


def wave_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    entries = reading.entries
    summary = require_wave_summary(entries, request.wave)
    events = tuple(entry.event for entry in entries)
    started = summary.started
    states = read_task_states(entries, started.wave)
    read_tree = functools.cache(lambda: _read_wave_tree(runtime, started))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": started.wave,
        "project": started.project,
        "branch": started.branch,
        "started_at": format_instant(summary.started_at),
        "last_event": summary.last_event,
        "pull_request": find_integration_pull_request(events, started.wave),
        "tasks": [_describe_task(events, states, started.wave, task) for task in started.tasks],
        **_name_milestone(request, entries, started, read_tree),
        "merge_command": _read_merge_command(runtime, entries, started, read_tree),
        "task_merge_commands": _read_task_merge_commands(runtime, entries, started, read_tree),
        "halt": _describe_halt(read_wave_pause(events, started.wave)),
        **_describe_events(reading, request),
    }


COMMAND = Command(
    path=("wave", "show"),
    help="print a wave and each of its tasks with its state, its pull request and its run",
    arguments=(
        Argument(("wave",), {"help": "the name of a wave of the ledger"}),
        Argument(
            ("--events",),
            {
                "action": "store_true",
                "help": "add its cost, tokens, turns, halts, handovers, parked tasks and events in the order recorded",
            },
        ),
    ),
    run=wave_show,
    render_text=_render_text,
)
