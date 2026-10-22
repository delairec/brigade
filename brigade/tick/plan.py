from datetime import datetime

from brigade.errors import BrigadeError
from brigade.ledger.format_instant import format_instant
from brigade.studies.read_schedule import read_schedule
from brigade.tasks.read_task_number import read_task_number
from brigade.tick.actions import (
    CloseWave,
    CutWaveBranch,
    LaunchStudy,
    LaunchTask,
    LaunchVerification,
    ParkTask,
    PauseWave,
    RecordTaskState,
    RemoveTaskWorktree,
    ReportWave,
    ResumeTaskRun,
    ResumeWave,
    RunPreflight,
    StartWave,
)
from brigade.tick.build_snapshot import SETTLED_STATES, ProjectFacts, Snapshot, StudyFacts, TaskFacts, WaveFacts
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


def plan(snapshot: Snapshot) -> tuple:
    pauses = _plan_pauses(snapshot)
    paused = {wave.wave for wave in snapshot.waves if wave.pause is not None} | {
        pause.wave for pause in pauses if isinstance(pause, PauseWave)
    }
    free_slots = {project.name: _count_free_slots(project) for project in snapshot.projects}
    launches = []
    for wave in (wave for wave in snapshot.waves if wave.wave not in paused):
        for task in sorted(
            (task for task in wave.tasks if _is_startable(task, wave)),
            key=lambda task: read_task_number(task.name, wave.wave),
        ):
            if free_slots[wave.project] <= 0:
                break
            free_slots[wave.project] -= 1
            launches.append(LaunchTask(project=wave.project, wave=wave.wave, branch=wave.branch, task=task.name))
    return (
        pauses
        + _plan_resumes(snapshot)
        + _plan_followed_pull_requests(snapshot)
        + _plan_blocked_task_parkings(snapshot)
        + _plan_branch_cuts(snapshot)
        + _plan_reports(snapshot)
        + _plan_closes(snapshot)
        + tuple(launches)
        + _plan_wave_starts(snapshot)
        + _plan_studies(snapshot)
    )


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
            ResumeTaskRun(wave=wave.wave, task=task.name, run=task.stopped_run)
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
    if state == RUNNING_STATE or _is_pushed_since_preflight(state, task):
        return RecordTaskState(wave=wave.wave, task=task.name, state=PR_OPEN_STATE, reason=None)
    return None


def _is_pushed_since_preflight(state: str, task: TaskFacts) -> bool:
    return state == VERIFYING_STATE and task.preflighted_head != task.pull_request.head


def _plan_followed_pull_requests(snapshot: Snapshot) -> tuple:
    held = {live.worktree for project in snapshot.projects for live in project.live_runs}
    live_tasks = {(live.wave, live.task) for project in snapshot.projects for live in project.live_runs}
    projects = {project.name: project for project in snapshot.projects}
    actions = []
    for wave in snapshot.waves:
        for task in (task for task in wave.tasks if task.pull_request is not None):
            record = _decide_task_state(wave, task)
            if record is not None:
                actions.append(record)
            if _is_ready_for_preflight(wave, task, projects[wave.project]):
                actions.append(
                    RunPreflight(
                        project=wave.project,
                        wave=wave.wave,
                        branch=wave.branch,
                        task=task.name,
                        pr=task.pull_request.number,
                    )
                )
            verification = _decide_verification(wave, task, held, live_tasks)
            if verification is not None:
                actions.append(verification)
            if (
                task.pull_request.state in SETTLED_PULL_REQUESTS
                and task.worktree is not None
                and task.worktree not in held
            ):
                actions.append(RemoveTaskWorktree(project=wave.project, task=task.name, worktree=task.worktree))
    return tuple(actions)


def _decide_verification(
    wave: WaveFacts, task: TaskFacts, held: set, live_tasks: set
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
        and task.worktree not in held
        and (wave.wave, task.name) not in live_tasks
    ):
        return LaunchVerification(
            project=wave.project, wave=wave.wave, task=task.name, pr=task.pull_request.number, worktree=task.worktree
        )
    return None


def _is_ready_for_preflight(wave: WaveFacts, task: TaskFacts, project: ProjectFacts) -> bool:
    return (
        wave.states.get(task.name) == PR_OPEN_STATE
        and task.opened_pull_request == task.pull_request.number
        and task.pull_request.state == OPEN_PULL_REQUEST
        and (bool(task.pull_request.checks) or not project.awaits_check_runs)
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


def _plan_closes(snapshot: Snapshot) -> tuple:
    return tuple(
        CloseWave(wave=wave.wave, pr=wave.integration_pull_request.number)
        for wave in snapshot.waves
        if wave.integration_pull_request is not None and wave.integration_pull_request.state == MERGED_PULL_REQUEST
    )


def _plan_wave_starts(snapshot: Snapshot) -> tuple:
    return tuple(
        StartWave(project=project.name)
        for project in snapshot.projects
        if project.wave_start == AUTOMATIC_WAVE_START and project.candidates
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
