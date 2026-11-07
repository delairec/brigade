import argparse
import dataclasses
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError, CommandFailed, TaskTypeMissing, ToolFailure
from brigade.git.check_ancestor import check_ancestor
from brigade.git.has_uncommitted_changes import has_uncommitted_changes
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_pr_described import MilestonePrDescribed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_reported import TaskReported
from brigade.ledger.task_state import QUOTA_RESUME_REASON, TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_policy_field import read_policy_field
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.list_runs import list_runs
from brigade.runs.read_run_question import read_run_question
from brigade.runtime import Runtime
from brigade.studies.read_last_study_orders import read_last_study_orders
from brigade.studies.read_live_study_runs import LiveStudyRun, read_live_study_runs
from brigade.studies.read_studies import read_studies
from brigade.system.parse_configuration import Configuration
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.read_study_runs import STUDY_RUNS_BY_DEFAULT
from brigade.system.remember_process_records import remember_process_records
from brigade.system.reset_hour import ResetHour
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.tick.decide_resume_at import decide_resume_at
from brigade.tick.describe_study_facts import describe_study_facts
from brigade.tick.is_milestone_rebase_held import MilestoneHeads, is_milestone_rebase_held
from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree
from brigade.tick.name_task_branch import name_task_branch
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.tick.read_integration_branches import (
    IntegrationBranchFacts,
    IntegrationBranchReading,
    read_integration_branches,
)
from brigade.tick.study_facts import StudyFacts
from brigade.waves.count_repair_rounds import count_repair_rounds
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_requeue import is_requeue
from brigade.waves.list_candidate_waves import CandidateWave, list_candidate_waves
from brigade.waves.list_tasks_of_reached_milestones import list_tasks_of_reached_milestones
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.name_milestone_branch import name_milestone_branch
from brigade.waves.prepare_wave_tree import WaveTreeReading, locate_wave_branch_base, prepare_wave_tree
from brigade.waves.read_active_milestones import read_active_milestones
from brigade.waves.read_project_tasks import ProjectTasks, ProjectTasksReading, read_project_tasks
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_pause import WavePause, read_wave_pause
from brigade.waves.read_wave_start import read_wave_start
from brigade.waves.summarize_waves import summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
TASK_TYPE = "TASK"
LIVE_RUN_STATE = "running"
SLOTS_FIELD = "SLOTS"
CHECK_RUNS_FIELD = "CHECK_RUNS"
NO_CHECK_RUNS = "none"
AFTER_FIELD = "AFTER"
TASK_PREFIX = "@TASK."
MILESTONE_FIELD = "MILESTONE"
TYPE_FIELD = "TYPE"
TITLE_FIELD = "TITLE"
MILESTONE_PREFIX = "@MILESTONE."
MILESTONE_TYPE = "MILESTONE"
NO_MILESTONE = None
TITLE_FIELD = "TITLE"
PROJECT_SLOTS = 4
QUEUED_STATE = "queued"
SETTLED_STATES = ("merged", "parked")
PATH_FIELD = "PATH"
MAIN_FIELD = "MAIN"
DESCENDING = 0
RUNNING_STATE = "running"
PAUSED_ON_QUOTA_STATE = "paused:quota"
RATE_LIMIT = "rate_limit"
REVIEW_SLOT = "review"
REBASE_SLOT = "rebase"
BLOCKED_OUTCOME = "blocked"
DONE_OUTCOME = "done"
FORGE_ACCOUNT_REASON = "forge_account"
QUOTA_REASON = "quota"
PROJECT_STATUS_FIELD = "STATUS"
PAUSED_PROJECT_STATUS = "paused"
MERGE_FIELD = "MERGE"
REBASE_MERGE = "rebase"
POLICY_TYPE = "POLICY"
REVIEW_FIELD = "REVIEW"
VERDICT_REVIEW = "verdict"
AUTO_MERGE_FIELD = "AUTO_MERGE"
MERGE_INTO_INTEGRATION = "integration"
VERIFY_ROUNDS_BY_DEFAULT = 2
VERIFY_ROUNDS_FIELD = "VERIFY_ROUNDS"
FIXING_STATE = "fixing"
QUOTA_PAUSED_STATES = (RUNNING_STATE, FIXING_STATE)
FAILED_PREFLIGHT_CHECK = "fail"
BEFORE_ANY_EVENT = datetime.min.replace(tzinfo=UTC)
STATUS_FIELD = "STATUS"
TODO_STATUS = "todo"
OPEN_TASK_STATUSES = frozenset({("draft",), (TODO_STATUS,)})
OPEN_PULL_REQUEST = "open"
PROMOTION_FIELDS = (STATUS_FIELD, "DELIVERED_BY")


@dataclass(frozen=True)
class RateLimit:
    reset: ResetHour | None

    def to_document(self) -> dict:
        return {"reset": None if self.reset is None else self.reset.to_document()}


@dataclass(frozen=True)
class RecordedVerdict:
    head: str
    verdict: str


@dataclass(frozen=True)
class PreflightFailure:
    name: str
    findings: tuple[str, ...]


@dataclass(frozen=True)
class BlockedRun:
    run: str
    question: str


@dataclass(frozen=True)
class TaskAmendment:
    on_pull_request: Entity
    on_wave: Entity


