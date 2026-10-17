import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.ledger.format_instant import format_instant
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.list_runs import list_runs
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.read_last_study_orders import LastStudyOrder, read_last_study_orders
from brigade.studies.read_studies import read_studies
from brigade.studies.study_run_context import STUDY_RECORD_FILE
from brigade.system.read_configuration import Configuration
from brigade.system.read_study_runs import STUDY_RUNS_BY_DEFAULT
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.tick.read_live_blockers import read_live_blockers
from brigade.waves.describe_request import describe_request
from brigade.waves.read_plan_review import read_plan_review
from brigade.waves.read_task_states import read_task_states

DOCUMENT_SCHEMA_VERSION = 1
REQUEST_TYPE = "REQUEST"
TASK_TYPE = "TASK"
RUNNING_STATUS = "running"
PLANNED_STATUS = "planned"
LIVE_RUN_STATE = "running"
SLOTS_FIELD = "SLOTS"
AFTER_FIELD = "AFTER"
TASK_PREFIX = "@TASK."
PROJECT_SLOTS = 4
PARKED_OUTCOME = "parked"


@dataclass(frozen=True)
class TaskFacts:
    name: str
    after: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()

    def to_document(self) -> dict:
        return {"task": self.name, "after": list(self.after), "blocked_by": list(self.blocked_by)}


@dataclass(frozen=True)
class WaveFacts:
    request: str
    project: str
    milestone: str
    branch: str
    tasks: tuple[TaskFacts, ...] = ()
    states: dict = field(default_factory=dict)
    implemented: tuple[str, ...] = ()

    def to_document(self) -> dict:
        return {
            "request": self.request,
            "project": self.project,
            "milestone": self.milestone,
            "branch": self.branch,
            "tasks": [task.to_document() for task in self.tasks],
            "states": dict(self.states),
            "implemented": list(self.implemented),
        }


@dataclass(frozen=True)
class LiveRun:
    run: str
    slot: str


@dataclass(frozen=True)
class ProjectFacts:
    name: str
    slots: int
    live_runs: tuple[LiveRun, ...] = ()

    def to_document(self) -> dict:
        return {
            "project": self.name,
            "slots": self.slots,
            "live_runs": [{"run": live.run, "slot": live.slot} for live in self.live_runs],
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
class LiveStudyRun:
    study: str
    run: str

    def to_document(self) -> dict:
        return {"study": self.study, "run": self.run}


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


def _read_wave_facts(runtime: Runtime, configuration: Configuration, request: dict) -> WaveFacts:
    query = argparse.Namespace(project=request["project"], ref=request["branch"], worktree=None)
    tree = prepare_project_tree(query, configuration, runtime)
    tasks = read_entities(runtime.run_process, tree.root, TASK_TYPE, f"MILESTONE==@MILESTONE.{request['milestone']}")
    return WaveFacts(
        request=request["name"],
        project=request["project"],
        milestone=request["milestone"],
        branch=request["branch"],
        tasks=tuple(_read_task_facts(runtime, tree.root, task) for task in tasks),
        states=read_task_states(runtime.paths.state_root, request["milestone"]),
        implemented=read_implemented_tasks(runtime.run_process, tree.root),
    )


def _read_project_facts(name: str, projects: tuple[Entity, ...], runs: list[dict]) -> ProjectFacts:
    slots = read_project_field(find_project(projects, name), SLOTS_FIELD)
    return ProjectFacts(
        name=name,
        slots=PROJECT_SLOTS if slots is None else int(slots),
        live_runs=tuple(
            LiveRun(run=run["run"], slot=run["slot"])
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


def _read_live_study_runs(state_root: Path) -> tuple[LiveStudyRun, ...]:
    return tuple(
        LiveStudyRun(study=json.loads(record.read_text(encoding="utf-8"))["study"], run=record.parent.name)
        for record in sorted((state_root / RUNS_DIRECTORY).glob(f"*/{STUDY_RECORD_FILE}"))
        if is_recorded_process_alive(record.parent)
    )


def build_snapshot(runtime: Runtime, configuration: Configuration) -> Snapshot:
    if not runtime.paths.schema_file.exists():
        return Snapshot(now=runtime.now)
    requests = tuple(
        describe_request(request)
        for request in read_entities(runtime.run_process, runtime.paths.config_root, REQUEST_TYPE)
    )
    waves = tuple(
        _read_wave_facts(runtime, configuration, request) for request in requests if request["status"] == RUNNING_STATUS
    )
    registered = read_projects(runtime)
    runs = list_runs(runtime.paths.state_root)["runs"]
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
        live_study_runs=_read_live_study_runs(runtime.paths.state_root),
        study_runs=configuration.study_runs,
    )
