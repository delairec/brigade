from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
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


def verify_preflight(request, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    run_process = runtime.run_process
    project = require_project_at(
        read_projects(runtime), locate_main_checkout(run_process, locate_worktree_root(run_process, Path.cwd()))
    )
    found = find_opened_task(runtime, project.name, request.pr)
    return preflight_pull_request(
        runtime,
        PreflightDemand(
            project=project,
            task=found.opened.task,
            wave_branch=found.wave_branch,
            pr=request.pr,
            forge=runtime.resolve_plugin("forge", FORGE_NAME),
            environment=read_forge_environment(configuration, CLI_KEY, runtime),
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