@dataclass(frozen=True)
class TaskFacts:
    name: str
    branch: str
    after: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    pull_request: PullRequestFacts | None = None
    worktree: str | None = None
    rate_limit: RateLimit | None = None
    stopped_run: str | None = None
    resumed_state: str | None = None
    opened_pull_request: int | None = None
    opening_of_its_pull_request: TaskPrOpened | None = None
    preflighted_head: str | None = None
    verdict: RecordedVerdict | None = None
    reviewed_head: str | None = None
    preflight_failures: tuple[PreflightFailure, ...] = ()
    repair_rounds: int = 0
    holds_uncommitted_changes: bool = False
    last_run: str | None = None
    blocked_run: BlockedRun | None = None
    rebased_by_last_run: bool = False
    last_run_is_a_rebase: bool = False
    milestone: str | None = None
    amendment: TaskAmendment | None = None
    reported: bool = False
    delivered_head: str | None = None

    def to_document(self) -> dict:
        return {
            "task": self.name,
            "branch": self.branch,
            "after": list(self.after),
            "blocked_by": list(self.blocked_by),
            "pull_request": None if self.pull_request is None else self.pull_request.to_document(),
            "worktree": self.worktree,
            "rate_limit": None if self.rate_limit is None else self.rate_limit.to_document(),
            "stopped_run": self.stopped_run,
            "opened_pull_request": self.opened_pull_request,
            "preflighted_head": self.preflighted_head,
            "verdict": None if self.verdict is None else {"head": self.verdict.head, "verdict": self.verdict.verdict},
            "reviewed_head": self.reviewed_head,
            "preflight_failures": [
                {"name": failure.name, "findings": list(failure.findings)} for failure in self.preflight_failures
            ],
            "repair_rounds": self.repair_rounds,
            "holds_uncommitted_changes": self.holds_uncommitted_changes,
            "last_run": self.last_run,
            "blocked_run": (
                None
                if self.blocked_run is None
                else {"run": self.blocked_run.run, "question": self.blocked_run.question}
            ),
            "milestone": self.milestone,
        }


@dataclass(frozen=True)
class WaveFacts:
    project: str
    wave: str
    base: str | None = None
    tasks: tuple[TaskFacts, ...] = ()
    states: dict = field(default_factory=dict)
    implemented: tuple[str, ...] = ()
    pause: WavePause | None = None
    forge_account_unavailable: bool = False
    milestone_branch: str | None = None
    blocked_rebase: BlockedRun | None = None

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "base": self.base,
            "tasks": [task.to_document() for task in self.tasks],
            "states": dict(self.states),
            "implemented": list(self.implemented),
            "pause": None if self.pause is None else self.pause.to_document(),
            "forge_account_unavailable": self.forge_account_unavailable,
            "milestone_branch": self.milestone_branch,
            "blocked_rebase": (
                None
                if self.blocked_rebase is None
                else {"run": self.blocked_rebase.run, "question": self.blocked_rebase.question}
            ),
        }


@dataclass(frozen=True)
class LiveRun:
    run: str
    slot: str
    worktree: str
    wave: str | None = None
    task: str | None = None


@dataclass(frozen=True)
class UncutMilestone:
    milestone: str
    branch: str
    open_waves: tuple[str, ...] = ()
    todo: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectFacts:
    name: str
    slots: int
    live_runs: tuple[LiveRun, ...] = ()
    awaits_check_runs: bool = True
    wave_start: str = "auto"
    candidates: tuple[CandidateWave, ...] = ()
    merge: str = REBASE_MERGE
    review: str = VERDICT_REVIEW
    auto_merge: str = MERGE_INTO_INTEGRATION
    verify_rounds: int = VERIFY_ROUNDS_BY_DEFAULT
    on_github: bool = False
    uncut_milestones: tuple[UncutMilestone, ...] = ()

    def to_document(self) -> dict:
        return {
            "project": self.name,
            "slots": self.slots,
            "live_runs": [{"run": live.run, "slot": live.slot, "worktree": live.worktree} for live in self.live_runs],
            "wave_start": self.wave_start,
            "candidates": [{"milestone": wave.milestone, "tasks": list(wave.tasks)} for wave in self.candidates],
            "merge": self.merge,
            "review": self.review,
            "auto_merge": self.auto_merge,
            "verify_rounds": self.verify_rounds,
            "awaits_check_runs": self.awaits_check_runs,
            "on_github": self.on_github,
            "uncut_milestones": [
                {
                    "milestone": uncut.milestone,
                    "branch": uncut.branch,
                    "open_waves": list(uncut.open_waves),
                    "todo": list(uncut.todo),
                }
                for uncut in self.uncut_milestones
            ],
        }


@dataclass(frozen=True)
class MilestoneFacts:
    project: str
    milestone: str
    branch: str
    closed_waves: tuple[str, ...] = ()
    open_waves: tuple[str, ...] = ()
    open_tasks: tuple[str, ...] = ()
    opened_pull_request: int | None = None
    pull_request: PullRequestFacts | None = None
    behind_main: bool = False
    rebase_run_live: bool = False
    blocked_rebase: BlockedRun | None = None
    tasks: tuple[str, ...] = ()
    reported: bool = False
    described_head: str | None = None

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "milestone": self.milestone,
            "branch": self.branch,
            "closed_waves": list(self.closed_waves),
            "open_waves": list(self.open_waves),
            "open_tasks": list(self.open_tasks),
            "opened_pull_request": self.opened_pull_request,
            "pull_request": None if self.pull_request is None else self.pull_request.to_document(),
            "behind_main": self.behind_main,
            "rebase_run_live": self.rebase_run_live,
            "blocked_rebase": (
                None
                if self.blocked_rebase is None
                else {"run": self.blocked_rebase.run, "question": self.blocked_rebase.question}
            ),
            "tasks": list(self.tasks),
            "reported": self.reported,
            "described_head": self.described_head,
        }


