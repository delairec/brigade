import dataclasses
from datetime import datetime, timedelta

from brigade.errors import BrigadeError
from brigade.ledger.format_instant import format_instant
from brigade.studies.read_schedule import read_schedule
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.tasks.read_task_number import read_task_number
from brigade.tick.actions import (
    CloseMilestone,
    CloseWave,
    CutWaveBranch,
    LaunchCheckRepair,
    LaunchRemediation,
    LaunchStudy,
    LaunchTask,
    LaunchVerification,
    MergePullRequest,
    MergeWavePullRequest,
    OpenIntegrationPullRequest,
    OpenMilestonePullRequest,
    ParkTask,
    PauseWave,
    RebaseMilestone,
    RebaseTask,
    RecordTaskState,
    RemoveTaskWorktree,
    ReportWave,
    ResumeTaskRun,
    ResumeWave,
    RunPreflight,
    StartWave,
)
from brigade.tick.build_snapshot import (
    SETTLED_STATES,
    BlockedRun,
    MilestoneFacts,
    ProjectFacts,
    Snapshot,
    StudyFacts,
    TaskFacts,
    WaveFacts,
)
from brigade.tick.decide_resume_at import decide_resume_at
from brigade.waves.read_task_state import PARKED_STATE

BUILD_SLOT = "build"
WAITING_STATE = "queued"
MERGED_STATE = "merged"
RUNNING_STATE = "running"
PR_OPEN_STATE = "pr_open"
VERIFYING_STATE = "verifying"
VERIFIED_STATE = "verified"
CHANGES_REQUESTED_STATE = "changes_requested"
FIXING_STATE = "fixing"
AWAITING_PUSH_STATES = (VERIFYING_STATE, CHANGES_REQUESTED_STATE, FIXING_STATE)
REPAIRED_STATES = (PR_OPEN_STATE, CHANGES_REQUESTED_STATE, FIXING_STATE)
REBASED_STATES = (PR_OPEN_STATE, VERIFYING_STATE, VERIFIED_STATE, CHANGES_REQUESTED_STATE, FIXING_STATE)
CHECKS_FINDING = "checks"
UNREQUESTED_FINDINGS = ("ancestry", CHECKS_FINDING)
STATES_BY_VERDICT = {"pass": VERIFIED_STATE, "changes": CHANGES_REQUESTED_STATE}
OPEN_PULL_REQUEST = "open"
PENDING_VERDICT = "pending"
MERGED_PULL_REQUEST = "merged"
CLOSED_PULL_REQUEST = "closed"
SETTLED_PULL_REQUESTS = (MERGED_PULL_REQUEST, CLOSED_PULL_REQUEST)
CLOSED_REASON = "pull request closed"
ACTIVE_STATUS = "active"
SCAN_SLOT = "none"
PAUSED_ON_QUOTA_STATE = "paused:quota"
QUOTA_REASON = "quota"
FORGE_ACCOUNT_REASON = "forge_account"
AUTOMATIC_WAVE_START = "auto"
BLOCKED_REASON = "blocked"
APPROVAL_REVIEW = "approval"
APPROVED_REVIEW = "approved"
LOCAL_REVIEW = "local"
NO_AUTO_MERGE = "none"
PASSING_VERDICT = "pass"
SUCCESSFUL_CHECK = "success"
OTHER_BASE_REASON = "pull request base is not the wave branch"
RUN_DEAD_REASON = "run dead"
RUN_NOT_STARTED_REASON = "run not started"
CHECK_SUITE_CREATION_DELAY = timedelta(minutes=1)


