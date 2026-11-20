import argparse
import functools
from collections.abc import Callable
from dataclasses import dataclass
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
from brigade.registry.read_project_slots import read_project_slots
from brigade.registry.read_projects import read_projects
from brigade.runs.list_runs import list_runs
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.render_table import render_table
from brigade.tasks.read_task_after import read_task_after
from brigade.tick.build_snapshot import TaskFacts, WaveFacts
from brigade.tick.find_launch_hold import LaunchRound, find_launch_hold
from brigade.tick.read_branch_of_task import read_branch_of_task
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.waves.describe_halt_document import describe_halt_document
from brigade.waves.describe_milestone_merge import describe_milestone_merge
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
from brigade.waves.summarize_waves import WaveSummary

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
TASK_HEADER = ("task", "state", "pull request", "run", "reason")
TASK_COLUMNS = ("task", "state", "pull_request", "run", "reason")
FIXING_STATE = "fixing"
WAITING_STATE = "queued"
LIVE_RUN_STATE = "running"
BUILD_SLOT = "build"
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
    return [describe_halt_document(document["wave"], halt)]


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


@dataclass(frozen=True)
class _WaveReading:
    events: tuple
    states: dict[str, str]
    summary: WaveSummary
    read_launch_hold: Callable[[str], str | None]


def _read_reason(reading: _WaveReading, task: str):
    last_state = find_last_task_event(reading.events, TASK_EVENTS, reading.summary.started.wave, task)
    if _is_explained(last_state):
        return last_state.reason
    if reading.states.get(task, WAITING_STATE) == WAITING_STATE and reading.summary.is_open:
        return reading.read_launch_hold(task)
    return None


def _describe_task(reading: _WaveReading, task: str) -> dict:
    wave = reading.summary.started.wave
    opened = find_last_task_event(reading.events, TaskPrOpened, wave, task)
    finished = find_last_task_event(reading.events, RunFinished, wave, task)
    return {
        "task": task,
        "state": reading.states.get(task),
        "pull_request": None if opened is None else opened.pr,
        "run": None if finished is None else finished.run,
        "reason": _read_reason(reading, task),
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
    root: Path
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
    root = _prepare_tree(runtime, configuration, started).root
    tasks = {
        task.name: task for task in read_entities(runtime.run_process, root, TASK_TYPE) if task.name in started.tasks
    }
    return WaveTree(
        configuration=configuration,
        root=root,
        tasks=tasks,
        milestone=read_wave_milestone(started.wave, tasks.values()),
    )


def _count_used_build_slots(runtime: Runtime, project: str) -> int:
    return sum(
        1
        for run in list_runs(runtime.paths.state_root)["runs"]
        if run["project"] == project and run["state"] == LIVE_RUN_STATE and run["slot"] == BUILD_SLOT
    )


@dataclass(frozen=True)
class _HoldReading:
    wave: WaveFacts
    launch_round: LaunchRound


@dataclass(frozen=True)
class _LaunchHoldSources:
    runtime: Runtime
    started: WaveStarted
    events: tuple
    states: dict[str, str]
    halt: WavePause | None
    read_tree: Callable[[], WaveTree]


def _read_hold_reading(sources: _LaunchHoldSources) -> _HoldReading:
    runtime = sources.runtime
    started = sources.started
    project = find_project(read_projects(runtime), started.project)
    return _HoldReading(
        wave=WaveFacts(
            project=started.project,
            wave=started.wave,
            states=sources.states,
            implemented=read_implemented_tasks(runtime.run_process, sources.read_tree().root),
        ),
        launch_round=LaunchRound(
            halt=sources.halt,
            used_slots=_count_used_build_slots(runtime, started.project),
            slots=read_project_slots(project),
        ),
    )


def _find_launch_hold(sources: _LaunchHoldSources, read_hold: Callable[[], _HoldReading], task: str) -> str | None:
    tree = sources.read_tree()
    entity = tree.tasks[task]
    reading = read_hold()
    facts = TaskFacts(
        name=task,
        branch=read_branch_of_task(sources.events, reading.wave.project, entity),
        after=read_task_after(entity),
        blocked_by=sources.runtime.read_live_blockers(sources.runtime.run_process, tree.root, task),
    )
    return find_launch_hold(facts, reading.wave, reading.launch_round)


def _create_wave_reading(sources: _LaunchHoldSources, summary: WaveSummary) -> _WaveReading:
    read_hold = functools.cache(lambda: _read_hold_reading(sources))
    return _WaveReading(
        events=sources.events,
        states=sources.states,
        summary=summary,
        read_launch_hold=lambda task: _find_launch_hold(sources, read_hold, task),
    )


def _describe_events(reading: LedgerReading, request: argparse.Namespace) -> dict:
    return {EVENTS_KEY: describe_wave(reading, request.wave)} if request.events else {}


def _describe_halt(halt: WavePause | None) -> dict | None:
    return None if halt is None else halt.to_document()


def _read_launch_hold_sources(
    runtime: Runtime, entries: tuple[LedgerEntry, ...], started: WaveStarted
) -> _LaunchHoldSources:
    events = tuple(entry.event for entry in entries)
    return _LaunchHoldSources(
        runtime=runtime,
        started=started,
        events=events,
        states=read_task_states(entries, started.wave),
        halt=read_wave_pause(events, started.wave),
        read_tree=functools.cache(lambda: _read_wave_tree(runtime, started)),
    )


def wave_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    entries = reading.entries
    summary = require_wave_summary(entries, request.wave)
    started = summary.started
    sources = _read_launch_hold_sources(runtime, entries, started)
    read_tree = sources.read_tree
    wave_reading = _create_wave_reading(sources, summary)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": started.wave,
        "project": started.project,
        "branch": started.branch,
        "started_at": format_instant(summary.started_at),
        "last_event": summary.last_event,
        "pull_request": find_integration_pull_request(sources.events, started.wave),
        "tasks": [_describe_task(wave_reading, task) for task in started.tasks],
        **_name_milestone(request, entries, started, read_tree),
        "merge_command": _read_merge_command(runtime, entries, started, read_tree),
        "task_merge_commands": _read_task_merge_commands(runtime, entries, started, read_tree),
        "halt": _describe_halt(sources.halt),
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