@dataclass(frozen=True)
class Snapshot:
    now: datetime
    waves: tuple[WaveFacts, ...] = ()
    projects: tuple[ProjectFacts, ...] = ()
    studies: tuple[StudyFacts, ...] = ()
    live_study_runs: tuple[LiveStudyRun, ...] = ()
    study_runs: int = STUDY_RUNS_BY_DEFAULT
    rate_limits: tuple[RateLimit, ...] = ()
    milestones: tuple[MilestoneFacts, ...] = ()
    integration_branches: tuple[IntegrationBranchFacts, ...] = ()

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "now": format_instant(self.now),
            "waves": [wave.to_document() for wave in self.waves],
            "projects": [project.to_document() for project in self.projects],
            "studies": [study.to_document() for study in self.studies],
            "live_study_runs": [live.to_document() for live in self.live_study_runs],
            "study_runs": self.study_runs,
            "rate_limits": [rate_limit.to_document() for rate_limit in self.rate_limits],
            "milestones": [milestone.to_document() for milestone in self.milestones],
            "integration_branches": [branch.to_document() for branch in self.integration_branches],
        }


def _read_milestone(task: Entity) -> str | None:
    milestone = read_project_field(task, MILESTONE_FIELD)
    return None if milestone is None else milestone.removeprefix(MILESTONE_PREFIX)


def _name_task_branch(task: Entity) -> str:
    task_type = read_project_field(task, TYPE_FIELD)
    if task_type is None:
        raise TaskTypeMissing(f"@TASK.{task.name} carries no TYPE to name its branch")
    return name_task_branch(task_type, task.name, read_project_field(task, TITLE_FIELD))


def _read_task_facts(runtime: Runtime, root: Path, task: Entity) -> TaskFacts:
    return TaskFacts(
        name=task.name,
        branch=_name_task_branch(task),
        after=tuple(field.value.removeprefix(TASK_PREFIX) for field in task.fields if field.name == AFTER_FIELD),
        blocked_by=runtime.read_live_blockers(runtime.run_process, root, task.name),
        milestone=_read_milestone(task),
    )


@dataclass(frozen=True)
class FollowedWave:
    repository: Path
    worktree_root: str | None
    states: dict
    opened_pull_requests: dict
    pull_request_openings: dict
    preflighted_heads: dict
    verdicts: dict
    reviewed_heads: dict
    preflight_failures: dict
    repair_rounds: dict
    reported_tasks: frozenset
    read_pull_request: Callable[[str, str], PullRequestFacts | None]
    run_process: Callable[[ProcessRequest], ProcessRecord]


def _follow_task(task: TaskFacts, followed: FollowedWave, implemented: tuple[str, ...]) -> TaskFacts:
    state = followed.states.get(task.name, QUEUED_STATE)
    worktree = locate_scheduled_worktree(followed.repository, followed.worktree_root, task.name)
    standing = worktree.is_dir()
    if (state == QUEUED_STATE and task.name not in implemented) or (state in SETTLED_STATES and not standing):
        return task
    pull_request = followed.read_pull_request(str(followed.repository), task.branch)
    return dataclasses.replace(
        task,
        pull_request=pull_request,
        worktree=str(worktree) if standing else None,
        opened_pull_request=followed.opened_pull_requests.get(task.name),
        opening_of_its_pull_request=(
            None if pull_request is None else followed.pull_request_openings.get((task.name, pull_request.number))
        ),
        preflighted_head=followed.preflighted_heads.get(task.name),
        verdict=followed.verdicts.get(task.name),
        reviewed_head=followed.reviewed_heads.get(task.name),
        preflight_failures=followed.preflight_failures.get(task.name, ()),
        repair_rounds=followed.repair_rounds.get(task.name, 0),
        reported=task.name in followed.reported_tasks,
        holds_uncommitted_changes=standing and has_uncommitted_changes(followed.run_process, worktree),
    )


def _list_preflight_failures(preflighted: TaskPreflighted) -> tuple[PreflightFailure, ...]:
    return tuple(
        PreflightFailure(name=check["name"], findings=tuple(check["findings"]))
        for check in preflighted.checks
        if check["verdict"] == FAILED_PREFLIGHT_CHECK
    )


@dataclass(frozen=True)
class ForgeReaders:
    read_pull_request: Callable[[str, str], PullRequestFacts | None]
    read_environment: Callable[[str], dict]


@dataclass(frozen=True)
class WaveReading:
    configuration: Configuration
    entries: tuple[LedgerEntry, ...]
    events: tuple
    live_runs: frozenset[str]
    runs: tuple[dict, ...]
    projects: tuple[Entity, ...]
    forge: ForgeReaders


def _is_verification_fact(event, wave: str, task: str) -> bool:
    return isinstance(event, TaskPreflighted | TaskVerdict) and event.wave == wave and event.task == task


def _list_events_since_requeue(events: tuple, wave: str) -> tuple:
    kept = []
    for event in events:
        if is_requeue(event, wave):
            kept = [held for held in kept if not _is_verification_fact(held, wave, event.task)]
        kept.append(event)
    return tuple(kept)


