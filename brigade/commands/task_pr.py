import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_attribution import read_attribution
from brigade.commands._read_forge_environment import BUILD_SLOT, ForgeSlot, read_forge_environment
from brigade.errors import BrigadeError
from brigade.registry.read_project_forge import NO_FORGE, read_project_forge
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.tasks.locate_task_worktree import locate_task_worktree
from brigade.tasks.open_task_pull_request import TaskPullRequestDemand, open_task_pull_request


def _render_text(document: dict) -> str:
    return document["url"]


def task_pr(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    located = locate_task_worktree(runtime, Path.cwd(), request.task)
    forge_name = read_project_forge(located.project)
    if forge_name == NO_FORGE:
        raise BrigadeError(
            f"@PROJECT.{located.project.name} acts through no forge: @TASK.{located.task} opens no pull request"
        )
    forge = runtime.resolve_plugin("forge", forge_name)
    environment = read_forge_environment(configuration, ForgeSlot(forge_name, BUILD_SLOT), runtime)
    return open_task_pull_request(
        runtime,
        TaskPullRequestDemand(
            path=Path.cwd(),
            task=request.task,
            subject=request.subject,
            forge=forge,
            environment=environment,
            login=ask_forge_account(forge, forge_name, environment, runtime).login,
            attribution=tuple(read_attribution(configuration, runtime)),
        ),
    )


COMMAND = Command(
    path=("task", "pr"),
    help="push the branch of a checked task and open its pull request on the branch of its wave",
    arguments=(
        Argument(("task",), {"nargs": "?"}),
        Argument(("--subject",), {"help": "the subject of the pull request, in the imperative"}),
    ),
    run=task_pr,
    render_text=_render_text,
)
