import dataclasses
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import BrigadeError, CommandFailed
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.list_runs import list_runs
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.read_last_study_orders import LastStudyOrder, read_last_study_orders
from brigade.studies.read_live_study_runs import LiveStudyRun, read_live_study_runs
from brigade.studies.read_studies import read_studies
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.read_configuration import Configuration
from brigade.system.read_study_runs import STUDY_RUNS_BY_DEFAULT
from brigade.system.reset_hour import ResetHour
from brigade.tasks.read_milestone_tasks import read_milestone_tasks
from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree
from brigade.tick.name_task_branch import name_task_branch
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.tick.read_live_blockers import read_live_blockers
from brigade.waves.describe_request import describe_request
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_plan_review import read_plan_review
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_pause import WavePause, read_wave_pause
from brigade.waves.require_wave_name import require_wave_name

DOCUMENT_SCHEMA_VERSION = 1
REQUEST_TYPE = "REQUEST"
RUNNING_STATUS = "running"
PLANNED_STATUS = "planned"
LIVE_RUN_STATE = "running"
SLOTS_FIELD = "SLOTS"
AFTER_FIELD = "AFTER"
TASK_PREFIX = "@TASK."
PROJECT_SLOTS = 4
PARKED_OUTCOME = "parked"
QUEUED_STATE = "queued"
SETTLED_STATES = ("merged", "parked")
PATH_FIELD = "PATH"
RUNNING_STATE = "running"
RATE_LIMIT = "rate_limit"
FORGE_ACCOUNT_REASON = "forge_account"
BEFORE_ANY_EVENT = datetime.min.replace(tzinfo=UTC)


@dataclass(frozen=True)
class RateLimit:
    reset: ResetHour | None

    def to_document(self) -> dict:
        return {"reset": None if self.reset is None else self.reset.to_document()}


@dataclass(frozen=True)
class TaskFacts:
    name: str
    after: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    pull_request: PullRequestFacts | None = None
    worktree: str | None = None
    rate_limit: RateLimit | None = None

    def to_document(self) -> dict:
        return {
            "task": self.name,
            "after": list(self.after),
            "blocked_by": list(self.blocked_by),
            "pull_request": None if self.pull_request is None else self.pull_request.to_document(),
            "worktree": self.worktree,
            "rate_limit": None if self.rate_limit is None else self.rate_limit.to_document(),
        }


@dataclass(frozen=True)
class WaveFacts:
    request: str
    project: str
    milestone: str
    wave: str
    branch: str
    tasks: tuple[TaskFacts, ...] = ()
    states: dict = field(default_factory=dict)
    implemented: tuple[str, ...] = ()
    pause: WavePause | None = None
    forge_account_unavailable: bool = False

    def to_document(self) -> dict:
        return {
            "request": self.request,
            "project": self.project,
            "milestone": self.milestone,
            "wave": self.wave,
            "branch": self.branch,
            "tasks": [task.to_document() for task in self.tasks],
            "states": dict(self.states),
            "implemented": list(self.implemented),
            "pause": None if self.pause is None else self.pause.to_document(),
            "forge_account_unavailable": self.forge_account_unavailable,
        }


@dataclass(frozen=True)
class LiveRun:
    run: str
    slot: str
    worktree: str


@dataclass(frozen=True)
class ProjectFacts:
    name: str
    slots: int
    live_runs: tuple[LiveRun, ...] = ()

    def to_document(self) -> dict:
        return {
            "project": self.name,
            "slots": self.slots,
            "live_runs": [{"run": live.run, "slot": live.slot, "worktree": live.worktree} for live in self.live_runs],
        }


@dataclass(frozen=True)
class PlannedRequest:
    request: str
    project: str
    plan_review: str

    def to_document(self) -> dict:
        return {"request": self.request, "project": self.project, "plan_review": self.plan_review}


@dataclass(frozen=True)
class StudyFacts:
    name: str
    slot: str
    every: str | None
    status: str
    last_started: datetime | None
    parked: bool

    def to_document(self) -> dict:
        return {
            "study": self.name,
            "slot": self.slot,
            "every": self.every,
            "status": self.status,
            "last_started": None if self.last_started is None else format_instant(self.last_started),
            "parked": self.parked,
        }