def _read_wave_facts(runtime: Runtime, reading: WaveReading, started: WaveStarted) -> WaveFacts | None:
    try:
        return _collect_wave_facts(runtime, reading, started)
    except (CommandFailed, TaskTypeMissing) as failure:
        sys.stderr.write(f"brigade tick: the wave {started.wave} skipped: {failure}\n")
        return None


def _list_task_runs(reading: WaveReading, wave: str, task: str) -> list[RunFinished]:
    return [
        event
        for event in reading.events
        if isinstance(event, RunFinished) and event.wave == wave and event.task == task
    ]


def _is_quota_event_of_task(event, wave: str, task: str) -> bool:
    if isinstance(event, RunFinished):
        return event.wave == wave and event.task == task
    return (
        isinstance(event, TaskState)
        and event.wave == wave
        and event.task == task
        and event.reason == QUOTA_RESUME_REASON
    )


def _read_rate_limit(reading: WaveReading, wave: str, task: str) -> RateLimit | None:
    quota_events = [event for event in reading.events if _is_quota_event_of_task(event, wave, task)]
    if not quota_events or not isinstance(quota_events[-1], RunFinished):
        return None
    last = quota_events[-1]
    if last.error_class != RATE_LIMIT or last.run in reading.live_runs:
        return None
    return RateLimit(reset=last.reset)


def _read_rate_limits(reading: WaveReading, now: datetime) -> tuple[RateLimit, ...]:
    return tuple(
        RateLimit(reset=entry.event.reset)
        for entry in reading.entries
        if isinstance(entry.event, RunFinished)
        and entry.event.error_class == RATE_LIMIT
        and entry.event.run not in reading.live_runs
        and decide_resume_at(entry.instant, entry.event.reset) > now
    )


def _is_forge_account_unavailable(entries: tuple[LedgerEntry, ...]) -> bool:
    unavailable = [entry.instant for entry in entries if isinstance(entry.event, ForgeAccountUnavailable)]
    cleared = [
        entry.instant
        for entry in entries
        if isinstance(entry.event, WaveResumed) and entry.event.reason == FORGE_ACCOUNT_REASON
    ]
    return bool(unavailable) and max(unavailable) > max(cleared, default=BEFORE_ANY_EVENT)


def _read_state_before_pause(reading: WaveReading, wave: str, task: str) -> str | None:
    held = [
        event.state
        for event in reading.events
        if isinstance(event, TaskState)
        and event.wave == wave
        and event.task == task
        and event.state != PAUSED_ON_QUOTA_STATE
    ]
    return held[-1] if held else None


def _note_quota(task: TaskFacts, reading: WaveReading, wave: str, states: dict) -> TaskFacts:
    if states.get(task.name) == PAUSED_ON_QUOTA_STATE:
        return dataclasses.replace(
            task,
            stopped_run=_list_task_runs(reading, wave, task.name)[-1].run,
            resumed_state=_read_state_before_pause(reading, wave, task.name),
        )
    if states.get(task.name) not in QUOTA_PAUSED_STATES:
        return task
    return dataclasses.replace(task, rate_limit=_read_rate_limit(reading, wave, task.name))


def _read_blocked_run(reading: WaveReading, run: str) -> BlockedRun | None:
    finished = [event for event in reading.events if isinstance(event, RunFinished) and event.run == run]
    if not finished or finished[-1].outcome != BLOCKED_OUTCOME:
        return None
    return BlockedRun(run=run, question=read_run_question(finished[-1].message))


def _is_blocked_run_answered(event, wave: str, run: str) -> bool:
    if isinstance(event, WaveResumed):
        return event.wave == wave and event.reason != QUOTA_REASON
    return isinstance(event, WavePaused) and event.wave == wave and event.reason.startswith(f"run {run} blocked")


def _read_blocked_rebase(reading: WaveReading, wave: str) -> BlockedRun | None:
    naming = [run for run in reading.runs if run["wave"] == wave and run["task"] is None and run["slot"] == REBASE_SLOT]
    if not naming:
        return None
    run = naming[-1]["run"]
    finished = [
        index for index, event in enumerate(reading.events) if isinstance(event, RunFinished) and event.run == run
    ]
    if not finished or any(_is_blocked_run_answered(event, wave, run) for event in reading.events[finished[-1] :]):
        return None
    return _read_blocked_run(reading, run)


def _is_rebase_done(reading: WaveReading, run: dict) -> bool:
    finished = [event for event in reading.events if isinstance(event, RunFinished) and event.run == run["run"]]
    return run["slot"] == REBASE_SLOT and bool(finished) and finished[-1].outcome == DONE_OUTCOME


def _note_last_run(task: TaskFacts, reading: WaveReading, wave: str) -> TaskFacts:
    naming = [run for run in reading.runs if run["wave"] == wave and run["task"] == task.name]
    if not naming:
        return task
    return dataclasses.replace(
        task,
        last_run=naming[-1]["run"],
        blocked_run=_read_blocked_run(reading, naming[-1]["run"]),
        rebased_by_last_run=_is_rebase_done(reading, naming[-1]),
        last_run_is_a_rebase=naming[-1]["slot"] == REBASE_SLOT,
    )


def _is_review_ended_within_quota(event, wave: str) -> bool:
    return (
        isinstance(event, RunFinished)
        and event.slot == REVIEW_SLOT
        and event.wave == wave
        and event.error_class != RATE_LIMIT
    )


