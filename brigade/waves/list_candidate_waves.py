import sys
from dataclasses import dataclass

from brigade.runtime import Runtime
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.list_held_tasks import list_held_tasks
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.read_project_tasks import ProjectTasks, ProjectTasksReading, read_project_tasks
from brigade.waves.read_served_milestones import read_served_milestones


@dataclass(frozen=True)
class CandidateWave:
    milestone: str | None
    tasks: tuple[str, ...]


def _read_served_milestones(runtime: Runtime, main: ProjectTasks) -> tuple[str, ...]:
    milestones = read_served_milestones(runtime.run_process, main)
    for waiting in milestones.waiting:
        sys.stderr.write(
            f"brigade tick: @MILESTONE.{waiting.milestone} is not served until its AFTER is reached:"
            f" {', '.join(waiting.after)}\n"
        )
    return milestones.served


def _compose_candidate_wave(
    runtime: Runtime, reading: ProjectTasksReading, tasks: ProjectTasks, open_tasks: dict[str, str]
) -> CandidateWave:
    held = list_held_tasks(reading.entries, reading.project.name, tasks)
    for hold in held:
        sys.stderr.write(
            f"brigade tick: @TASK.{hold.task} is held since the wave {hold.wave}:"
            f" it waits for an answer to: {hold.question}\n"
        )
    unavailable_tasks = {**open_tasks, **{hold.task: hold.wave for hold in held}}
    return CandidateWave(milestone=tasks.milestone, tasks=admit_candidates(runtime, tasks, unavailable_tasks))


def list_candidate_waves(
    runtime: Runtime, reading: ProjectTasksReading, main: ProjectTasks
) -> tuple[CandidateWave, ...]:
    readings = (
        *(read_project_tasks(runtime, reading, milestone) for milestone in _read_served_milestones(runtime, main)),
        main,
    )
    open_tasks = map_open_tasks(reading.entries, reading.project.name)
    waves = tuple(_compose_candidate_wave(runtime, reading, tasks, open_tasks) for tasks in readings)
    return tuple(wave for wave in waves if wave.tasks)