@dataclass(frozen=True)
class Snapshot:
    now: datetime
    waves: tuple[WaveFacts, ...] = ()
    projects: tuple[ProjectFacts, ...] = ()
    planned: tuple[PlannedRequest, ...] = ()
    studies: tuple[StudyFacts, ...] = ()
    live_study_runs: tuple[LiveStudyRun, ...] = ()
    study_runs: int = STUDY_RUNS_BY_DEFAULT

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "now": format_instant(self.now),
            "waves": [wave.to_document() for wave in self.waves],
            "projects": [project.to_document() for project in self.projects],
            "planned": [planned.to_document() for planned in self.planned],
            "studies": [study.to_document() for study in self.studies],
            "live_study_runs": [live.to_document() for live in self.live_study_runs],
            "study_runs": self.study_runs,
        }


def _read_task_facts(runtime: Runtime, root: Path, task: Entity) -> TaskFacts:
    return TaskFacts(
        name=task.name,
        after=tuple(field.value.removeprefix(TASK_PREFIX) for field in task.fields if field.name == AFTER_FIELD),
        blocked_by=read_live_blockers(runtime.run_process, root, task.name),
    )


@dataclass(frozen=True)
class FollowedWave:
    repository: Path
    worktree_root: str | None
    branch: str
    states: dict
    read_pull_request: Callable[[str, str], PullRequestFacts | None]


def _follow_task(task: TaskFacts, followed: FollowedWave) -> TaskFacts:
    state = followed.states.get(task.name, QUEUED_STATE)
    worktree = locate_scheduled_worktree(followed.repository, followed.worktree_root, task.name)
    standing = worktree.is_dir()
    if state == QUEUED_STATE or (state in SETTLED_STATES and not standing):
        return task
    return dataclasses.replace(
        task,
        pull_request=followed.read_pull_request(str(followed.repository), name_task_branch(followed.branch, task.name)),
        worktree=str(worktree) if standing else None,
    )


@dataclass(frozen=True)
class WaveReading:
    configuration: Configuration
    entries: tuple[LedgerEntry, ...]
    events: tuple
    live_runs: frozenset[str]
    projects: tuple[Entity, ...]
    read_pull_request: Callable[[str, str], PullRequestFacts | None]


def _report_skipped_request(request: dict, refusal: BrigadeError) -> None:
    sys.stderr.write(f"brigade tick: @{REQUEST_TYPE}.{request['name']} skipped: {refusal}\n")


def _read_wave_facts(runtime: Runtime, reading: WaveReading, request: dict) -> WaveFacts | None:
    try:
        wave = require_wave_name(reading.events, request)
    except BrigadeError as refusal:
        _report_skipped_request(request, refusal)
        return None
    try:
        return _collect_wave_facts(runtime, reading, request, wave)
    except CommandFailed as failure:
        _report_skipped_request(request, failure)
        return None


def _read_rate_limit(reading: WaveReading, wave: str, task: str) -> RateLimit | None:
    finished = [
        event
        for event in reading.events
        if isinstance(event, RunFinished) and event.wave == wave and event.task == task
    ]
    if not finished or finished[-1].error_class != RATE_LIMIT or finished[-1].run in reading.live_runs:
        return None
    return RateLimit(reset=finished[-1].reset)


def _is_forge_account_unavailable(entries: tuple[LedgerEntry, ...], wave: str) -> bool:
    unavailable = [entry.instant for entry in entries if isinstance(entry.event, ForgeAccountUnavailable)]
    cleared = [
        entry.instant
        for entry in entries
        if getattr(entry.event, "wave", None) == wave
        and (
            isinstance(entry.event, WaveStarted)
            or (isinstance(entry.event, WaveResumed) and entry.event.reason == FORGE_ACCOUNT_REASON)
        )
    ]
    return bool(unavailable) and max(unavailable) > max(cleared, default=BEFORE_ANY_EVENT)