def _read_reviewed_heads(events: tuple, wave: str) -> dict:
    preflighted = {}
    reviewed = {}
    for event in events:
        if isinstance(event, TaskPreflighted) and event.wave == wave:
            preflighted[event.task] = event.head
            reviewed.pop(event.task, None)
        if _is_review_ended_within_quota(event, wave):
            reviewed[event.task] = preflighted.get(event.task)
    return reviewed


@dataclass(frozen=True)
class _OpenWave:
    started: WaveStarted
    tree_root: Path
    followed: FollowedWave
    implemented: tuple[str, ...]


def _locate_wave_repository(reading: WaveReading, started: WaveStarted) -> Path:
    return Path(read_project_field(find_project(reading.projects, started.project), PATH_FIELD))


def _read_no_pull_request(repository: str, branch: str) -> None:
    return None


def _choose_pull_request_reader(reading: WaveReading, started: WaveStarted) -> Callable:
    if is_on_github(find_project(reading.projects, started.project)):
        return reading.forge.read_pull_request
    return _read_no_pull_request


def _read_preflighted_heads(events: tuple, wave: str) -> dict:
    return {event.task: event.head for event in events if isinstance(event, TaskPreflighted) and event.wave == wave}


def _read_reported_tasks(events: tuple, project: str) -> frozenset[str]:
    return frozenset(event.task for event in events if isinstance(event, TaskReported) and event.project == project)


def _read_pull_request_openings(events: tuple, project: str) -> dict:
    return {
        (event.task, event.pr): event
        for event in events
        if isinstance(event, TaskPrOpened) and event.project == project
    }


def _follow_wave(runtime: Runtime, reading: WaveReading, started: WaveStarted, states: dict) -> FollowedWave:
    wave = started.wave
    since_requeue = _list_events_since_requeue(reading.events, wave)
    return FollowedWave(
        repository=_locate_wave_repository(reading, started),
        worktree_root=reading.configuration.worktree_root,
        states=states,
        opened_pull_requests={
            event.task: event.pr for event in reading.events if isinstance(event, TaskPrOpened) and event.wave == wave
        },
        pull_request_openings=_read_pull_request_openings(reading.events, started.project),
        preflighted_heads=_read_preflighted_heads(since_requeue, wave),
        verdicts={
            event.task: RecordedVerdict(head=event.head, verdict=event.verdict)
            for event in since_requeue
            if isinstance(event, TaskVerdict) and event.wave == wave
        },
        reviewed_heads=_read_reviewed_heads(since_requeue, wave),
        preflight_failures={
            event.task: _list_preflight_failures(event)
            for event in since_requeue
            if isinstance(event, TaskPreflighted) and event.wave == wave
        },
        repair_rounds=count_repair_rounds(reading.entries, reading.runs, wave),
        reported_tasks=_read_reported_tasks(reading.events, started.project),
        read_pull_request=_choose_pull_request_reader(reading, started),
        run_process=runtime.run_process,
    )


def _read_task_on_its_pull_request(
    runtime: Runtime, reading: WaveReading, open_wave: _OpenWave, task: TaskFacts
) -> Entity | None:
    if task.pull_request is None or task.pull_request.state != OPEN_PULL_REQUEST:
        return None
    query = argparse.Namespace(project=open_wave.started.project, ref=task.pull_request.head, worktree=None)
    tree = prepare_project_tree(query, reading.configuration, runtime)
    return read_entity(runtime.run_process, tree.root, TASK_TYPE, task.name)


def _read_specified_fields(entity: Entity) -> tuple:
    return tuple(field for field in entity.fields if field.name not in PROMOTION_FIELDS)


def _note_amendment(task: TaskFacts, on_pull_request: Entity | None, on_wave: Entity) -> TaskFacts:
    if on_pull_request is None or _read_specified_fields(on_pull_request) == _read_specified_fields(on_wave):
        return task
    return dataclasses.replace(task, amendment=TaskAmendment(on_pull_request=on_pull_request, on_wave=on_wave))


def _is_delivered_by_a_build_run(reading: WaveReading, open_wave: _OpenWave, task: TaskFacts) -> bool:
    finished = [event for event in reading.events if isinstance(event, RunFinished) and event.run == task.last_run]
    return (
        not is_on_github(find_project(reading.projects, open_wave.started.project))
        and not task.last_run_is_a_rebase
        and bool(finished)
        and finished[-1].outcome == DONE_OUTCOME
    )


def _note_delivered_head(reading: WaveReading, open_wave: _OpenWave, task: TaskFacts) -> TaskFacts:
    if not _is_delivered_by_a_build_run(reading, open_wave, task):
        return task
    followed = open_wave.followed
    return dataclasses.replace(
        task, delivered_head=resolve_commit(followed.run_process, followed.repository, task.branch)
    )


def _read_wave_task(runtime: Runtime, reading: WaveReading, open_wave: _OpenWave, task: Entity) -> TaskFacts:
    wave = open_wave.started.wave
    followed = _follow_task(
        _read_task_facts(runtime, open_wave.tree_root, task), open_wave.followed, open_wave.implemented
    )
    amended = _note_amendment(followed, _read_task_on_its_pull_request(runtime, reading, open_wave, followed), task)
    noted = _note_last_run(_note_quota(amended, reading, wave, open_wave.followed.states), reading, wave)
    return _note_delivered_head(reading, open_wave, noted)


def _open_wave(runtime: Runtime, reading: WaveReading, started: WaveStarted, tree_root: Path) -> _OpenWave:
    states = read_task_states(reading.entries, started.wave)
    return _OpenWave(
        started=started,
        tree_root=tree_root,
        followed=_follow_wave(runtime, reading, started, states),
        implemented=read_implemented_tasks(runtime.run_process, tree_root),
    )


