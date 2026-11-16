import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._equip_collector import equip_collector
from brigade.commands._equip_preflight import equip_preflight
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.tasks.check_task import TaskCheckDemand, check_task
from brigade.tasks.locate_task_worktree import locate_task_worktree

PASSED = "pass"
FAILED = "fail"
MS_PER_S = 1000
ONE_FAILED = 1


def _describe_verdict(check: dict) -> str:
    verdict = PASSED if check["passed"] else FAILED
    return f"{verdict}  {check['command']}  {check['duration_ms'] / MS_PER_S:.1f} s\n"


def _describe_tail(check: dict) -> str:
    return f"\n$ {check['command']}\n" + "".join(f"{line}\n" for line in check["tail"])


def _render_text(document: dict) -> str:
    checks = document["checks"]
    verdicts = "".join(_describe_verdict(check) for check in checks)
    tails = "".join(_describe_tail(check) for check in checks if not check["passed"])
    return f"{verdicts}{tails}".removesuffix("\n")


def _decide_exit_code(document: dict) -> int:
    return ONE_FAILED if any(not check["passed"] for check in document["checks"]) else 0


def task_check(request: argparse.Namespace, runtime: Runtime) -> dict:
    worktree = locate_task_worktree(runtime, Path.cwd(), request.task)
    equipment = equip_collector(Path(read_project_field(worktree.project, "PATH")), runtime)
    return check_task(
        runtime, TaskCheckDemand(worktree=worktree, equipment=equipment, plugins=equip_preflight(runtime))
    )


COMMAND = Command(
    path=("task", "check"),
    help="run the acceptance commands and the checks of the corpus in the worktree of a task",
    arguments=(Argument(("task",), {"nargs": "?"}),),
    run=task_check,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