def plan(snapshot: Snapshot) -> tuple:
    pauses = _plan_blocked_rebase_pauses(snapshot) + _plan_pauses(snapshot)
    paused = {wave.wave for wave in snapshot.waves if wave.pause is not None} | {
        pause.wave for pause in pauses if isinstance(pause, PauseWave)
    }
    return (
        pauses
        + _plan_resumes(snapshot)
        + _plan_followed_pull_requests(snapshot)
        + _plan_blocked_task_parkings(snapshot)
        + _plan_dead_run_parkings(snapshot)
        + _plan_branch_cuts(snapshot)
        + _plan_reports(snapshot)
        + _plan_wave_merges(snapshot)
        + _plan_closes(snapshot)
        + _plan_integration_pull_requests(snapshot)
        + _plan_milestone_pull_requests(snapshot)
        + _plan_milestone_closes(snapshot)
        + _plan_launches(snapshot, paused)
        + _plan_milestone_rebases(snapshot)
        + _plan_wave_starts(snapshot)
        + _plan_studies(snapshot)
    )


def _plan_launches(snapshot: Snapshot, paused: set) -> tuple:
    free_slots = {project.name: _count_free_slots(project) for project in snapshot.projects}
    live_tasks = _read_occupancy(snapshot).tasks
    launches = []
    for wave in (wave for wave in snapshot.waves if wave.wave not in paused):
        for task in sorted(
            (task for task in wave.tasks if _is_startable(task, wave) or _is_rebased(task, wave, live_tasks)),
            key=lambda task: read_task_number(task.name, wave.wave),
        ):
            if free_slots[wave.project] <= 0:
                break
            free_slots[wave.project] -= 1
            launches.append(LaunchTask(project=wave.project, wave=wave.wave, branch=wave.branch, task=task.name))
    return tuple(launches)


def _decide_quota_resume_at(snapshot: Snapshot) -> datetime | None:
    pauses_in_force = [
        wave.pause.resume_at
        for wave in snapshot.waves
        if wave.pause is not None and wave.pause.reason == QUOTA_REASON and wave.pause.resume_at > snapshot.now
    ]
    if pauses_in_force:
        return max(pauses_in_force)
    if snapshot.rate_limits:
        return max(decide_resume_at(snapshot.now, rate_limit.reset) for rate_limit in snapshot.rate_limits)
    return None


def _plan_pauses(snapshot: Snapshot) -> tuple:
    unpaused = [wave for wave in snapshot.waves if wave.pause is None]
    stopped_tasks = tuple(
        RecordTaskState(wave=wave.wave, task=task.name, state=PAUSED_ON_QUOTA_STATE, reason=None)
        for wave in snapshot.waves
        for task in wave.tasks
        if task.rate_limit is not None
    )
    resume_at = _decide_quota_resume_at(snapshot)
    if resume_at is None:
        return (
            tuple(
                PauseWave(wave=wave.wave, reason=FORGE_ACCOUNT_REASON, resume_at=None)
                for wave in unpaused
                if wave.forge_account_unavailable
            )
            + stopped_tasks
        )
    return (
        tuple(PauseWave(wave=wave.wave, reason=QUOTA_REASON, resume_at=format_instant(resume_at)) for wave in unpaused)
        + stopped_tasks
    )


def _plan_blocked_rebase_pauses(snapshot: Snapshot) -> tuple:
    return tuple(
        PauseWave(
            wave=wave.wave,
            reason=_describe_blocked_run(wave.blocked_rebase),
            resume_at=None,
        )
        for wave in snapshot.waves
        if wave.pause is None and wave.blocked_rebase is not None
    )


def _is_quota_over(wave: WaveFacts, snapshot: Snapshot) -> bool:
    return wave.pause.reason == QUOTA_REASON and wave.pause.resume_at <= snapshot.now


def _plan_resumes(snapshot: Snapshot) -> tuple:
    actions = []
    for wave in snapshot.waves:
        if wave.pause is not None and not _is_quota_over(wave, snapshot):
            continue
        if wave.pause is not None:
            actions.append(ResumeWave(wave=wave.wave, reason=QUOTA_REASON))
        actions.extend(
            ResumeTaskRun(wave=wave.wave, task=task.name, run=task.stopped_run, state=task.resumed_state)
            for task in wave.tasks
            if wave.states.get(task.name) == PAUSED_ON_QUOTA_STATE
        )
    return tuple(actions)


