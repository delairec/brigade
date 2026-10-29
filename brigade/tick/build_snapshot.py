import dataclasses
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import CommandFailed, ToolFailure
from brigade.git.has_uncommitted_changes import has_uncommitted_changes
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_policy_field import read_policy_field
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.list_runs import list_runs
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.read_last_study_orders import LastStudyOrder, read_last_study_orders
from brigade.studies.read_live_study_runs import LiveStudyRun, read_live_study_runs
from brigade.studies.read_studies import read_studies
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT
from brigade.system.parse_configuration import Configuration
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.read_study_runs import STUDY_RUNS_BY_DEFAULT
from brigade.system.reset_hour import ResetHour
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tick.decide_resume_at import decide_resume_at
from brigade.tick.locate_scheduled_worktree import locate_scheduled_worktree
from brigade.tick.name_task_branch import name_task_branch
from brigade.tick.read_implemented_tasks import read_implemented_tasks
from brigade.tick.read_live_blockers import read_live_blockers
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.cut_wave_branch import WaveBranchCut
from brigade.waves.find_integration_pull_request import find_integration_pull_request
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_wave_branch_missing import is_wave_branch_missing
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_project_tasks import read_project_tasks
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
MILESTONE_PREFIX = "@MILESTONE."
PROJECT_SLOTS = 4
PARKED_OUTCOME = "parked"
QUEUED_STATE = "queued"
SETTLED_STATES = ("merged", "parked")
PATH_FIELD = "PATH"
RUNNING_STATE = "running"
PAUSED_ON_QUOTA_STATE = "paused:quota"
RATE_LIMIT = "rate_limit"
REVIEW_SLOT = "review"
REBASE_SLOT = "rebase"
BLOCKED_OUTCOME = "blocked"
DONE_OUTCOME = "done"
FORGE_ACCOUNT_REASON = "forge_account"
PROJECT_STATUS_FIELD = "STATUS"
PAUSED_PROJECT_STATUS = "paused"
NO_UNRESOLVED_THREAD = 0
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
FAILED_PREFLIGHT_CHECK = "fail"
BEFORE_ANY_EVENT = datetime.min.replace(tzinfo=UTC)


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
class TaskFacts:
    name: str
    after: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    pull_request: PullRequestFacts | None = None
    worktree: str | None = None
    rate_limit: RateLimit | None = None
    stopped_run: str | None = None
    opened_pull_request: int | None = None
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

    def to_document(self) -> dict:
        return {
            "task": self.name,
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
    branch: str
    tasks: tuple[TaskFacts, ...] = ()
    states: dict = field(default_factory=dict)
    implemented: tuple[str, ...] = ()
    pause: WavePause | None = None
    forge_account_unavailable: bool = False
    branch_missing: bool = False
    reported: bool = False
    integration_pull_request: PullRequestFacts | None = None
    opened_integration_pull_request: int | None = None
    milestone_branch: str | None = None
    unresolved_threads: int = 0

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "branch": self.branch,
            "tasks": [task.to_document() for task in self.tasks],
            "states": dict(self.states),
            "implemented": list(self.implemented),
            "pause": None if self.pause is None else self.pause.to_document(),
            "forge_account_unavailable": self.forge_account_unavailable,
            "branch_missing": self.branch_missing,
            "reported": self.reported,
            "integration_pull_request": (
                None if self.integration_pull_request is None else self.integration_pull_request.to_document()
            ),
            "opened_integration_pull_request": self.opened_integration_pull_request,
            "milestone_branch": self.milestone_branch,
            "unresolved_threads": self.unresolved_threads,
        }


@dataclass(frozen=True)
class LiveRun:
    run: str
    slot: str
    worktree: str
    wave: str | None = None
    task: str | None = None


