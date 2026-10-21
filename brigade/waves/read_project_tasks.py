import argparse
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import Entity, read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.tasks.read_task_field import read_task_field

TASK_TYPE = "TASK"
STATUS_FIELD = "STATUS"
IMPLEMENTED_STATUS = "implemented"


@dataclass(frozen=True)
class ProjectTasks:
    root: Path
    by_name: dict[str, Entity]
    implemented: frozenset[str]


def read_project_tasks(runtime: Runtime, configuration: Configuration, project: Entity) -> ProjectTasks:
    query = argparse.Namespace(project=project.name, ref=read_project_field(project, "MAIN"), worktree=None)
    root = prepare_project_tree(query, configuration, runtime).root
    tasks = read_entities(runtime.run_process, root, TASK_TYPE)
    return ProjectTasks(
        root=root,
        by_name={task.name: task for task in tasks},
        implemented=frozenset(
            task.name for task in tasks if read_task_field(task, STATUS_FIELD) == (IMPLEMENTED_STATUS,)
        ),
    )
