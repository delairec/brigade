import sys
from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.runtime import Runtime
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.list_held_tasks import list_held_tasks
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.read_project_tasks import ProjectTasks, ProjectTasksReading, read_project_tasks

MILESTONE = "MILESTONE"
STATUS_FIELD = "STATUS"
ACTIVE_STATUS = "active"
NO_ACTIVE_MILESTONE = ()


@dataclass(frozen=True)
class CandidateWave:
    milestone: str | None
    tasks: tuple[str, ...]


def _read_active_milestones(
    run_process: Callable[[ProcessRequest], ProcessRecord], main: ProjectTasks
) -> tuple[str, ...]:
    if not any(read_task_field(task, MILESTONE) for task in main.by_name.values()):
        return NO_ACTIVE_MILESTONE
    status = read_awawa_document(
        run_process, main.root, ("status", MILESTONE, "--where", f"{STATUS_FIELD}=={ACTIVE_STATUS}")
    )
    return tuple(entity["name"] for entity in status["entities"])


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
        *(
            read_project_tasks(runtime, reading, milestone)
            for milestone in _read_active_milestones(runtime.run_process, main)
        ),
        main,
    )
    open_tasks = map_open_tasks(reading.entries, reading.project.name)
    waves = tuple(_compose_candidate_wave(runtime, reading, tasks, open_tasks) for tasks in readings)
    return tuple(wave for wave in waves if wave.tasks)
