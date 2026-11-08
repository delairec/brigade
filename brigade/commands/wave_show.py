import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.corpus.read_entities import Entity, read_entities
from brigade.git.describe_merge_command import describe_merge_command
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_policy_field import read_policy_field
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.render_table import render_table
from brigade.tick.name_branch_of_task import name_branch_of_task
from brigade.waves.describe_milestone_merge import describe_milestone_merge
from brigade.waves.find_integration_pull_request import find_integration_pull_request
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.locate_merge_worktree import locate_merge_worktree
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_task_state import TASK_EVENTS
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_milestone import read_wave_milestone
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


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_text(document: dict) -> str:
    rows = [tuple(_show(task[column]) for column in TASK_COLUMNS) for task in document["tasks"]]
    heading = (
        f"wave {document['wave']} of @PROJECT.{document['project']} on {document['branch']},"
        f" started {document['started_at']}, last event {document['last_event']},"
        f" pull request {_show(document['pull_request'])}"
    )
    commands = (*document["task_merge_commands"], document["merge_command"])
    merges = [f"to merge: {command}" for command in commands if command is not None]
    return "\n".join([heading, render_table(TASK_HEADER, rows), *merges])


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


def _read_merge_command(runtime: Runtime, entries: tuple[LedgerEntry, ...], started: WaveStarted) -> str | None:
    if not any(
        isinstance(entry.event, MilestoneReported) and entry.event.project == started.project for entry in entries
    ):
        return None
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tasks = read_entities(runtime.run_process, prepare_wave_tree(runtime, configuration, started).root, TASK_TYPE)
    milestone = read_wave_milestone(started.wave, (task for task in tasks if task.name in started.tasks))
    return describe_milestone_merge(entries, find_project(read_projects(runtime), started.project), milestone)


def _leaves_the_milestone_merge_to_the_user(runtime: Runtime, project: Entity) -> bool:
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    return read_policy_field(policies, project.name, AUTO_MERGE_FIELD, NO_POLICY) == NO_AUTO_MERGE


def _locate_task_merge(runtime: Runtime, project: Entity, worktree_root: str | None, branch: str | None) -> Path:
    repository = Path(read_project_field(project, PATH_FIELD))
    if branch is None:
        return repository
    return locate_merge_worktree(runtime.run_process, repository, worktree_root, branch).path


def _read_task_merge_commands(
    runtime: Runtime, entries: tuple[LedgerEntry, ...], started: WaveStarted, states: dict[str, str]
) -> list[str]:
    verified = [task for task in started.tasks if states.get(task) == VERIFIED_STATE]
    if not verified:
        return []
    project = find_project(read_projects(runtime), started.project)
    if is_on_a_forge(project):
        return []
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    tasks = read_entities(runtime.run_process, prepare_wave_tree(runtime, configuration, started).root, TASK_TYPE)
    of_wave = {task.name: task for task in tasks if task.name in started.tasks}
    milestone = read_wave_milestone(started.wave, of_wave.values())
    if milestone is not None and not _leaves_the_milestone_merge_to_the_user(runtime, project):
        return []
    branch = find_milestone_branch(entries, started.project, milestone)
    target = _locate_task_merge(runtime, project, configuration.worktree_root, branch)
    return [describe_merge_command(target, name_branch_of_task(of_wave[task])) for task in verified]


def wave_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    entries = read_ledger(runtime.paths.state_root).entries
    summary = require_wave_summary(entries, request.wave)
    events = tuple(entry.event for entry in entries)
    started = summary.started
    states = read_task_states(entries, started.wave)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": started.wave,
        "project": started.project,
        "branch": started.branch,
        "started_at": format_instant(summary.started_at),
        "last_event": summary.last_event,
        "pull_request": find_integration_pull_request(events, started.wave),
        "tasks": [_describe_task(events, states, started.wave, task) for task in started.tasks],
        "merge_command": _read_merge_command(runtime, entries, started),
        "task_merge_commands": _read_task_merge_commands(runtime, entries, started, states),
    }


COMMAND = Command(
    path=("wave", "show"),
    help="print a wave and each of its tasks with its state, its pull request and its run",
    arguments=(Argument(("wave",), {"help": "the name of a wave of the ledger"}),),
    run=wave_show,
    render_text=_render_text,
)