def _decide_task_state(wave: WaveFacts, task: TaskFacts) -> RecordTaskState | None:
    state = wave.states.get(task.name, WAITING_STATE)
    if state in SETTLED_STATES:
        return None
    if task.pull_request.state == MERGED_PULL_REQUEST:
        return RecordTaskState(wave=wave.wave, task=task.name, state=MERGED_STATE, reason=None)
    if task.pull_request.state == CLOSED_PULL_REQUEST:
        return RecordTaskState(wave=wave.wave, task=task.name, state=PARKED_STATE, reason=CLOSED_REASON)
    if (state == RUNNING_STATE and not task.last_run_is_a_rebase) or _is_pushed_since_preflight(state, task):
        return RecordTaskState(wave=wave.wave, task=task.name, state=PR_OPEN_STATE, reason=None)
    return None


def _is_pushed_since_preflight(state: str, task: TaskFacts) -> bool:
    return state in AWAITING_PUSH_STATES and task.preflighted_head != task.pull_request.head


@dataclasses.dataclass(frozen=True)
class _Occupancy:
    worktrees: frozenset
    tasks: frozenset


def _read_occupancy(snapshot: Snapshot) -> _Occupancy:
    live_runs = [live for project in snapshot.projects for live in project.live_runs]
    return _Occupancy(
        worktrees=frozenset(live.worktree for live in live_runs),
        tasks=frozenset((live.wave, live.task) for live in live_runs),
    )


@dataclasses.dataclass(frozen=True)
class _FollowedReading:
    occupancy: _Occupancy
    now: datetime


def _decide_preflight(wave: WaveFacts, task: TaskFacts, project: ProjectFacts, now: datetime) -> RunPreflight | None:
    if not _is_ready_for_preflight(wave, task, project, now):
        return None
    return RunPreflight(
        project=wave.project, wave=wave.wave, branch=wave.branch, task=task.name, pr=task.pull_request.number
    )


def _decide_worktree_removal(wave: WaveFacts, task: TaskFacts, occupancy: _Occupancy) -> RemoveTaskWorktree | None:
    if (
        task.pull_request.state not in SETTLED_PULL_REQUESTS
        or task.worktree is None
        or task.worktree in occupancy.worktrees
    ):
        return None
    return RemoveTaskWorktree(project=wave.project, task=task.name, worktree=task.worktree)


def _plan_followed_task(wave: WaveFacts, task: TaskFacts, project: ProjectFacts, reading: _FollowedReading) -> tuple:
    if task.rate_limit is not None:
        return ()
    record = _decide_task_state(wave, task)
    recorded = () if record is None else (record,)
    blocked_parking = _decide_blocked_parking(wave, task, reading.occupancy)
    if blocked_parking is not None:
        return (*recorded, blocked_parking)
    catch_up = _decide_catch_up(wave, task, project, reading.occupancy)
    if catch_up is not None:
        return (*recorded, catch_up)
    decided = (
        _decide_preflight(wave, task, project, reading.now),
        _decide_verification(wave, task, reading.occupancy),
        _decide_repair(wave, task, project, reading.occupancy),
        _decide_merge(wave, task, project, reading.now),
        _decide_worktree_removal(wave, task, reading.occupancy),
    )
    return (*recorded, *(action for action in decided if action is not None))


def _plan_followed_pull_requests(snapshot: Snapshot) -> tuple:
    reading = _FollowedReading(occupancy=_read_occupancy(snapshot), now=snapshot.now)
    projects = {project.name: project for project in snapshot.projects}
    return tuple(
        action
        for wave in snapshot.waves
        for task in wave.tasks
        if task.pull_request is not None
        for action in _plan_followed_task(wave, task, projects[wave.project], reading)
    )


