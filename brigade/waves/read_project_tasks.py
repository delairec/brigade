import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tasks.read_task_field import read_task_field
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_milestone_branch_off_the_forge import RecordedMilestoneBranch, is_milestone_branch_off_the_forge
from brigade.waves.locate_forge_branch import locate_forge_branch

TASK_TYPE = "TASK"
STATUS_FIELD = "STATUS"
IMPLEMENTED_STATUS = "implemented"


@dataclass(frozen=True)
class ProjectTasks:
    root: Path
    by_name: dict[str, Entity]
    implemented: frozenset[str]
    milestone: str | None


@dataclass(frozen=True)
class ProjectTasksReading:
    configuration: Configuration
    project: Entity
    read_environment: Callable[[str], dict]
    entries: tuple[LedgerEntry, ...]


def _find_branch_to_read(runtime: Runtime, reading: ProjectTasksReading, milestone: str | None) -> str:
    recorded = find_milestone_branch(reading.entries, reading.project.name, milestone)
    if recorded is None or is_milestone_branch_off_the_forge(
        runtime.run_process,
        RecordedMilestoneBranch(project=reading.project, branch=recorded, read_environment=reading.read_environment),
    ):
        return read_project_field(reading.project, "MAIN")
    return recorded


def read_project_tasks(runtime: Runtime, reading: ProjectTasksReading, milestone: str | None) -> ProjectTasks:
    branch = _find_branch_to_read(runtime, reading, milestone)
    ref = locate_forge_branch(runtime.run_process, reading.project, branch, reading.read_environment)
    query = argparse.Namespace(project=reading.project.name, ref=ref, worktree=None)
    root = prepare_project_tree(query, reading.configuration, runtime).root
    tasks = read_entities(runtime.run_process, root, TASK_TYPE)
    return ProjectTasks(
        root=root,
        by_name={task.name: task for task in tasks},
        implemented=frozenset(
            task.name for task in tasks if read_task_field(task, STATUS_FIELD) == (IMPLEMENTED_STATUS,)
        ),
        milestone=milestone,
    )
