from pathlib import Path

from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.tasks.promote_task import TaskPromotionDemand, promote_task


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return f"@TASK.{document['task']} implemented, delivered by #{document['pr']}, in {document['commit']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def task_promote(request, runtime: Runtime) -> dict:
    return promote_task(runtime, TaskPromotionDemand(path=Path.cwd(), task=request.task, pr=request.pr))


COMMAND = Command(
    path=("task", "promote"),
    help="set a task implemented and delivered by its pull request, then commit and push the promotion",
    arguments=(
        Argument(("task",), {"nargs": "?"}),
        Argument(("--pr",), {"type": int, "help": "the pull request that delivers the task, when not the last opened"}),
    ),
    run=task_promote,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
