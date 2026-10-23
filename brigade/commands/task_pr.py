import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_attribution import read_attribution
from brigade.commands._read_forge_environment import BUILD_SLOT, FORGE_NAME, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.parse_configuration import parse_configuration
from brigade.tasks.open_task_pull_request import TaskPullRequestDemand, open_task_pull_request


def _render_text(document: dict) -> str:
    return document["url"]


def task_pr(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = parse_configuration(runtime.paths.configuration_file)
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    environment = read_forge_environment(configuration, BUILD_SLOT, runtime)
    return open_task_pull_request(
        runtime,
        TaskPullRequestDemand(
            path=Path.cwd(),
            task=request.task,
            subject=request.subject,
            forge=forge,
            environment=environment,
            login=ask_forge_account(forge, FORGE_NAME, environment, runtime).login,
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
