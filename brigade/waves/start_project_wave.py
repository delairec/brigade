from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tasks.digest_task_entity import digest_task_entity
from brigade.tasks.find_task_number import find_task_number
from brigade.tasks.read_task_after import read_task_after
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.list_held_tasks import list_held_tasks
from brigade.waves.locate_wave_base import WaveBaseDemand, locate_wave_base
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.name_next_wave import name_next_wave
from brigade.waves.read_project_tasks import ProjectTasks, ProjectTasksReading, read_project_tasks
from brigade.waves.read_wave_milestone import read_wave_milestone

TASK_TYPE = "TASK"
NO_MILESTONE = None


@dataclass(frozen=True)
class WaveStart:
    project: str
    tasks: tuple[str, ...]
    configuration: Configuration
    read_environment: Callable[[str], dict]
    read_login: Callable[[], str]


def _take_named_tasks(start: WaveStart, tasks: ProjectTasks, open_tasks: dict[str, str]) -> tuple[str, ...]:
    for name in start.tasks:
        if name not in tasks.by_name:
            raise BrigadeError(f"@{TASK_TYPE}.{name} is not defined in the corpus of @PROJECT.{start.project}")
        if name in open_tasks:
            raise BrigadeError(f"@{TASK_TYPE}.{name} is in the open wave {open_tasks[name]}")
        if find_task_number(name) is None:
            raise BrigadeError(f"@{TASK_TYPE}.{name} has no number in its name")
        for after in read_task_after(tasks.by_name[name]):
            if after not in tasks.implemented and after not in start.tasks:
                raise BrigadeError(
                    f"@{TASK_TYPE}.{name} comes after @{TASK_TYPE}.{after}, neither implemented nor named"
                )
    return start.tasks


def _compose_tasks(runtime: Runtime, start: WaveStart, tasks: ProjectTasks, reading: LedgerReading) -> tuple:
    open_tasks = map_open_tasks(reading.entries, start.project)
    if start.tasks:
        chosen = _take_named_tasks(start, tasks, open_tasks)
    else:
        held = {hold.task: hold.wave for hold in list_held_tasks(reading.entries, start.project, tasks)}
        chosen = admit_candidates(runtime, tasks, {**open_tasks, **held})
    if not chosen:
        raise BrigadeError(f"@PROJECT.{start.project} has no task to start")
    return tuple(sorted(chosen, key=find_task_number))


def _demand_base(start: WaveStart, project: Entity, tasks: ProjectTasks, wave: WaveStarted) -> WaveBaseDemand:
    return WaveBaseDemand(
        project=project,
        milestone=read_wave_milestone(wave.wave, (tasks.by_name[task] for task in wave.tasks)),
        root=tasks.root,
        read_environment=start.read_environment,
        read_login=start.read_login,
    )


def start_project_wave(runtime: Runtime, start: WaveStart, milestone: str | None) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), start.project)
    tasks_reading = ProjectTasksReading(
        configuration=start.configuration,
        project=project,
        read_environment=start.read_environment,
        entries=runtime.read_ledger(runtime.paths.state_root).entries,
    )
    tasks = read_project_tasks(runtime, tasks_reading, milestone)

    def name_wave(reading: LedgerReading) -> WaveStarted:
        chosen = _compose_tasks(runtime, start, tasks, reading)
        return WaveStarted(
            wave=name_next_wave(start.project, reading.entries),
            project=start.project,
            tasks=chosen,
            task_digests={task: digest_task_entity(tasks.by_name[task]) for task in chosen},
        )

    started = append_derived_event(runtime.paths, runtime.now, name_wave)
    wave = WaveStarted(wave=started["wave"], project=started["project"], tasks=tuple(started["tasks"]))
    locate_wave_base(runtime, _demand_base(start, project, tasks, wave))
    return {key: started[key] for key in ("wave", "project", "tasks")}
