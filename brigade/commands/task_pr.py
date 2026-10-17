from pathlib import Path

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.tasks.open_task_pull_request import TaskPullRequestDemand, open_task_pull_request


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return document["url"]


def _decide_exit_code(document: dict) -> int:
    return 0


def task_pr(request, runtime: Runtime) -> dict:
    return open_task_pull_request(
        runtime, TaskPullRequestDemand(path=Path.cwd(), task=request.task, subject=request.subject)
    )


COMMAND = Command(
    path=("task", "pr"),
    help="push the branch of a checked task and open its pull request on the branch of its wave",
    arguments=(
        Argument(("task",), {"nargs": "?"}),
        Argument(("--subject",), {"help": "the subject of the pull request, in the imperative"}),
    ),
    run=task_pr,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
