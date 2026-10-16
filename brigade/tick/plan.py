import re

from brigade.errors import BrigadeError
from brigade.tick.actions import LaunchTask, StartWave
from brigade.tick.build_snapshot import ProjectFacts, Snapshot, TaskFacts, WaveFacts

AUTOMATIC_PLAN_REVIEW = "auto"
BUILD_SLOT = "build"
WAITING_STATE = "queued"
MERGED_STATE = "merged"
TASK_NUMBER = re.compile(r"\d+$")


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
                    branch=wave.branch,
                    task=task.name,
                )
            )
    return starts + tuple(launches)


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