def _decide_blocked_parking(wave: WaveFacts, task: TaskFacts, occupancy: _Occupancy) -> ParkTask | None:
    if (
        task.blocked_run is None
        or wave.states.get(task.name) != FIXING_STATE
        or task.pull_request.state != OPEN_PULL_REQUEST
        or task.preflighted_head != task.pull_request.head
        or task.worktree in occupancy.worktrees
        or (wave.wave, task.name) in occupancy.tasks
    ):
        return None
    return ParkTask(
        wave=wave.wave,
        task=task.name,
        reason=_describe_blocked_run(task.blocked_run),
        blockers=(),
    )


def _decide_catch_up(
    wave: WaveFacts, task: TaskFacts, project: ProjectFacts, occupancy: _Occupancy
) -> RebaseTask | ParkTask | LaunchRemediation | LaunchCheckRepair | None:
    if (
        not task.pull_request.behind
        or task.pull_request.state != OPEN_PULL_REQUEST
        or wave.states.get(task.name) not in REBASED_STATES
        or task.worktree is None
        or task.worktree in occupancy.worktrees
        or (wave.wave, task.name) in occupancy.tasks
    ):
        return None
    if task.holds_uncommitted_changes:
        parking_reason = _describe_spent_rounds(task, project)
        if parking_reason is not None:
            return ParkTask(wave=wave.wave, task=task.name, reason=parking_reason, blockers=())
        return _launch_repair(wave, task)
    return RebaseTask(
        project=wave.project,
        wave=wave.wave,
        branch=wave.branch,
        task=task.name,
        pr=task.pull_request.number,
        worktree=task.worktree,
        head=task.pull_request.head,
        parking_reason=_describe_spent_rounds(task, project),
    )


def _describe_spent_rounds(task: TaskFacts, project: ProjectFacts) -> str | None:
    if task.repair_rounds < project.verify_rounds:
        return None
    return f"past {project.verify_rounds} repair rounds"


def _decide_verification(
    wave: WaveFacts, task: TaskFacts, occupancy: _Occupancy
) -> RecordTaskState | LaunchVerification | None:
    state = wave.states.get(task.name)
    if (
        state != VERIFYING_STATE
        or task.pull_request.state != OPEN_PULL_REQUEST
        or _is_pushed_since_preflight(state, task)
    ):
        return None
    if task.verdict is not None and task.verdict.head == task.pull_request.head:
        return RecordTaskState(
            wave=wave.wave, task=task.name, state=STATES_BY_VERDICT[task.verdict.verdict], reason=None
        )
    if (
        task.reviewed_head != task.pull_request.head
        and task.worktree is not None
        and task.worktree not in occupancy.worktrees
        and (wave.wave, task.name) not in occupancy.tasks
    ):
        return LaunchVerification(
            project=wave.project, wave=wave.wave, task=task.name, pr=task.pull_request.number, worktree=task.worktree
        )
    return None


def _describe_request(task: TaskFacts) -> str:
    return "; ".join(
        f"{failure.name}: {finding}"
        for failure in task.preflight_failures
        if failure.name not in UNREQUESTED_FINDINGS
        for finding in failure.findings
    )


def _launch_repair(wave: WaveFacts, task: TaskFacts) -> LaunchRemediation | LaunchCheckRepair:
    if CHECKS_FINDING in {failure.name for failure in task.preflight_failures}:
        return LaunchCheckRepair(
            project=wave.project,
            wave=wave.wave,
            branch=wave.branch,
            task=task.name,
            pr=task.pull_request.number,
            worktree=task.worktree,
            checks=tuple(check.name for check in task.pull_request.checks if check.verdict != SUCCESSFUL_CHECK),
            findings=tuple(failure for failure in task.preflight_failures if failure.name != CHECKS_FINDING),
        )
    return LaunchRemediation(
        project=wave.project, wave=wave.wave, task=task.name, pr=task.pull_request.number, worktree=task.worktree
    )


