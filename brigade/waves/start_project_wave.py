from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.git.find_branch import find_branch
from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.read_configuration import CLI_KEY, Configuration
from brigade.tasks.find_task_number import find_task_number
from brigade.tasks.read_task_after import read_task_after
from brigade.tick.name_task_branch import WAVE_BRANCH_PREFIX
from brigade.waves.admit_candidates import admit_candidates
from brigade.waves.cut_wave_branch import WaveBranchCut, cut_wave_branch
from brigade.waves.is_wave_branch_missing import is_wave_branch_missing
from brigade.waves.list_open_waves import list_open_waves
from brigade.waves.map_open_tasks import map_open_tasks
from brigade.waves.name_next_wave import name_next_wave
from brigade.waves.read_project_tasks import ProjectTasks, read_project_tasks

TASK_TYPE = "TASK"


@dataclass(frozen=True)
class WaveStart:
    project: str
    tasks: tuple[str, ...]
    configuration: Configuration
    read_environment: Callable[[str], dict]


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
        chosen = admit_candidates(runtime.run_process, tasks, open_tasks)
    if not chosen:
        raise BrigadeError(f"@PROJECT.{start.project} has no task to start")
    return tuple(sorted(chosen, key=find_task_number))


def _find_branch_anywhere(runtime: Runtime, start: WaveStart, project: Entity, branch: str) -> bool:
    repository = Path(read_project_field(project, "PATH"))
    if find_branch(runtime.run_process, repository, branch):
        return True
    if not is_on_github(project):
        return False
    remote_branch = RemoteBranch(repository=repository, branch=branch, environment=start.read_environment(CLI_KEY))
    return find_remote_branch(runtime.run_process, remote_branch)


def _cut_missing_branches(runtime: Runtime, start: WaveStart, project: Entity) -> None:
    for wave in list_open_waves(read_ledger(runtime.paths.state_root).entries, start.project):
        cut = WaveBranchCut(project=project, branch=wave.branch, read_environment=start.read_environment)
        if is_wave_branch_missing(runtime.run_process, cut):
            cut_wave_branch(runtime.run_process, cut)


def start_project_wave(runtime: Runtime, start: WaveStart) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), start.project)
    tasks = read_project_tasks(runtime, start.configuration, project)

    def name_wave(reading: LedgerReading) -> WaveStarted:
        chosen = _compose_tasks(runtime, start, tasks, reading)
        wave = name_next_wave(start.project, reading.entries)
        branch = f"{WAVE_BRANCH_PREFIX}{wave}"
        if _find_branch_anywhere(runtime, start, project, branch):
            raise BrigadeError(f"the branch {branch} exists and no wave.started names it")
        return WaveStarted(wave=wave, project=start.project, branch=branch, tasks=chosen)

    started = append_derived_event(runtime.paths, runtime.now, name_wave)
    _cut_missing_branches(runtime, start, project)
    return {key: started[key] for key in ("wave", "project", "branch", "tasks")}
