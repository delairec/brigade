from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.runtime import Runtime
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.read_project_tasks import ProjectTasks, ProjectTasksReading, read_project_tasks

MILESTONE = "MILESTONE"
STATUS_FIELD = "STATUS"
ACTIVE_STATUS = "active"
NO_MILESTONE = None
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


def list_candidate_waves(runtime: Runtime, reading: ProjectTasksReading) -> tuple[CandidateWave, ...]:
    main = read_project_tasks(runtime, reading, NO_MILESTONE)
    readings = (
        *(
            read_project_tasks(runtime, reading, milestone)
            for milestone in _read_active_milestones(runtime.run_process, main)
        ),
        main,
    )
    open_tasks = map_open_tasks(reading.entries, reading.project.name)
    waves = (
        CandidateWave(milestone=tasks.milestone, tasks=admit_candidates(runtime, tasks, open_tasks))
        for tasks in readings
    )
    return tuple(wave for wave in waves if wave.tasks)