def _note_rate_limit(task: TaskFacts, reading: WaveReading, wave: str, states: dict) -> TaskFacts:
    if states.get(task.name) != RUNNING_STATE:
        return task
    return dataclasses.replace(task, rate_limit=_read_rate_limit(reading, wave, task.name))


def _collect_wave_facts(runtime: Runtime, reading: WaveReading, request: dict, wave: str) -> WaveFacts:
    tree = prepare_wave_tree(runtime, reading.configuration, request)
    tasks = read_milestone_tasks(runtime.run_process, tree.root, request["milestone"])
    states = read_task_states(runtime.paths.state_root, wave)
    followed = FollowedWave(
        repository=Path(read_project_field(find_project(reading.projects, request["project"]), PATH_FIELD)),
        worktree_root=reading.configuration.worktree_root,
        branch=request["branch"],
        states=states,
        read_pull_request=reading.read_pull_request,
    )
    return WaveFacts(
        request=request["name"],
        project=request["project"],
        milestone=request["milestone"],
        wave=wave,
        branch=request["branch"],
        tasks=tuple(
            _note_rate_limit(_follow_task(_read_task_facts(runtime, tree.root, task), followed), reading, wave, states)
            for task in tasks
        ),
        states=states,
        implemented=read_implemented_tasks(runtime.run_process, tree.root),
        pause=read_wave_pause(reading.events, wave),
        forge_account_unavailable=_is_forge_account_unavailable(reading.entries, wave),
    )


def _read_project_facts(name: str, projects: tuple[Entity, ...], runs: list[dict]) -> ProjectFacts:
    slots = read_project_field(find_project(projects, name), SLOTS_FIELD)
    return ProjectFacts(
        name=name,
        slots=PROJECT_SLOTS if slots is None else int(slots),
        live_runs=tuple(
            LiveRun(run=run["run"], slot=run["slot"], worktree=run["worktree"])
            for run in runs
            if run["project"] == name and run["state"] == LIVE_RUN_STATE
        ),
    )


def _describe_study(study: Study, last_order: LastStudyOrder | None) -> StudyFacts:
    return StudyFacts(
        name=study.name,
        slot=study.slot,
        every=study.every,
        status=study.status,
        last_started=None if last_order is None else last_order.started,
        parked=last_order is not None and last_order.outcome == PARKED_OUTCOME,
    )


def build_snapshot(
    runtime: Runtime,
    configuration: Configuration,
    read_pull_request: Callable[[str, str], PullRequestFacts | None],
) -> Snapshot:
    if not runtime.paths.schema_file.exists():
        return Snapshot(now=runtime.now)
    requests = tuple(
        describe_request(request)
        for request in read_entities(runtime.run_process, runtime.paths.config_root, REQUEST_TYPE)
    )
    registered = read_projects(runtime)
    entries = read_ledger(runtime.paths.state_root).entries
    runs = list_runs(runtime.paths.state_root)["runs"]
    reading = WaveReading(
        configuration=configuration,
        entries=entries,
        events=tuple(entry.event for entry in entries),
        live_runs=frozenset(run["run"] for run in runs if run["state"] == LIVE_RUN_STATE),
        projects=registered,
        read_pull_request=read_pull_request,
    )
    waves = tuple(
        facts
        for facts in (
            _read_wave_facts(runtime, reading, request) for request in requests if request["status"] == RUNNING_STATUS
        )
        if facts is not None
    )
    projects = tuple(
        _read_project_facts(project, registered, runs) for project in dict.fromkeys(wave.project for wave in waves)
    )
    planned = tuple(
        PlannedRequest(
            request=request["name"],
            project=request["project"],
            plan_review=read_plan_review(runtime, request["project"]),
        )
        for request in requests
        if request["status"] == PLANNED_STATUS
    )
    last_orders = read_last_study_orders(runtime.paths.state_root)
    return Snapshot(
        now=runtime.now.astimezone(),
        waves=waves,
        projects=projects,
        planned=planned,
        studies=tuple(_describe_study(study, last_orders.get(study.name)) for study in read_studies(runtime)),
        live_study_runs=read_live_study_runs(runtime.paths.state_root),
        study_runs=configuration.study_runs,
    )