def _find_wave_base(project: Entity, tasks: tuple[TaskFacts, ...], milestone_branch: str | None) -> str | None:
    if tasks[0].milestone is None:
        return read_project_field(project, MAIN_FIELD)
    return milestone_branch


def _collect_wave_facts(runtime: Runtime, reading: WaveReading, started: WaveStarted) -> WaveFacts:
    project = find_project(reading.projects, started.project)
    tree = prepare_wave_tree(
        runtime,
        WaveTreeReading(configuration=reading.configuration, read_environment=reading.forge.read_environment),
        started,
    )
    tasks = {task.name: task for task in read_entities(runtime.run_process, tree.root, TASK_TYPE)}
    open_wave = _open_wave(runtime, reading, started, tree.root)
    wave_tasks = tuple(_read_wave_task(runtime, reading, open_wave, tasks[task]) for task in started.tasks)
    milestone_branch = find_milestone_branch(reading.entries, started.project, wave_tasks[0].milestone)
    return WaveFacts(
        project=started.project,
        wave=started.wave,
        base=_find_wave_base(project, wave_tasks, milestone_branch),
        tasks=wave_tasks,
        states=open_wave.followed.states,
        implemented=open_wave.implemented,
        pause=read_wave_pause(reading.events, started.wave),
        forge_account_unavailable=_is_forge_account_unavailable(reading.entries),
        milestone_branch=milestone_branch,
        blocked_rebase=_read_blocked_rebase(reading, started.wave),
    )


@dataclass(frozen=True)
class _WaveMaking:
    candidates: tuple[CandidateWave, ...]
    uncut_milestones: tuple[UncutMilestone, ...]


NO_WAVE_MAKING = _WaveMaking(candidates=(), uncut_milestones=())


@dataclass(frozen=True)
class _MainReading:
    project: str
    main: ProjectTasks


def _describe_uncut_milestone(
    runtime: Runtime, reading: WaveReading, main: _MainReading, milestone: str
) -> UncutMilestone:
    entity = read_entity(runtime.run_process, main.main.root, MILESTONE_TYPE, milestone)
    tasks = tuple(main.main.by_name.values())
    return UncutMilestone(
        milestone=milestone,
        branch=name_milestone_branch(read_project_field(entity, TITLE_FIELD)),
        open_waves=_list_open_waves(
            reading, main.project, {task.name for task in tasks if _read_milestone(task) == milestone}
        ),
        todo=_list_todo(tasks, milestone),
    )


def _list_uncut_milestones(
    runtime: Runtime, reading: WaveReading, project: str, main: ProjectTasks
) -> tuple[UncutMilestone, ...]:
    if not any(_read_milestone(task) for task in main.by_name.values()):
        return ()
    return tuple(
        _describe_uncut_milestone(runtime, reading, _MainReading(project=project, main=main), milestone)
        for milestone in sorted(
            active.removeprefix(MILESTONE_PREFIX) for active in read_active_milestones(runtime.run_process, main.root)
        )
        if find_milestone_branch(reading.entries, project, milestone) is None
    )


def _read_wave_making(runtime: Runtime, reading: WaveReading, project: Entity) -> _WaveMaking:
    if read_project_field(project, PROJECT_STATUS_FIELD) == PAUSED_PROJECT_STATUS:
        return NO_WAVE_MAKING
    tasks_reading = ProjectTasksReading(
        configuration=reading.configuration,
        project=project,
        read_environment=reading.forge.read_environment,
        entries=reading.entries,
    )
    main = read_project_tasks(runtime, tasks_reading, NO_MILESTONE)
    for held in list_tasks_of_reached_milestones(runtime.run_process, main):
        sys.stderr.write(
            f"brigade tick: @TASK.{held.task} is served never: its milestone {held.milestone} is reached\n"
        )
    return _WaveMaking(
        candidates=list_candidate_waves(runtime, tasks_reading, main),
        uncut_milestones=_list_uncut_milestones(runtime, reading, project.name, main),
    )


def _read_project_facts(runtime: Runtime, reading: WaveReading, project: Entity, runs: list[dict]) -> ProjectFacts:
    slots = read_project_field(project, SLOTS_FIELD)
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    wave_making = _read_wave_making(runtime, reading, project)
    return ProjectFacts(
        name=project.name,
        slots=PROJECT_SLOTS if slots is None else int(slots),
        awaits_check_runs=read_project_field(project, CHECK_RUNS_FIELD) != NO_CHECK_RUNS,
        live_runs=tuple(
            LiveRun(run=run["run"], slot=run["slot"], worktree=run["worktree"], wave=run["wave"], task=run["task"])
            for run in runs
            if run["project"] == project.name and run["state"] == LIVE_RUN_STATE
        ),
        wave_start=read_wave_start(runtime, project.name),
        candidates=wave_making.candidates,
        merge=read_project_field(project, MERGE_FIELD) or REBASE_MERGE,
        review=read_policy_field(policies, project.name, REVIEW_FIELD, VERDICT_REVIEW),
        auto_merge=read_policy_field(policies, project.name, AUTO_MERGE_FIELD, MERGE_INTO_INTEGRATION),
        verify_rounds=int(
            read_policy_field(policies, project.name, VERIFY_ROUNDS_FIELD, str(VERIFY_ROUNDS_BY_DEFAULT))
        ),
        on_github=is_on_github(project),
        uncut_milestones=wave_making.uncut_milestones,
    )