@dataclass(frozen=True)
class ProjectFacts:
    name: str
    slots: int
    live_runs: tuple[LiveRun, ...] = ()
    awaits_check_runs: bool = True
    wave_start: str = "auto"
    candidates: tuple[str, ...] = ()
    merge: str = REBASE_MERGE
    review: str = VERDICT_REVIEW
    auto_merge: str = MERGE_INTO_INTEGRATION
    verify_rounds: int = VERIFY_ROUNDS_BY_DEFAULT
    on_github: bool = False

    def to_document(self) -> dict:
        return {
            "project": self.name,
            "slots": self.slots,
            "live_runs": [{"run": live.run, "slot": live.slot, "worktree": live.worktree} for live in self.live_runs],
            "wave_start": self.wave_start,
            "candidates": list(self.candidates),
            "merge": self.merge,
            "review": self.review,
            "auto_merge": self.auto_merge,
            "verify_rounds": self.verify_rounds,
            "awaits_check_runs": self.awaits_check_runs,
            "on_github": self.on_github,
        }


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
    studies: tuple[StudyFacts, ...] = ()
    live_study_runs: tuple[LiveStudyRun, ...] = ()
    study_runs: int = STUDY_RUNS_BY_DEFAULT
    rate_limits: tuple[RateLimit, ...] = ()

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
        }


def _read_milestone(task: Entity) -> str | None:
    milestone = read_project_field(task, MILESTONE_FIELD)
    return None if milestone is None else milestone.removeprefix(MILESTONE_PREFIX)


def _read_task_facts(runtime: Runtime, root: Path, task: Entity) -> TaskFacts:
    return TaskFacts(
        name=task.name,
        after=tuple(field.value.removeprefix(TASK_PREFIX) for field in task.fields if field.name == AFTER_FIELD),
        blocked_by=read_live_blockers(runtime.run_process, root, task.name),
        milestone=_read_milestone(task),
    )


@dataclass(frozen=True)
class FollowedWave:
    repository: Path
    worktree_root: str | None
    branch: str
    states: dict
    opened_pull_requests: dict
    preflighted_heads: dict
    verdicts: dict
    reviewed_heads: dict
    preflight_failures: dict
    repair_rounds: dict
    read_pull_request: Callable[[str, str], PullRequestFacts | None]
    run_process: Callable[[ProcessRequest], ProcessRecord]