def _decide_repair(
    wave: WaveFacts, task: TaskFacts, project: ProjectFacts, occupancy: _Occupancy
) -> RecordTaskState | ParkTask | LaunchRemediation | LaunchCheckRepair | None:
    state = wave.states.get(task.name)
    if (
        state not in REPAIRED_STATES
        or task.pull_request.state != OPEN_PULL_REQUEST
        or task.preflighted_head != task.pull_request.head
        or task.worktree in occupancy.worktrees
        or (wave.wave, task.name) in occupancy.tasks
    ):
        return None
    failed = {failure.name for failure in task.preflight_failures}
    if state == PR_OPEN_STATE and CHECKS_FINDING not in failed:
        request = _describe_request(task)
        if not request:
            return None
        return RecordTaskState(wave=wave.wave, task=task.name, state=CHANGES_REQUESTED_STATE, reason=request)
    parking_reason = _describe_spent_rounds(task, project)
    if parking_reason is not None:
        return ParkTask(wave=wave.wave, task=task.name, reason=parking_reason, blockers=())
    if task.worktree is None:
        return None
    return _launch_repair(wave, task)


def _is_awaiting_check_runs(pull_request: PullRequestFacts, project: ProjectFacts, now: datetime) -> bool:
    return (
        project.awaits_check_runs
        and not pull_request.checks
        and now - pull_request.updated_at < CHECK_SUITE_CREATION_DELAY
    )


def _are_checks_passed(pull_request: PullRequestFacts, project: ProjectFacts, now: datetime) -> bool:
    return not _is_awaiting_check_runs(pull_request, project, now) and all(
        check.verdict == SUCCESSFUL_CHECK for check in pull_request.checks
    )


def _is_verdict_accepted(task: TaskFacts, project: ProjectFacts) -> bool:
    if project.review == APPROVAL_REVIEW:
        return task.pull_request.review == APPROVED_REVIEW
    return (
        task.verdict is not None
        and task.verdict.verdict == PASSING_VERDICT
        and task.verdict.head == task.pull_request.head
    )


def _decide_merge(
    wave: WaveFacts, task: TaskFacts, project: ProjectFacts, now: datetime
) -> MergePullRequest | ParkTask | None:
    if (
        wave.states.get(task.name) != VERIFIED_STATE
        or task.pull_request.state != OPEN_PULL_REQUEST
        or project.auto_merge == NO_AUTO_MERGE
        or not _are_checks_passed(task.pull_request, project, now)
        or not _is_verdict_accepted(task, project)
    ):
        return None
    if task.pull_request.base != wave.branch:
        return ParkTask(wave=wave.wave, task=task.name, reason=OTHER_BASE_REASON, blockers=())
    return MergePullRequest(
        project=wave.project, wave=wave.wave, task=task.name, pr=task.pull_request.number, method=project.merge
    )


def _is_ready_for_preflight(wave: WaveFacts, task: TaskFacts, project: ProjectFacts, now: datetime) -> bool:
    return (
        wave.states.get(task.name) == PR_OPEN_STATE
        and task.opened_pull_request == task.pull_request.number
        and task.pull_request.state == OPEN_PULL_REQUEST
        and not _is_awaiting_check_runs(task.pull_request, project, now)
        and all(check.verdict != PENDING_VERDICT for check in task.pull_request.checks)
        and task.preflighted_head != task.pull_request.head
    )


def _plan_blocked_task_parkings(snapshot: Snapshot) -> tuple:
    return tuple(
        ParkTask(wave=wave.wave, task=task.name, reason=BLOCKED_REASON, blockers=task.blocked_by)
        for wave in snapshot.waves
        for task in wave.tasks
        if wave.states.get(task.name, WAITING_STATE) == WAITING_STATE and task.blocked_by
    )


def _describe_blocked_run(blocked: BlockedRun) -> str:
    return f"run {blocked.run} blocked: {blocked.question}"