def _read_readable_project_facts(
    runtime: Runtime, reading: WaveReading, project: Entity, runs: list[dict]
) -> ProjectFacts | None:
    try:
        return _read_project_facts(runtime, reading, project, runs)
    except ToolFailure as failure:
        sys.stderr.write(f"brigade tick: the project {project.name} skipped: {failure}\n")
        return None


def _assemble_reading(runtime: Runtime, configuration: Configuration, forge: ForgeReaders) -> WaveReading:
    entries = runtime.read_ledger(runtime.paths.state_root).entries
    runs = list_runs(runtime.paths.state_root)["runs"]
    return WaveReading(
        configuration=configuration,
        entries=entries,
        events=tuple(entry.event for entry in entries),
        live_runs=frozenset(run["run"] for run in runs if run["state"] == LIVE_RUN_STATE),
        runs=tuple(runs),
        projects=read_projects(runtime),
        forge=forge,
    )


def _read_open_waves(runtime: Runtime, reading: WaveReading, projects: frozenset[str]) -> tuple[WaveFacts, ...]:
    return tuple(
        facts
        for facts in (
            _read_wave_facts(runtime, reading, summary.started)
            for summary in summarize_waves(reading.entries)
            if summary.is_open and summary.started.project in projects
        )
        if facts is not None
    )


def _read_registered_projects(runtime: Runtime, reading: WaveReading) -> tuple[ProjectFacts, ...]:
    runs = list(reading.runs)
    return tuple(
        facts
        for facts in (_read_readable_project_facts(runtime, reading, project, runs) for project in reading.projects)
        if facts is not None
    )


def _find_milestone_pull_request(reading: WaveReading, project: str, milestone: str) -> int | None:
    opened = [
        event.pr
        for event in reading.events
        if isinstance(event, MilestonePrOpened) and event.project == project and event.milestone == milestone
    ]
    return opened[-1] if opened else None


def _find_described_head(reading: WaveReading, project: str, milestone: str) -> str | None:
    heads = [
        event.head
        for event in reading.events
        if isinstance(event, MilestonePrDescribed) and (event.project, event.milestone) == (project, milestone)
    ]
    return heads[-1] if heads else None


def _list_closed_waves(reading: WaveReading, project: str, of_milestone: set[str]) -> tuple[str, ...]:
    closed = {event.wave for event in reading.events if isinstance(event, WaveClosed)}
    return tuple(
        event.wave
        for event in reading.events
        if isinstance(event, WaveStarted)
        and event.project == project
        and event.wave in closed
        and of_milestone.intersection(event.tasks)
    )


def _list_todo(tasks: tuple[Entity, ...], milestone: str) -> tuple[str, ...]:
    return tuple(
        task.name
        for task in tasks
        if _read_milestone(task) == milestone and read_task_field(task, STATUS_FIELD) == (TODO_STATUS,)
    )


def _list_open_tasks(tasks: tuple[Entity, ...]) -> tuple[str, ...]:
    return tuple(task.name for task in tasks if read_task_field(task, STATUS_FIELD) in OPEN_TASK_STATUSES)


def _list_open_waves(reading: WaveReading, project: str, of_milestone: set[str]) -> tuple[str, ...]:
    return tuple(
        summary.started.wave
        for summary in summarize_waves(reading.entries)
        if summary.is_open and summary.started.project == project and of_milestone.intersection(summary.started.tasks)
    )


@dataclass(frozen=True)
class MilestoneRefs:
    main: str
    branch: str


def _is_behind_main(runtime: Runtime, reading: WaveReading, cut: MilestoneBranchCut, refs: MilestoneRefs) -> bool:
    project = find_project(reading.projects, cut.project)
    query = argparse.Namespace(project=cut.project, ref=refs.main, worktree=None)
    active = read_active_milestones(
        runtime.run_process, prepare_project_tree(query, reading.configuration, runtime).root
    )
    if MILESTONE_PREFIX + cut.milestone not in active:
        return False
    repository = Path(read_project_field(project, PATH_FIELD))
    return check_ancestor(runtime.run_process, repository, refs.main, refs.branch).exit_code != DESCENDING


def _locate_milestone_refs(runtime: Runtime, reading: WaveReading, project: Entity, ref: str) -> MilestoneRefs:
    main = locate_forge_branch(
        runtime.run_process, project, read_project_field(project, MAIN_FIELD), reading.forge.read_environment
    )
    return MilestoneRefs(main=main, branch=ref)


def _read_blocked_milestone_rebase(
    runtime: Runtime, reading: WaveReading, cut: MilestoneBranchCut, refs: MilestoneRefs
) -> BlockedRun | None:
    project = find_project(reading.projects, cut.project)
    rebase_runs = _list_branch_rebase_runs(reading, project, cut.branch)
    blocked = _read_blocked_run(reading, rebase_runs[-1]["run"]) if rebase_runs else None
    if blocked is None:
        return None
    repository = Path(read_project_field(project, PATH_FIELD))
    heads = MilestoneHeads(
        main=resolve_commit(runtime.run_process, repository, refs.main),
        branch=resolve_commit(runtime.run_process, repository, refs.branch),
    )
    return blocked if is_milestone_rebase_held(reading.events, blocked.run, heads) else None


def _list_branch_rebase_runs(reading: WaveReading, project: Entity, branch: str) -> tuple[dict, ...]:
    repository = Path(read_project_field(project, PATH_FIELD))
    worktree = locate_branch_worktree(repository, reading.configuration.worktree_root, branch)
    return tuple(run for run in reading.runs if run["worktree"] == str(worktree))


