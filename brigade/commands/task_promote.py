import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_attribution import read_attribution
from brigade.commands._read_forge_environment import BUILD_SLOT, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.tasks.promote_task import TaskPromotionDemand, promote_task


def _render_text(document: dict) -> str:
    return f"@TASK.{document['task']} implemented, delivered by #{document['pr']}, in {document['commit']}"


def task_promote(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    return promote_task(
        runtime,
        TaskPromotionDemand(
            path=Path.cwd(),
            task=request.task,
            pr=request.pr,
            environment=read_forge_environment(configuration, BUILD_SLOT, runtime),
            attribution=tuple(read_attribution(configuration, runtime)),
        ),
    )


COMMAND = Command(
    path=("task", "promote"),
    help="set a task implemented and delivered by its pull request, then commit and push the promotion",
    arguments=(
        Argument(("task",), {"nargs": "?"}),
        Argument(("--pr",), {"type": int, "help": "the pull request that delivers the task, when not the last opened"}),
    ),
    run=task_promote,
    render_text=_render_text,
)
