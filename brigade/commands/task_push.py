import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import BUILD_SLOT, ForgeSlot, read_forge_environment
from brigade.registry.read_project_forge import read_project_forge
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.tasks.push_task_branch import TaskPushDemand, push_task_branch


def _render_text(document: dict) -> str:
    return f"{document['branch']} pushed at {document['head']} for @TASK.{document['task']}"


def task_push(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    located = locate_task_worktree(runtime, Path.cwd(), request.task)
    forge_slot = ForgeSlot(read_project_forge(located.project), BUILD_SLOT)
    return push_task_branch(
        runtime,
        TaskPushDemand(
            path=Path.cwd(), task=request.task, environment=read_forge_environment(configuration, forge_slot, runtime)
        ),
    )


COMMAND = Command(
    path=("task", "push"),
    help="push the branch of a task whose HEAD passed brigade task check, with a lease",
    arguments=(Argument(("task",), {"nargs": "?"}),),
    run=task_push,
    render_text=_render_text,
)
