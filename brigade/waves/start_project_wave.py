import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import BrigadeError
from brigade.git.cut_branch import BranchCut, cut_branch
from brigade.git.find_branch import find_branch
from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from brigade.git.push_branch import BranchPush, push_branch
from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.read_configuration import CLI_KEY, Configuration
from brigade.tasks.read_task_number import TASK_NUMBER
from brigade.tick.name_task_branch import WAVE_BRANCH_PREFIX
from brigade.tick.read_live_blockers import read_live_blockers
from brigade.waves.name_next_wave import name_next_wave

TASK_TYPE = "TASK"
TASK_REFERENCE_PREFIX = f"@{TASK_TYPE}."
STATUS_FIELD = "STATUS"
AFTER_FIELD = "AFTER"
TODO_STATUS = "todo"
IMPLEMENTED_STATUS = "implemented"
GITHUB_FORGE = "github"


@dataclass(frozen=True)
class WaveStart:
    project: str
    tasks: tuple[str, ...]
    configuration: Configuration
    read_environment: Callable[[str], dict]


@dataclass(frozen=True)
class _ProjectTasks:
    root: Path
    by_name: dict[str, Entity]
    implemented: frozenset[str]


def _read_number(task: str) -> int | None:
    number = TASK_NUMBER.search(task)
    if number is None:
        return None
    return int(number.group())


def _read_field(task: Entity, field_name: str) -> tuple[str, ...]:
    return tuple(field.value for field in task.fields if field.name == field_name)


def _read_after(task: Entity) -> tuple[str, ...]:
    return tuple(after.removeprefix(TASK_REFERENCE_PREFIX) for after in _read_field(task, AFTER_FIELD))


def _read_project_tasks(runtime: Runtime, start: WaveStart, project: Entity) -> _ProjectTasks:
    query = argparse.Namespace(project=project.name, ref=read_project_field(project, "MAIN"), worktree=None)
    root = prepare_project_tree(query, start.configuration, runtime).root
    tasks = read_entities(runtime.run_process, root, TASK_TYPE)
    return _ProjectTasks(
        root=root,
        by_name={task.name: task for task in tasks},
        implemented=frozenset(task.name for task in tasks if _read_field(task, STATUS_FIELD) == (IMPLEMENTED_STATUS,)),
    )


def _list_open_waves(reading: LedgerReading, project: str) -> tuple[WaveStarted, ...]:
    return tuple(
        entry.event
        for entry in reading.entries
        if isinstance(entry.event, WaveStarted) and entry.event.project == project
    )


def _map_open_tasks(reading: LedgerReading, project: str) -> dict[str, str]:
    return {task: wave.wave for wave in _list_open_waves(reading, project) for task in wave.tasks}


def _take_named_tasks(start: WaveStart, tasks: _ProjectTasks, open_tasks: dict[str, str]) -> tuple[str, ...]:
    for name in start.tasks:
        if name not in tasks.by_name:
            raise BrigadeError(f"@{TASK_TYPE}.{name} is not defined in the corpus of @PROJECT.{start.project}")
        if name in open_tasks:
            raise BrigadeError(f"@{TASK_TYPE}.{name} is in the open wave {open_tasks[name]}")
        if _read_number(name) is None:
            raise BrigadeError(f"@{TASK_TYPE}.{name} has no number in its name")
        for after in _read_after(tasks.by_name[name]):
            if after not in tasks.implemented and after not in start.tasks:
                raise BrigadeError(
                    f"@{TASK_TYPE}.{name} comes after @{TASK_TYPE}.{after}, neither implemented nor named"
                )
    return start.tasks


def _is_candidate(runtime: Runtime, tasks: _ProjectTasks, task: Entity, open_tasks: dict[str, str]) -> bool:
    return (
        _read_field(task, STATUS_FIELD) == (TODO_STATUS,)
        and _read_number(task.name) is not None
        and task.name not in open_tasks
        and not read_live_blockers(runtime.run_process, tasks.root, task.name)
    )


def _admit_candidates(runtime: Runtime, tasks: _ProjectTasks, open_tasks: dict[str, str]) -> tuple[str, ...]:
    candidates = [task for task in tasks.by_name.values() if _is_candidate(runtime, tasks, task, open_tasks)]
    admitted: list[str] = []
    while True:
        ready = [
            task.name
            for task in candidates
            if task.name not in admitted
            and all(after in tasks.implemented or after in admitted for after in _read_after(task))
        ]
        if not ready:
            return tuple(admitted)
        admitted.extend(ready)


def _compose_tasks(runtime: Runtime, start: WaveStart, tasks: _ProjectTasks, reading: LedgerReading) -> tuple:
    open_tasks = _map_open_tasks(reading, start.project)
    if start.tasks:
        chosen = _take_named_tasks(start, tasks, open_tasks)
    else:
        chosen = _admit_candidates(runtime, tasks, open_tasks)
    if not chosen:
        raise BrigadeError(f"@PROJECT.{start.project} has no task to start")
    return tuple(sorted(chosen, key=_read_number))


def _is_on_github(project: Entity) -> bool:
    return read_project_field(project, "FORGE") == GITHUB_FORGE


def _find_branch_anywhere(runtime: Runtime, start: WaveStart, project: Entity, branch: str) -> bool:
    repository = Path(read_project_field(project, "PATH"))
    if find_branch(runtime.run_process, repository, branch):
        return True
    if not _is_on_github(project):
        return False
    remote_branch = RemoteBranch(repository=repository, branch=branch, environment=start.read_environment(CLI_KEY))
    return find_remote_branch(runtime.run_process, remote_branch)


def _cut_missing_branches(runtime: Runtime, start: WaveStart, project: Entity) -> None:
    repository = Path(read_project_field(project, "PATH"))
    for wave in _list_open_waves(read_ledger(runtime.paths.state_root), start.project):
        if find_branch(runtime.run_process, repository, wave.branch):
            continue
        cut = BranchCut(repository=repository, branch=wave.branch, start=read_project_field(project, "MAIN"))
        cut_branch(runtime.run_process, cut)
        if _is_on_github(project):
            push = BranchPush(repository=repository, branch=wave.branch, environment=start.read_environment(CLI_KEY))
            push_branch(runtime.run_process, push)


def start_project_wave(runtime: Runtime, start: WaveStart) -> dict:
    require_operational_corpus(runtime.paths)
    project = find_project(read_projects(runtime), start.project)
    tasks = _read_project_tasks(runtime, start, project)

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
