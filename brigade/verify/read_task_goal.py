from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.registry.read_project_field import read_project_field
from brigade.system.run_process import ProcessRecord, ProcessRequest

MILESTONE_TYPE = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."


def _list_values(entity: Entity, field_name: str) -> list[str]:
    return [field.value for field in entity.fields if field.name == field_name]


def _read_milestone(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, name: str) -> dict:
    milestone = read_entity(run_process, root, MILESTONE_TYPE, name)
    return {
        "name": name,
        "title": read_project_field(milestone, "TITLE"),
        "subject": read_project_field(milestone, "SUBJECT"),
        "desc": _list_values(milestone, "DESC"),
        "source": _list_values(milestone, "SOURCE"),
    }


def read_task_goal(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, task: Entity) -> dict:
    milestone = read_project_field(task, "MILESTONE")
    return {
        "task": task.name,
        "title": read_project_field(task, "TITLE"),
        "milestone": None
        if milestone is None
        else _read_milestone(run_process, root, milestone.removeprefix(MILESTONE_PREFIX)),
    }
