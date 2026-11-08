import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.tasks.find_task_base import find_task_base
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request

CLI_KEY = "cli"
FAILED = "fail"


def _render_text(document: dict) -> str:
    lines = [f"preflight of #{document['pr']}, @TASK.{document['task']} at {document['head']}"]
    for check in document["checks"]:
        lines.append(f"{check['verdict']}  {check['name']}")
        lines.extend(f"  {finding}" for finding in check["findings"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return int(any(check["verdict"] == FAILED for check in document["checks"]))


def verify_preflight(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    run_process = runtime.run_process
    worktree = locate_worktree_root(run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(run_process, worktree))
    found = find_opened_task(runtime, project.name, request.pr)
    forge_name = read_project_forge(project)
    return preflight_pull_request(
        runtime,
        PreflightDemand(
            project=project,
            task=found.opened.task,
            base_branch=find_task_base(runtime, worktree, project, found.opened.task),
            pr=request.pr,
            forge=runtime.resolve_plugin("forge", forge_name),
            environment=read_forge_environment(configuration, ForgeSlot(forge_name, CLI_KEY), runtime),
            configuration=configuration,
        ),
    )


COMMAND = Command(
    path=("verify", "preflight"),
    help="run the deterministic checks of a pull request of a task before any judgment",
    group_help="check the pull request of a task",
    arguments=(Argument(("pr",), {"type": int, "help": "the number of the pull request"}),),
    run=verify_preflight,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