def _is_milestone_reported(reading: WaveReading, cut: MilestoneBranchCut) -> bool:
    return any(
        isinstance(event, MilestoneReported) and (event.project, event.milestone) == (cut.project, cut.milestone)
        for event in reading.events
    )


def _read_tasks_of_milestone(runtime: Runtime, reading: WaveReading, cut: MilestoneBranchCut, ref: str) -> list:
    query = argparse.Namespace(project=cut.project, ref=ref, worktree=None)
    tasks = read_entities(
        runtime.run_process, prepare_project_tree(query, reading.configuration, runtime).root, TASK_TYPE
    )
    return [task for task in tasks if _read_milestone(task) == cut.milestone]


def _read_milestone_facts(runtime: Runtime, reading: WaveReading, cut: MilestoneBranchCut) -> MilestoneFacts:
    project = find_project(reading.projects, cut.project)
    opened = _find_milestone_pull_request(reading, cut.project, cut.milestone)
    if opened is not None:
        return MilestoneFacts(
            project=cut.project,
            milestone=cut.milestone,
            branch=cut.branch,
            opened_pull_request=opened,
            pull_request=reading.forge.read_pull_request(read_project_field(project, PATH_FIELD), cut.branch),
            described_head=_find_described_head(reading, cut.project, cut.milestone),
        )
    ref = locate_forge_branch(runtime.run_process, project, cut.branch, reading.forge.read_environment)
    rebase_runs = _list_branch_rebase_runs(reading, project, cut.branch)
    of_milestone = _read_tasks_of_milestone(runtime, reading, cut, ref)
    names = {task.name for task in of_milestone}
    refs = _locate_milestone_refs(runtime, reading, project, ref)
    return MilestoneFacts(
        project=cut.project,
        milestone=cut.milestone,
        branch=cut.branch,
        closed_waves=_list_closed_waves(reading, cut.project, names),
        open_waves=_list_open_waves(reading, cut.project, names),
        open_tasks=_list_open_tasks(tuple(of_milestone)),
        behind_main=_is_behind_main(runtime, reading, cut, refs),
        rebase_run_live=any(run["state"] == LIVE_RUN_STATE for run in rebase_runs),
        blocked_rebase=_read_blocked_milestone_rebase(runtime, reading, cut, refs),
        tasks=tuple(task.name for task in of_milestone),
        reported=_is_milestone_reported(reading, cut),
    )


def _read_readable_milestone_facts(
    runtime: Runtime, reading: WaveReading, cut: MilestoneBranchCut
) -> MilestoneFacts | None:
    try:
        return _read_milestone_facts(runtime, reading, cut)
    except BrigadeError as failure:
        sys.stderr.write(f"brigade tick: the milestone {cut.milestone} of {cut.project} skipped: {failure}\n")
        return None


def _read_milestones(runtime: Runtime, reading: WaveReading, projects: frozenset[str]) -> tuple[MilestoneFacts, ...]:
    cuts = {
        (event.project, event.milestone): event for event in reading.events if isinstance(event, MilestoneBranchCut)
    }
    closed = {(event.project, event.milestone) for event in reading.events if isinstance(event, MilestoneClosed)}
    return tuple(
        facts
        for facts in (
            _read_readable_milestone_facts(runtime, reading, cut)
            for key, cut in cuts.items()
            if key not in closed and cut.project in projects
        )
        if facts is not None
    )


def _read_integration_branches(
    runtime: Runtime, configuration: Configuration, reading: WaveReading, projects: frozenset[str]
) -> tuple[IntegrationBranchFacts, ...]:
    return read_integration_branches(
        runtime.run_process,
        IntegrationBranchReading(
            entries=reading.entries,
            projects=tuple(project for project in reading.projects if project.name in projects),
            worktree_root=configuration.worktree_root,
            state_root=runtime.paths.state_root,
            read_pull_request=reading.forge.read_pull_request,
            read_environment=reading.forge.read_environment,
            locate_wave_base=lambda started: locate_wave_branch_base(
                runtime,
                WaveTreeReading(configuration=configuration, read_environment=reading.forge.read_environment),
                started,
            ),
            is_alive=is_recorded_process_alive,
        ),
    )


def build_snapshot(runtime: Runtime, configuration: Configuration, forge: ForgeReaders) -> Snapshot:
    if not runtime.paths.schema_file.exists():
        return Snapshot(now=runtime.now)
    runtime = dataclasses.replace(runtime, run_process=remember_process_records(runtime.run_process))
    reading = _assemble_reading(runtime, configuration, forge)
    last_orders = read_last_study_orders(reading.entries)
    projects = _read_registered_projects(runtime, reading)
    projects_read = frozenset(project.name for project in projects)
    return Snapshot(
        now=runtime.now.astimezone(),
        waves=_read_open_waves(runtime, reading, projects_read),
        projects=projects,
        studies=tuple(describe_study_facts(study, last_orders.get(study.name)) for study in read_studies(runtime)),
        live_study_runs=read_live_study_runs(runtime.paths.state_root, is_recorded_process_alive),
        study_runs=configuration.study_runs,
        rate_limits=_read_rate_limits(reading, runtime.now),
        milestones=_read_milestones(runtime, reading, projects_read),
        integration_branches=_read_integration_branches(runtime, configuration, reading, projects_read),
    )
