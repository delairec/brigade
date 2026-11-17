import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._accept_parameter import accept_parameter
from brigade.commands._equip_collector import equip_collector
from brigade.commands._equip_preflight import equip_preflight
from brigade.commands._equip_registered_collector import equip_registered_collector
from brigade.commands._locate_preflights import locate_preflights
from brigade.commands._read_parameters import read_parameters
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.preflights.run_preflight import PreflightRun, run_preflight
from brigade.registry.read_projects import read_projects
from brigade.registry.require_project_at import require_project_at
from brigade.runtime import Runtime
from brigade.system.check_shapes import FAILED
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.tasks.find_task_base import find_task_base
from brigade.verify.find_opened_task import find_opened_task
from brigade.verify.preflight_pull_request import REVIEW_PULL_REQUEST, PreflightDemand, preflight_pull_request

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    lines = [f"preflight {document['preflight']}"]
    for check in document["checks"]:
        lines.append(f"{check['result']}  {check['name']}")
        lines.extend(f"  {finding}" for finding in check["findings"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return int(document["result"] == FAILED)


def _preflight_pull_request(pr: int, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_REQUIRED)
    worktree = locate_worktree_root(runtime.run_process, Path.cwd())
    project = require_project_at(read_projects(runtime), locate_main_checkout(runtime.run_process, worktree))
    task = find_opened_task(runtime, project.name, pr).opened.task
    return preflight_pull_request(
        runtime,
        PreflightDemand(
            project=project,
            task=task,
            base_branch=find_task_base(runtime, worktree, project, task),
            pr=pr,
            equipment=equip_registered_collector(project, configuration, runtime),
            plugins=equip_preflight(runtime),
        ),
    )


def preflight(request: argparse.Namespace, runtime: Runtime) -> dict:
    parameters = read_parameters(request.extra_arguments)
    if request.name == REVIEW_PULL_REQUEST:
        return _preflight_pull_request(int(parameters["pr"]), runtime)
    project = locate_main_checkout(runtime.run_process, locate_worktree_root(runtime.run_process, Path.cwd()))
    run = PreflightRun(
        name=request.name,
        project=project,
        parameters=parameters,
        equipment=equip_collector(project, runtime),
        preflights=locate_preflights(project, runtime),
        plugins=equip_preflight(runtime),
    )
    outcome = run_preflight(run, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "preflight": request.name,
        "parameters": parameters,
        "result": outcome.result,
        "checks": outcome.checks,
    }


COMMAND = Command(
    path=("preflight",),
    help="run the collectors and the checks of a named preflight; key=value pairs are their parameters",
    arguments=(Argument(("name",), {"help": "the name of the preflight"}),),
    run=preflight,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    accept_extra_argument=accept_parameter,
)