def _follow_task(task: TaskFacts, followed: FollowedWave, implemented: tuple[str, ...]) -> TaskFacts:
    state = followed.states.get(task.name, QUEUED_STATE)
    worktree = locate_scheduled_worktree(followed.repository, followed.worktree_root, task.name)
    standing = worktree.is_dir()
    if (state == QUEUED_STATE and task.name not in implemented) or (state in SETTLED_STATES and not standing):
        return task
    return dataclasses.replace(
        task,
        pull_request=followed.read_pull_request(str(followed.repository), name_task_branch(followed.branch, task.name)),
        worktree=str(worktree) if standing else None,
        opened_pull_request=followed.opened_pull_requests.get(task.name),
        preflighted_head=followed.preflighted_heads.get(task.name),
        verdict=followed.verdicts.get(task.name),
        reviewed_head=followed.reviewed_heads.get(task.name),
        preflight_failures=followed.preflight_failures.get(task.name, ()),
        repair_rounds=followed.repair_rounds.get(task.name, 0),
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
    count_unresolved_threads: Callable[[str, int], int]


@dataclass(frozen=True)
class WaveReading:
    configuration: Configuration
    entries: tuple[LedgerEntry, ...]
    events: tuple
    live_runs: frozenset[str]
    runs: tuple[dict, ...]
    projects: tuple[Entity, ...]
    forge: ForgeReaders


def _is_rebase_launch(entry: LedgerEntry, runs: tuple[dict, ...]) -> bool:
    launched = f"{entry.instant.astimezone(UTC).strftime(COMPACT_INSTANT_FORMAT)}-"
    return any(
        run["slot"] == REBASE_SLOT
        and run["wave"] == entry.event.wave
        and run["task"] == entry.event.task
        and run["run"].startswith(launched)
        for run in runs
    )


def _count_repair_rounds(reading: WaveReading, wave: str) -> dict:
    rounds = {}
    for entry in reading.entries:
        event = entry.event
        if (
            isinstance(event, TaskState)
            and event.wave == wave
            and event.state == FIXING_STATE
            and not _is_rebase_launch(entry, reading.runs)
        ):
            rounds[event.task] = rounds.get(event.task, 0) + 1
    return rounds


def _read_wave_facts(runtime: Runtime, reading: WaveReading, started: WaveStarted) -> WaveFacts | None:
    try:
        return _collect_wave_facts(runtime, reading, started)
    except CommandFailed as failure:
        sys.stderr.write(f"brigade tick: the wave {started.wave} skipped: {failure}\n")
        return None


def _list_task_runs(reading: WaveReading, wave: str, task: str) -> list[RunFinished]:
    return [
        event
        for event in reading.events
        if isinstance(event, RunFinished) and event.wave == wave and event.task == task
    ]


def _read_rate_limit(reading: WaveReading, wave: str, task: str) -> RateLimit | None:
    finished = _list_task_runs(reading, wave, task)
    if not finished or finished[-1].error_class != RATE_LIMIT or finished[-1].run in reading.live_runs:
        return None
    return RateLimit(reset=finished[-1].reset)


def _read_rate_limits(reading: WaveReading, now: datetime) -> tuple[RateLimit, ...]:
    return tuple(
        RateLimit(reset=entry.event.reset)
        for entry in reading.entries
        if isinstance(entry.event, RunFinished)
        and entry.event.error_class == RATE_LIMIT
        and entry.event.run not in reading.live_runs
        and decide_resume_at(entry.instant, entry.event.reset) > now
    )


def _is_forge_account_unavailable(entries: tuple[LedgerEntry, ...], wave: str) -> bool:
    unavailable = [entry.instant for entry in entries if isinstance(entry.event, ForgeAccountUnavailable)]
    cleared = [
        entry.instant
        for entry in entries
        if isinstance(entry.event, WaveResumed)
        and entry.event.wave == wave
        and entry.event.reason == FORGE_ACCOUNT_REASON
    ]
    return bool(unavailable) and max(unavailable) > max(cleared, default=BEFORE_ANY_EVENT)


def _note_quota(task: TaskFacts, reading: WaveReading, wave: str, states: dict) -> TaskFacts:
    if states.get(task.name) == PAUSED_ON_QUOTA_STATE:
        return dataclasses.replace(task, stopped_run=_list_task_runs(reading, wave, task.name)[-1].run)
    if states.get(task.name) != RUNNING_STATE:
        return task
    return dataclasses.replace(task, rate_limit=_read_rate_limit(reading, wave, task.name))


def _read_question(message: str | None) -> str:
    if message is None:
        return ""
    return " ".join(line.strip() for line in message.splitlines()[:-1] if line.strip())


def _read_blocked_run(reading: WaveReading, run: str) -> BlockedRun | None:
    finished = [event for event in reading.events if isinstance(event, RunFinished) and event.run == run]
    if not finished or finished[-1].outcome != BLOCKED_OUTCOME:
        return None
    return BlockedRun(run=run, question=_read_question(finished[-1].message))


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


def _is_reported(reading: WaveReading, wave: str) -> bool:
    return any(isinstance(event, WaveReported) and event.wave == wave for event in reading.events)


@dataclass(frozen=True)
class _OpenWave:
    started: WaveStarted
    tree_root: Path
    followed: FollowedWave
    implemented: tuple[str, ...]


def _locate_wave_repository(reading: WaveReading, started: WaveStarted) -> Path:
    return Path(read_project_field(find_project(reading.projects, started.project), PATH_FIELD))


def _follow_wave(runtime: Runtime, reading: WaveReading, started: WaveStarted, states: dict) -> FollowedWave:
    wave = started.wave
    return FollowedWave(
        repository=_locate_wave_repository(reading, started),
        worktree_root=reading.configuration.worktree_root,
        branch=started.branch,
        states=states,
        opened_pull_requests={
            event.task: event.pr for event in reading.events if isinstance(event, TaskPrOpened) and event.wave == wave
        },
        preflighted_heads={
            event.task: event.head
            for event in reading.events
            if isinstance(event, TaskPreflighted) and event.wave == wave
        },
        verdicts={
            event.task: RecordedVerdict(head=event.head, verdict=event.verdict)
            for event in reading.events
            if isinstance(event, TaskVerdict) and event.wave == wave
        },
        reviewed_heads=_read_reviewed_heads(reading.events, wave),
        preflight_failures={
            event.task: _list_preflight_failures(event)
            for event in reading.events
            if isinstance(event, TaskPreflighted) and event.wave == wave
        },
        repair_rounds=_count_repair_rounds(reading, wave),
        read_pull_request=reading.forge.read_pull_request,
        run_process=runtime.run_process,
    )


def _read_wave_task(runtime: Runtime, reading: WaveReading, open_wave: _OpenWave, task: Entity) -> TaskFacts:
    wave = open_wave.started.wave
    followed = _follow_task(
        _read_task_facts(runtime, open_wave.tree_root, task), open_wave.followed, open_wave.implemented
    )
    return _note_last_run(_note_quota(followed, reading, wave, open_wave.followed.states), reading, wave)


def _open_wave(runtime: Runtime, reading: WaveReading, started: WaveStarted, tree_root: Path) -> _OpenWave:
    states = read_task_states(runtime.paths.state_root, started.wave)
    return _OpenWave(
        started=started,
        tree_root=tree_root,
        followed=_follow_wave(runtime, reading, started, states),
        implemented=read_implemented_tasks(runtime.run_process, tree_root),
    )


@dataclass(frozen=True)
class _WavePullRequest:
    facts: PullRequestFacts | None
    milestone_branch: str | None
    unresolved_threads: int


def _read_wave_pull_request(
    reading: WaveReading, open_wave: _OpenWave, tasks: tuple[TaskFacts, ...]
) -> _WavePullRequest:
    started = open_wave.started
    milestone_branch = find_milestone_branch(reading.entries, started.project, tasks[0].milestone)
    if not _is_reported(reading, started.wave):
        return _WavePullRequest(facts=None, milestone_branch=milestone_branch, unresolved_threads=NO_UNRESOLVED_THREAD)
    repository = open_wave.followed.repository
    facts = reading.forge.read_pull_request(str(repository), started.branch)
    if facts is None or facts.base != milestone_branch:
        return _WavePullRequest(facts=facts, milestone_branch=milestone_branch, unresolved_threads=NO_UNRESOLVED_THREAD)
    threads = reading.forge.count_unresolved_threads(str(repository), facts.number)
    return _WavePullRequest(facts=facts, milestone_branch=milestone_branch, unresolved_threads=threads)


def _collect_wave_facts(runtime: Runtime, reading: WaveReading, started: WaveStarted) -> WaveFacts:
    project = find_project(reading.projects, started.project)
    cut = WaveBranchCut(project=project, branch=started.branch, read_environment=reading.forge.read_environment)
    if is_wave_branch_missing(runtime.run_process, cut):
        return WaveFacts(project=started.project, wave=started.wave, branch=started.branch, branch_missing=True)
    tree = prepare_wave_tree(runtime, reading.configuration, started)
    tasks = {task.name: task for task in read_entities(runtime.run_process, tree.root, TASK_TYPE)}
    open_wave = _open_wave(runtime, reading, started, tree.root)
    wave_tasks = tuple(_read_wave_task(runtime, reading, open_wave, tasks[task]) for task in started.tasks)
    pull_request = _read_wave_pull_request(reading, open_wave, wave_tasks)
    return WaveFacts(
        project=started.project,
        wave=started.wave,
        branch=started.branch,
        tasks=wave_tasks,
        states=open_wave.followed.states,
        implemented=open_wave.implemented,
        pause=read_wave_pause(reading.events, started.wave),
        forge_account_unavailable=_is_forge_account_unavailable(reading.entries, started.wave),
        reported=_is_reported(reading, started.wave),
        integration_pull_request=pull_request.facts,
        opened_integration_pull_request=find_integration_pull_request(reading.events, started.wave),
        milestone_branch=pull_request.milestone_branch,
        unresolved_threads=pull_request.unresolved_threads,
    )


def _read_candidates(runtime: Runtime, reading: WaveReading, project: Entity) -> tuple[str, ...]:
    if read_project_field(project, PROJECT_STATUS_FIELD) == PAUSED_PROJECT_STATUS:
        return ()
    tasks = read_project_tasks(runtime, reading.configuration, project, reading.forge.read_environment)
    return admit_candidates(runtime.run_process, tasks, map_open_tasks(reading.entries, project.name))


def _read_project_facts(runtime: Runtime, reading: WaveReading, project: Entity, runs: list[dict]) -> ProjectFacts:
    slots = read_project_field(project, SLOTS_FIELD)
    policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
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
        candidates=_read_candidates(runtime, reading, project),
        merge=read_project_field(project, MERGE_FIELD) or REBASE_MERGE,
        review=read_policy_field(policies, project.name, REVIEW_FIELD, VERDICT_REVIEW),
        auto_merge=read_policy_field(policies, project.name, AUTO_MERGE_FIELD, MERGE_INTO_INTEGRATION),
        verify_rounds=int(
            read_policy_field(policies, project.name, VERIFY_ROUNDS_FIELD, str(VERIFY_ROUNDS_BY_DEFAULT))
        ),
        on_github=is_on_github(project),
    )


