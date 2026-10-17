import re

from brigade.errors import BrigadeError
from brigade.studies.read_schedule import read_schedule
from brigade.tick.actions import LaunchStudy, LaunchTask, StartWave
from brigade.tick.build_snapshot import ProjectFacts, Snapshot, StudyFacts, TaskFacts, WaveFacts

AUTOMATIC_PLAN_REVIEW = "auto"
BUILD_SLOT = "build"
WAITING_STATE = "queued"
MERGED_STATE = "merged"
TASK_NUMBER = re.compile(r"\d+$")
ACTIVE_STATUS = "active"
SCAN_SLOT = "none"


def plan(snapshot: Snapshot) -> tuple:
    starts = tuple(
        StartWave(request=planned.request)
        for planned in snapshot.planned
        if planned.plan_review == AUTOMATIC_PLAN_REVIEW
    )
    free_slots = {project.name: _count_free_slots(project) for project in snapshot.projects}
    launches = []
    for wave in snapshot.waves:
        for task in sorted(
            (task for task in wave.tasks if _is_startable(task, wave)), key=lambda task: _read_task_number(task, wave)
        ):
            if free_slots[wave.project] <= 0:
                break
            free_slots[wave.project] -= 1
            launches.append(
                LaunchTask(
                    request=wave.request,
                    project=wave.project,
                    milestone=wave.milestone,
                    wave=wave.wave,
                    branch=wave.branch,
                    task=task.name,
                )
            )
    return starts + tuple(launches) + _plan_studies(snapshot)


def _count_free_slots(project: ProjectFacts) -> int:
    return project.slots - sum(1 for live in project.live_runs if live.slot == BUILD_SLOT)


def _is_startable(task: TaskFacts, wave: WaveFacts) -> bool:
    return (
        wave.states.get(task.name, WAITING_STATE) == WAITING_STATE
        and task.name not in wave.implemented
        and all(wave.states.get(earlier) == MERGED_STATE or earlier in wave.implemented for earlier in task.after)
        and not task.blocked_by
    )


def _read_task_number(task: TaskFacts, wave: WaveFacts) -> int:
    number = TASK_NUMBER.search(task.name)
    if number is None:
        raise BrigadeError(f"@TASK.{task.name} of the wave {wave.milestone} carries no number to be ordered by")
    return int(number.group())


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