def _describe_dead_run(task: TaskFacts) -> str:
    if task.blocked_run is not None:
        return _describe_blocked_run(task.blocked_run)
    if task.last_run is None:
        return RUN_NOT_STARTED_REASON
    return f"{RUN_DEAD_REASON}: {task.last_run}"


def _plan_dead_run_parkings(snapshot: Snapshot) -> tuple:
    live_tasks = {(live.wave, live.task) for project in snapshot.projects for live in project.live_runs}
    return tuple(
        ParkTask(wave=wave.wave, task=task.name, reason=_describe_dead_run(task), blockers=())
        for wave in snapshot.waves
        for task in wave.tasks
        if wave.states.get(task.name) == RUNNING_STATE
        and (task.pull_request is None or task.last_run_is_a_rebase)
        and task.rate_limit is None
        and not task.rebased_by_last_run
        and (wave.wave, task.name) not in live_tasks
    )


def _plan_branch_cuts(snapshot: Snapshot) -> tuple:
    return tuple(
        CutWaveBranch(project=wave.project, wave=wave.wave, branch=wave.branch)
        for wave in snapshot.waves
        if wave.branch_missing
    )


def _is_settled(wave: WaveFacts) -> bool:
    return bool(wave.tasks) and all(wave.states.get(task.name) in SETTLED_STATES for task in wave.tasks)


def _plan_reports(snapshot: Snapshot) -> tuple:
    return tuple(ReportWave(wave=wave.wave) for wave in snapshot.waves if _is_settled(wave) and not wave.reported)


def _is_wave_pull_request_ready(wave: WaveFacts, project: ProjectFacts, now: datetime) -> bool:
    pull_request = wave.integration_pull_request
    return (
        pull_request is not None
        and pull_request.state == OPEN_PULL_REQUEST
        and pull_request.base == wave.milestone_branch
        and project.auto_merge != NO_AUTO_MERGE
        and _are_checks_passed(pull_request, project, now)
        and wave.unresolved_threads == 0
        and (project.review != APPROVAL_REVIEW or pull_request.review == APPROVED_REVIEW)
    )


def _plan_wave_merges(snapshot: Snapshot) -> tuple:
    projects = {project.name: project for project in snapshot.projects}
    return tuple(
        MergeWavePullRequest(
            project=wave.project,
            wave=wave.wave,
            pr=wave.integration_pull_request.number,
            method=projects[wave.project].merge,
        )
        for wave in snapshot.waves
        if _is_wave_pull_request_ready(wave, projects[wave.project], snapshot.now)
    )


def _plan_closes(snapshot: Snapshot) -> tuple:
    return tuple(
        CloseWave(
            wave=wave.wave,
            pr=wave.integration_pull_request.number,
            project=wave.project,
            milestones=tuple(sorted({task.milestone for task in wave.tasks if task.milestone is not None})),
        )
        for wave in snapshot.waves
        if wave.integration_pull_request is not None and wave.integration_pull_request.state == MERGED_PULL_REQUEST
    )


def _is_integration_pull_request_due(wave: WaveFacts, project: ProjectFacts) -> bool:
    return (
        project.on_github
        and project.review != LOCAL_REVIEW
        and wave.opened_integration_pull_request is None
        and any(wave.states.get(task.name) == MERGED_STATE for task in wave.tasks)
    )


def _plan_integration_pull_requests(snapshot: Snapshot) -> tuple:
    projects = {project.name: project for project in snapshot.projects}
    return tuple(
        OpenIntegrationPullRequest(
            project=wave.project, wave=wave.wave, branch=wave.branch, tasks=tuple(task.name for task in wave.tasks)
        )
        for wave in snapshot.waves
        if _is_integration_pull_request_due(wave, projects[wave.project])
    )