def _read_readable_project_facts(
    runtime: Runtime, reading: WaveReading, project: Entity, runs: list[dict]
) -> ProjectFacts | None:
    try:
        return _read_project_facts(runtime, reading, project, runs)
    except ToolFailure as failure:
        sys.stderr.write(f"brigade tick: the project {project.name} skipped: {failure}\n")
        return None


def _describe_study(study: Study, last_order: LastStudyOrder | None) -> StudyFacts:
    return StudyFacts(
        name=study.name,
        slot=study.slot,
        every=study.every,
        status=study.status,
        last_started=None if last_order is None else last_order.started,
        parked=last_order is not None and last_order.outcome == PARKED_OUTCOME,
    )


def _assemble_reading(runtime: Runtime, configuration: Configuration, forge: ForgeReaders) -> WaveReading:
    entries = read_ledger(runtime.paths.state_root).entries
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


def _read_open_waves(runtime: Runtime, reading: WaveReading) -> tuple[WaveFacts, ...]:
    return tuple(
        facts
        for facts in (
            _read_wave_facts(runtime, reading, summary.started)
            for summary in summarize_waves(reading.entries)
            if summary.is_open
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


def build_snapshot(runtime: Runtime, configuration: Configuration, forge: ForgeReaders) -> Snapshot:
    if not runtime.paths.schema_file.exists():
        return Snapshot(now=runtime.now)
    reading = _assemble_reading(runtime, configuration, forge)
    last_orders = read_last_study_orders(runtime.paths.state_root)
    return Snapshot(
        now=runtime.now.astimezone(),
        waves=_read_open_waves(runtime, reading),
        projects=_read_registered_projects(runtime, reading),
        studies=tuple(_describe_study(study, last_orders.get(study.name)) for study in read_studies(runtime)),
        live_study_runs=read_live_study_runs(runtime.paths.state_root, is_recorded_process_alive),
        study_runs=configuration.study_runs,
        rate_limits=_read_rate_limits(reading, runtime.now),
    )