def _is_milestone_pull_request_due(milestone: MilestoneFacts, snapshot: Snapshot, project: ProjectFacts | None) -> bool:
    return (
        project is not None
        and project.on_github
        and milestone.opened_pull_request is None
        and bool(milestone.merged_waves)
        and not milestone.open_waves
        and not milestone.todo
        and not any(
            wave.project == milestone.project and wave.milestone_branch == milestone.branch for wave in snapshot.waves
        )
    )


def _plan_milestone_pull_requests(snapshot: Snapshot) -> tuple:
    projects = {project.name: project for project in snapshot.projects}
    return tuple(
        OpenMilestonePullRequest(
            project=milestone.project,
            milestone=milestone.milestone,
            branch=milestone.branch,
            waves=milestone.merged_waves,
        )
        for milestone in snapshot.milestones
        if _is_milestone_pull_request_due(milestone, snapshot, projects.get(milestone.project))
    )


def _plan_milestone_closes(snapshot: Snapshot) -> tuple:
    return tuple(
        CloseMilestone(project=milestone.project, milestone=milestone.milestone, pr=milestone.opened_pull_request)
        for milestone in snapshot.milestones
        if milestone.pull_request is not None and milestone.pull_request.state == MERGED_PULL_REQUEST
    )


def _is_rebase_due(milestone: MilestoneFacts) -> bool:
    return milestone.behind_main and not milestone.rebase_run_live and milestone.blocked_rebase is None


def _plan_milestone_rebases(snapshot: Snapshot) -> tuple:
    return tuple(
        RebaseMilestone(
            project=milestone.project,
            milestone=milestone.milestone,
            branch=milestone.branch,
            waves=milestone.open_waves,
        )
        for milestone in snapshot.milestones
        if _is_rebase_due(milestone)
    )


def _plan_wave_starts(snapshot: Snapshot) -> tuple:
    rebasing = {
        (milestone.project, milestone.milestone) for milestone in snapshot.milestones if _is_rebase_due(milestone)
    }
    return tuple(
        StartWave(project=project.name, milestone=wave.milestone)
        for project in snapshot.projects
        if project.wave_start == AUTOMATIC_WAVE_START
        for wave in project.candidates
        if (project.name, wave.milestone) not in rebasing
    )


def _count_free_slots(project: ProjectFacts) -> int:
    return project.slots - sum(1 for live in project.live_runs if live.slot == BUILD_SLOT)


def _is_startable(task: TaskFacts, wave: WaveFacts) -> bool:
    return (
        wave.states.get(task.name, WAITING_STATE) == WAITING_STATE
        and task.name not in wave.implemented
        and all(wave.states.get(earlier) == MERGED_STATE or earlier in wave.implemented for earlier in task.after)
        and not task.blocked_by
    )


def _is_rebased(task: TaskFacts, wave: WaveFacts, live_tasks: frozenset) -> bool:
    return (
        wave.states.get(task.name) == RUNNING_STATE
        and task.rebased_by_last_run
        and (wave.wave, task.name) not in live_tasks
    )


def _is_study_due(study: StudyFacts, snapshot: Snapshot) -> bool:
    if study.status != ACTIVE_STATUS or study.every is None or study.parked:
        return False
    try:
        schedule = read_schedule(study.every)
    except BrigadeError as refusal:
        raise BrigadeError(f"@STUDY.{study.name}: {refusal}") from None
    return study.last_started is None or schedule.has_passed_since(study.last_started, snapshot.now)


def _plan_studies(snapshot: Snapshot) -> tuple:
    scans = {study.name for study in snapshot.studies if study.slot == SCAN_SLOT}
    live = {run.study for run in snapshot.live_study_runs}
    free_runs = snapshot.study_runs - sum(1 for run in snapshot.live_study_runs if run.study not in scans)
    launches = []
    for study in sorted(snapshot.studies, key=lambda study: study.name):
        if study.name in live or not _is_study_due(study, snapshot):
            continue
        if study.slot != SCAN_SLOT:
            if free_runs <= 0:
                continue
            free_runs -= 1
        launches.append(LaunchStudy(study=study.name))
    return tuple(launches)
